# pico

A minimal multi-agent framework, built from scratch in pure Python on top of
the raw Anthropic API - no LangGraph, no CrewAI. Plus a demo app: a
scaled-down version of Allianz's "Nemo" multi-agent claims triage pipeline.

## Why build a framework instead of using LangGraph?

LangGraph and CrewAI are the right choice for production systems, but using
them without understanding what they're doing internally means I can wire
nodes together without being able to explain *why* a tool-use loop needs to
re-send tool results back to the model, or *how* a graph decides which edge
to follow. This project reimplements the core mechanics - schema generation
from a function signature, the tool=use request/response loop, and
conditional graph routing - in under 800 lines, so the whole thing is
readable in one sitting.

## Structure
```
pico-agents/
|-- tools.py        # @tool decorator: function -> Claude-compatible JSON schema
|-- agent.py        # Agent: system prompt + tools + the tool-use loop
|-- orchestrator.py # Orchestrator: minimal directed graph, conditional edges
|-- tracer.py       # Tracer: spans + timing for every agent/tool/handoff

demo/
|-- claim_tools.py       # deterministic tools: policy lookup, weather check, payout calc
|-- claims_pipeline.py   # 5-agent claims triage pipeline (coverage -> weather -> fraud -> payout -> audit)

tests/
|-- test_tool.py    # tool unit tests
|-- test_framework.py   # framework unit tests
```

## Design decisions worth calling out

- **Deterministic where determinism is correct.** Payout calculation and 
policy lookup are plain Python, not LLM calls - real dollar amounts and 
coverage rules shouldn't be left to a generative model. LLM reasoning is
reserved for the parts where language understanding adds value: fraud 
rationale, weather-event interpretation, audit summarization.
- **Every agent returns a rationale.** Insurance decisions need to be
explainable to a regulator and a human reviewer, not just correct - so the
`Agent` class extracts a structured `RATIONALE:` field from every response
rather than treating the agent's text as an opaque blob.
- **Conditional routing on real signals.** The claims pipeline routes a HIGH
fraud-risk claim straight to the audit agent, skipping the payout step
entirely - the same "if fraud agent flags something, escalate instead of
paying out" brach you'd want in a production Nemo-sytle system.
- **Cyber/planner roles are infrastructure, not agents.** In the demo, there
is no separate "cyber agent" LLM call - access control and orchestration
durability are treated as cross-cutting infrastructure concerns ( see the
architecture notes below), which is closer to how this would actually be
build at an insurer.

## Running the demo

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
python -m demo.claims_pipeline
```

his runs Laura's storm claim (AUD 250 food spoilage, 20-hour outage,
Adelaide) through the five-agent pipeline and prints a human-reviewer-ready
case summary plus a trace of every agent/tool call and its duration.

## Running the framework tests (no API key needed)

```bash
uv run pytest tests/test_tool.py -v
uv run pytest tests/test_framework.py -v
```

## What this would need to become production-grade

This is deliberately a portfolio-scale project. A real deployment would add:
durable workflow state (Step Functions/Temporal instead of an in-process
loop), each agent as an independently-deployed microservice with its own
IAM role, an append-only audit log instead of an in-memory dict, and
OpenTelemetry tracing instead of the lightweight `Tracer` here. See
`docs/enterprise-architecture.md` for the full mapping.