"""
Tool registration for pico-agents.

A `Tool` wraps a plain Python function and auto-derives the JSON schema
that the Claude API's tool-use interface expects, by inspecting the
function's type hints and docstring. This is the same mechanic that
LangChain/LangGraph hide behind their `@tool` decorators -- reimplemented
here 
"""

import inspect
import typing
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints

_PY_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    schema: dict

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def to_api_schema(self) -> dict:
        """Return the dict shape expected by the Anthropic Messages API tools param."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.schema,
        }

def tool(func: Callable[..., Any] | None = None, *, name: str | None = None) -> Callable: 
    """
    Decorator that turns a plain function into a `Tool`.

    The function's docstring becomes the tool description (first line) and
    per-argument descriptions (subsequent ":param x:" lines, optional).
    Type hints become the JSON schema types. Required-ness is inferred from
    whether the parameter has a default value.

    Example:
        @tool
        def get_weather(city: str, country: str = "AU") -> str:
            '''Look up current weather for a city.
            :param city: City name
            :param country: ISO country code
            '''
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Tool:
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)
        doc = inspect.getdoc(fn) or ""
        doc_lines = doc.splitlines()
        description = doc_lines[0].strip() if doc_lines else fn.__name__

        param_descriptions: dict[str, str] = {}
        for line in doc_lines[1:]:
            line = line.strip()
            if line.startswith(":param"):
                try:
                    _, rest = line.split(":param", 1)
                    pname, pdesc = rest.split(":", 1)
                    param_descriptions[pname.strip()] = pdesc.strip()
                except ValueError:
                    continue
        
        properties: dict[str, dict] = {}
        required: list[str] = []

        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            py_type = hints.get(pname, str)
            json_type = _PY_TO_JSON_TYPE.get(py_type, "string")
            prop: dict[str, Any] = {"type": json_type}
            if pname in param_descriptions:
                prop["description"] = param_descriptions[pname]
            properties[pname] = prop
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        
        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        return Tool(
            name=name or fn.__name__,
            description=description,
            func=fn,
            schema=schema,
        )

    # This is the pattern that lets a decorator work both with and without parentheses, @tool and @tool(name="custom_name")
    if func is not None:
        return decorator(func)
    return decorator