from pico_agents.tools import tool

def test_tool_schema():
    @tool
    def get_weather(city: str, country: str = "AU") -> str:
        """Look up weather.
        :param city: City name
        """
        return "sunny"

    assert get_weather.name == "get_weather"
    assert "city" in get_weather.schema["properties"]
    assert get_weather.schema["required"] == ["city"]