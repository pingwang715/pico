"""
Claims triage demo: a scaled-down versino of Allianz's "Nemo" multi-agent
claims pipeline, built on the pico_agents framework instead of LangGraph.

Pipeline: coverage -> weather -> fraud -> payout -> audit -> human review.
The "cyber" and "planner" roles from Nemo are folded into orchestration
concers (see README) rather than modeled as separate LLM agents, since in
a real deployment they're infrastructure, not reasoning steps.

Run:
    python -m demo.claims_pipeline
"""

from __future__ import annotations

import json

from pico_agents import Agent, Orchestrator, Tracer

from demo.claim_tools import (
    lookup_policy,
    verify_weather_event,
    get_claim_history,
    calculate_payout,
)

RATIONALE_INSTRUCTION = (
    "\n\nAlways end your response with a line starting exactly with "
    "'RATIONALE:' giving a one-sentence, plain-language reason for your "
    "conclusion. This is required for audit for regulatory explainability."
)

coverage_agent = Agent(
    name="coverage_agent",
    system_prompt=(
        "You are a claims coverage agent for an insurer. Given a customer ID "
        "and a claim description, use the lookup_policy tool to determine "
        "whether the claim is covered. State clearly COVERED or NOT COVERED."
        + RATIONALE_INSTRUCTION
    ),
    tools=[lookup_policy],
)

weather_agent = Agent(
    name="weather_agent",
    system_prompt=(
        "You are a weather verification agent. Given a region, date, and "
        "claimed outage duration, use verify_weather_event to confirm whether "
        "a matching severe weather event occurred and whether it meets the "
        "threshold for a claim. State clearly CONFIRMED or NOT CONFIRMED."
    ),
    tools=[verify_weather_event],
)

fraud_agent = Agent(
    name="fraud_agent",
    system_prompt=(
        "Your are a fraud-screening agent. Use get_claim_history to review the "
        "customer's past claims and assess whether this new claim looks "
        "suspicious (e.g. unusually frequent, inconsistent amounts). State "
        "clearly a risk level of LOW, MEDIUM, or HIGH."
        + RATIONALE_INSTRUCTION
    ),
    tools=[get_claim_history],
)

payout_agent = Agent(
    name="payout_agent",
    system_prompt=(
        "You are a payout calculation agent. Use calculate_payout with the "
        "claimed amount, policy limit, and deductible to determine the exact "
        "AUD payout. Report the final number clearly."
        + RATIONALE_INSTRUCTION
    ),
    tools=[calculate_payout],
)

audit_agent = Agent(
    name="audit_agent",
    system_prompt=(
        "You are an audit agent. You will be given the outputs of the "
        "coverage, weather, fraud, and payout agents for a single claim. "
        "Write a concise case summary a human claims reviewer can read in "
        "under 30 seconds, listing each agent's decision and rationale, and "
        "a final recommendation of APPROVE, DENY or ESCALATE."
        + RATIONALE_INSTRUCTION
    ),
    tools=[],
)

def build_pipeline() -> Orchestrator:
    orch = Orchestrator(name="claims_triage")

    orch.add_node("coverage", coverage_agent)
    orch.add_node("weather", weather_agent)
    orch.add_node("fraud", fraud_agent)
    orch.add_node("payout", payout_agent)
    orch.add_node("audit", _audit_node)   # plain function: assembles context, then calls audit_agent

    orch.add_edge(Orchestrator.START, "coverage")
    orch.add_edge("coverage", "weather")
    orch.add_edge("weather", "fraud")
    orch.add_edge("fraud", "audit", condition=lambda s: "HIGH" in s["fraud_agent_result"].text.upper())
    orch.add_edge("fraud", "payout")
    orch.add_edge("payout", "audit")
    orch.add_edge("audit", Orchestrator.END)

    return orch

def _audit_node(state: dict) -> dict:
    """Assembles prior agent outputs into context, then runs the audit agent."""
    parts = []
    for key in ["coverage_agent_result", "weather_agent_result", "fraud_agent_result", "payout_agent_result"]:
        if key in state:
            parts.append(f"{key}: {state[key].text}")
    context = "\n\n".join(parts)

    result = audit_agent.run(
        user_message="Summarize this claim for human review.",
        context={"agent_outputs": context},
        tracer=state.get("_tracer"),
    )
    return {"audit_agent_result": result}

def run_demo() -> None:
    tracer = Tracer()
    pipeline = build_pipeline()

    initial_state = {
        "task": (
            "Customer laura-001 is claiming AUD 250 for food spoilage caused "
            "by a power outage in Adelaide, SA, lasting 20 hours, on 2026-07-01."
        ),
        "context": {
            "customer_id": "laura-001",
            "region": "Adelaide",
            "date": "2026-07-01",
            "outage_hours": 20,
            "claimed_amount_aud": 250,
        },
    }

    final_state = pipeline.run(initial_state, tracer=tracer)

    print("\n=== CASE SUMMARY (for human reviewer) ===\n")
    print(final_state["audit_agent_result"].text)

    print("\n=== TRACE ===\n")
    print(tracer.summary())

if __name__ == "__main__":
    run_demo()
