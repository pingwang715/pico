# From portfolio demo to enterprise architecture

| This project | Production equivalent |
| ---|--- |
| `Orchestrator.run()` in-process loop | AWS Step Functions or Temporal - durable execution, survives pod restarts |
| `Tracer` (in-memory spans) | OpenTelemetry, exported to Jaeger/Datadog |
| Each `Agent` as a Python object | Independently deployed microservice, own IAM role, own scaling policy |
| `claim_tools.py` in-memory dicts | Policy DB (Postgres), external weather API, fraud-socring model (SageMaker) |
| `RATIONALE` text field | Structured explainability requirement for regulators (APRA/ASIC in Australia) |
| No separate cyber agent | API gateway + service mesh (Istio/mTLS) + IAM scoping - security is cross-cutting infra, not a reasoning step |
| Audit agent output printed to console | Cased pushed to a claims-review queue (Pega/Salesforce Service Cloud or internal UI) for the human decision |
| Single-process conditional routing | Same conditional-edge idea, but edges can trigger parallel branches, retries, and dead-letter queues |

## Why this mapping matters

The point of building the minimal version first is to prove the control
flow is correct before adding infrastructure weight. Every one of the 
production substitutes above is a drop-in replacement for a piece that
already has a clear interface here (`Orchestrator`, `Tracer`, `Agent`) -
nothing about the demo's logic would need to change to swap the backing
implementation.


