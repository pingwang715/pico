"""
Tools for the Nemo-inspired claims triage demo.

Deliberately deterministic where determinism is correct: coverage lookup,
payout calculation. LLM reasoning is reserved for the parts where language
understanding earns its keep (fraud rationale, weather-event interpretation,
audit summarization) -- mirrors the note in the enterprise-architecture
write-up about not routing everything through an LLM by default.
"""

from __future__ import annotations

from pico_agents.tools import tool

# --- fake in-memory "databases" for the demo -----------------------------

_POLICIES = {
    "laura-001": {
        "customer": "Laura",
        "state": "SA",
        "covers_severe_weather_food_spoilage": True,
        "policy_limit_aud": 1000,
        "deductible_aud": 0,
    }
}

_WEATHER_EVENTS = [
    {
        "region": "Adelaide",
        "date": "2026-07-01",
        "type": "storm",
        "caused_power_outage": True,
        "min_outage_hours": 4
    },
]

_CLAIM_HISTORY = {
    "laura-001": [
        {"date": "2025-11-02", "type": "food_spoilage", "amount_aud": 180},
    ]
}

@tool
def lookup_policy(customer_id: str) -> dict:
    """Look up a customer's policy and whether it covers severe-weather food spoilage. 
    :param customer_id: The customer's policy ID
    """

    return _POLICIES.get(customer_id, {"error": "policy not found"})

@tool
def verify_weather_event(region: str, date: str, outage_hours: int) -> dict:
    """Check whether a severe weather event matching the claim occurred.
    :param region: Region/city of the claim
    :param date: Date of the incident (YYYY-MM-DD)
    :param outage_hours: Length of the power outage in hours, as claimed
    """

    for event in _WEATHER_EVENTS:
        if event["region"].lower() == region.lower() and event["date"] == date:
            matches = outage_hours >= event["min_outage_hours"]
            return {"event_found": True, "meets_threshold": matches, **event}
    return {"event_found": False}

@tool
def get_claim_history(customer_id: str) -> list:
    """Retrieve a customer's past claims for fraud-pattern checking.
    :param customer_id: The customer's policy ID
    """
    return _CLAIM_HISTORY.get(customer_id, [])

@tool
def calculate_payout(claimed_amount_aud: float, policy_limit_aud: float, deductible_aud: float) -> dict:
    """Deterministically calculate the payout amount given policy terms.
    :param claimed_amount_aud: Amount claimed by the customer
    :param policy_limit_aud: Maximum the policy will pay for this claim type
    :param deductible_aud: Deductible to substract before payout
    """

    payout = max(0.0, min(claimed_amount_aud, policy_limit_aud) - deductible_aud)
    return {"payout_aud": round(payout, 2)}