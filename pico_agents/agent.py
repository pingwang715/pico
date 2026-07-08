"""
Agent: wraps a system prompt + a set of Tools + a tool-use loop.

This reimplements the core mechanic that LangGraph/CrewAI hide inside their
own agent classes: call the model, check if it wants a tool, run the tool,
feed the result back, repeat until the model produces a final text answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic

from .tools import Tool
from .tracer import Tracer

DEFAULT_MODEL = "claude-sonnet-4-5"

@dataclass
class AgentResult:
    text: str
    rationale: str | None # explainability field -- every agent should return "why"
    tool_calls: list[dict] = field(default_factory=list)
    raw_messages: list[dict] = field(default_factory=list)

class Agent:
    """A single agent: system prompt + tools + a run loop."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[Tool] | None = None,
        model: str = DEFAULT_MODEL,
        client: anthropic.Anthropic | None = None,
        max_tool_iterations: int = 6,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in (tools or [])}
        self.model = model
        self.client = client or anthropic.Anthropic()
        self.max_tool_iterations = max_tool_iterations

    def run(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        tracer: Tracer | None = None,
    ) -> AgentResult:
        """
        Run the agent to completion: repeatedly call the model, execute any
        requested tools, and feed results back until the model stops asking
        for tools and returns a final text response.
        """

        span_id = tracer.start_span("agent_run", self.name, input=user_message) if tracer else None

        full_prompt = user_message
        if context:
            full_prompt = f"Context:\n{contet}\n\nTask:\n{user_message}"

        messages: list[dict] = [{"role": "user", "content": full_prompt}]
        tool_calls_log : list[dict] = []

        api_tools = [t.to_api_schema() for t in self.tools.values()]
    
        for _ in range(self.max_tool_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                tools=api_tools if api_tools else anthropic.NOT_GIVEN,
            )

            if response.stop_reason != "tool_use":
                text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                result = AgentResult(
                    text=text,
                    rationale=self._extract_rationale(text),
                    tool_calls=tool_calls_log,
                    raw_messages=messages,
                )
                if tracer and span_id
                    tracer.end_span(span_id, output=text)
                return result
        
            # Model wants to use one or more tools
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_name = block.name
                tool_input = block.input
                tool_span_id = tracer.start_span(
                    "tool_call", tool_name, input=tool_input
                ) if tracer else None

                if tool_name not in self.tools:
                    ouput = f"Error: unknown tool '{tool_name}'"
                else:
                    try:
                        output = self.tools[tool_name](**tool_input)
                    except Exception as exc: # tool failures shouldn't crash the run
                        output =f"Error running tool '{tool_name}': {exc}"
                
                if tracer and tool_span_id:
                    tracer.end_span(tool_span_id, output=output)
                
                tool_calls_log.append({"tool": tool_name, "input": tool_input, "output": output})
                tool_results. append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                })

            messages.append({"role": "user", "content": tool_results})

        # Ran out of iterations without a final answer
        result = AgentResult(
            text="[max tool iterations reached without a final answer]",
            rationale=None,
            tool_calls=tool_calls_log,
            raw_messages=messages,
        )
        if tracer and span_id:
            tracer.end_span(span_id, output=result.text)
        return result

    @staticmethod
    def _extract_rationale(text: str) -> str | None:
        """
        Convention: agents are prompted to end their answer with a line like
        'RATIONALE: ...". This pulls it out into a structured field so
        downstream agents (e.g. an audit agent) can consume it without
        re-parsing free text.
        """
        marker = "RATIONALE:"
        if marker in text:
            return text.split(marker, 1)[1].strip()
        return None
            


