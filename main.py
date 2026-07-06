from anthropic import Anthropic

def main():
    print("Hello from pico!")


if __name__ == "__main__":
    main()

from dotenv import load_dotenv
load_dotenv()

client = Anthropic()

def get_weather(location: str, unit: str = "celsius"):
    return f"The weather in {location} is 18 degrees {unit[0].upper()}, partly cloudy."

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The name of a city and the state, e.g. Munich, Bayern",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature",
                },
            },
            "required": ["location"]
        },
        "input_examples": [
            {"location": "Paris, France", "unit": "celsius"},
            {"location": "New York, NY", "unit": "fahrenheit"}
        ]
    }
]

messages = [{"role": "user", "content": "What's the weather like in New York, NY?"}]

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather like in New York, NY?"}],
)
print(response)

tool_use_block = next(b for b in response.content if b.type == "tool_use")

tool_name = tool_use_block.name
tool_input = tool_use_block.input
tool_id = tool_use_block.id

result = get_weather(**tool_input)

messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": [
    {
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": str(result)
    }
]})

final_response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

print(final_response.content[0].text)
print(messages)