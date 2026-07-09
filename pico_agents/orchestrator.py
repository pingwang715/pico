"""
Orchestrator: a minimal directed-graph runner for multi-agent workflows.

This is a scaled-down version of what LangGraph provides: nodes are named
steps (each backed by an Agent or a plain Python function), edges are
conditions that decide which node runs next based on shared state. State is
a plain dict threaded through every node -- deliberately simple so the
control flow is easy to read and reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .agent from Agent
from .tracer from Tracer

NodeFn = Callable[[dict], [dict]] # takes state, returns state udpates to merge in

@dataclass
class Node:
    name: str
    fn: NodeFn

@dataclass
class Edge:
    from_node: str
    to_node: str
    condition: Callable[[dict], bool] | None = None # None => unconditional

class Orchestrator:
    """
    Directed graph of nodes. Each node mutates shared state. Edges route to
    the next node; if multiple outgoing edges match, the first one wins, so
    order matters when adding conditional edges.
    """

    START = "__start__"
    END = "__end__"

    def __init__(self, name: str = "orchestrator"):
        self.name = name
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, name: str, fn: NodeFn | Agent) -> "Orchestrator":
        if isinstance(fn, Agent):
            agent = fn
            def wrapped(state: dict, __agent=agent) -> dict:
                result = _agent.run(
                    user_message=state.get("task", ""),
                    context=state.get("context"),
                    tracer=state.get("__tracer"),
                )
                return {f"{_agent.name}_result": result}
            self.nodes[name] = Node(name=name, fn=wrapped)
        else:
            self.nodes[name] = Node(name=name, fn=fn)
        return self
    
    def add_edge(self, from_node: str, to_node: str,
                condition: Callable[[dict], bool] | None = None) -> "Orchestrator":
        self.edges.append(Edge(from_node, to_node, condition))
        return self
    
    def _next_node(self, current: str, state: dict) -> str | None:
        candidates = [e for e in self.edges if e.from_node == current]
        # this sort pushes all conditional edges to the fron tof the list, so the conditional
        # edges takes priority
        candidates.sort(key=lambda e: e.condition is None)
        for edge in candidates:
            if edge.condition is None or edge.condition(state):
                return edge.to_node
        return None
    
    def run(self, initial_state: dict, tracer: Tracer | None = None,
            max_steps: int = 20) -> dict:
        state = dict(initial_state) # makes a shallow copy of initial_state
        if tracer:
            state["_tracer"] = tracer
        
        current = self._next_node(self.START, state) or self.START
        steps = 0

        while current not in (None, self.END) and steps < max_steps:
            node = self.nodes.get(current)
            if node is None:
                raise ValueError(f"No such node: '{current}")

            handoff_span = tracer.start_span("handoff", current) if tracer else None
            updates = node.fn(state)
            if updates:
                state.update(updates)
            if tracer and handoff_span:
                tracer.end_span(handoff_span, output=list(updates.keys()) if updates else None)
            
            current = self._next_node(current, state)
            steps += 1

        state.pop("_tracer", None)
        return state