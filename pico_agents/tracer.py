"""
Minimal tracer for pico-agents.

Records every agent call, tool invocation, and handoff with timing, so a 
multi-agent run can be reconstructed and inspected after the fact -- the 
same idea as OpenTelemetry spans, scoped down to what a portfolio demo needs.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Span:
    span_id: str
    kind: str  # "agent_run" | "tool_call" | "handoff"
    name: str
    start_ts: float
    end_ts: float | None = None
    input: Any = None
    output: Any = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.end_ts is None:
            return None
        return round((self.end_ts - self.start_ts) * 1000, 2)

class Tracer:
    """Collects spans for a single claim/task run."""
    
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.spans: list[Span] = []
        self._open_spans: dict[str, Span] = {}

    def start_span(self, kind: str, name: str, input: Any = None, **metadata) -> str:
        span_id = str(uuid.uuid4())
        span = Span(span_id=span_id, kind=kind, name=name, start_ts=time.time(),
                    input=input, metadata=metadata)
        self.spans.append(span)
        self._open_spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, output: Any = None) -> None:
        span = self._open_spans.pop(span_id, None)
        if span:
            span.end_ts = time.time()
            span.output = output
    
    def summary(self) -> str:
        """Human-readable timeline, useful for README demos are debugging."""
        lines = [f"Run {self.run_id}"]
        for s in self.spans:
            dur = f"{s.duration_ms}ms" if s.duration_ms is not None else "(open)"
            lines.append(f"  [{s.kind:10s}] {s.name:20s} {dur}")
        total = sum(s.duration_ms or 0 for s in self.spans if s.kind == "agent_run")
        lines.append(f"  total agent time: {round(total, 2)}ms")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "spans": [
                {
                    "span_id": s.span_id,
                    "kind": s.kind,
                    "name": s.name,
                    "duration_ms": s.duration_ms,
                    "input": s.input,
                    "output": s.output,
                    "metadata": s.metadata
                }
                for s in self.spans
            ],
        }