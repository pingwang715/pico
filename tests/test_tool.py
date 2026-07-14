from pico_agents.tools import tool
from demo.claim_tools import lookup_policy, verify_weather_event, get_claim_history, calculate_payout

def test_tool_schema():
    @tool
    def get_weather(city: str, country: str = "AU") -> str:
        """Look up current weather for a city.
        :param city: City name
        :param country: ISO country code
        """
        return f"sunny in {city}, {country}"

    assert get_weather.name == "get_weather"
    assert get_weather.description == "Look up current weather for a city."
    schema = get_weather.schema
    assert schema["properties"]["city"]["type"] == "string"
    assert schema["properties"]["city"]["description"] == "City name"
    assert schema["required"] == ["city"] # country has as default, so no required
    assert get_weather(city="Adelaide") == "sunny in Adelaide, AU"
    
def test_tool_demo():
    @tool
    def lookup_policy(customer_id: str) -> dict:
        """Look up policy.
        :param customer_id: The customer's policy ID
        """
        return {
            "customer": "Laura",
            "state": "SA",
            "covers_severe_weather_food_spoilage": True,
            "policy_limit_aud": 1000,
            "deductible_aud": 0,
        }   
    
    result = lookup_policy("laura-001")
    assert result["customer"] == "Laura"

    @tool
    def verify_weather_event_match_meets_threshold():
        result = verify_weather_event(region= "Adeleide", date="2026-07-01", outage_hours=6)
        assert result["event_found"] is True
        assert result["meets_threshold"] is True
    
    @tool
    def get_claim_history_existing_customer():
        """Retrieve a customer's past claims for fraud-pattern checking.
        :param customer_id: The customer's policy ID
        """
        result = get_claim_history("laura-001")
        assert result == [
            {"date": "2025-11-02", "type": "food_spoilage", "amount_aud": 180}
        ]
    
    @tool 
    def get_claim_history_unknown_customer_returns_empty_list():
        result = get_claim_history("nonexistent-999")
        assert result == []
    
    @tool
    def calculate_payout_successful():
        result = calculate_payout(100, 40, 0)
        assert result == {"payout_aud": 40.0}
    
    @tool
    def calculate_payout_dedictible_subtracted():
        result = calculate_payout(100, 1000, 20)
        assert result["payout_aud"] == 80.0


if __name__ == "__main__":
    test_tool_schema()
    test_tool_demo()
    print("All tests passed.")