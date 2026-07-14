from pico_agents.orchestrator import Orchestrator

def test_orchestrator_linear_routing():
    calls = []

    def node_a(state):
        calls.append("a")
        return {"a_done": True}

    def node_b(state):
        calls.append("b")
        return {"b_done": True}
    
    orch = Orchestrator("test")
    orch.add_node("a", node_a)
    orch.add_node("b", node_b)
    orch.add_edge(Orchestrator.START, "a")
    orch.add_edge("a", "b")
    orch.add_edge("b", Orchestrator.END)

    final_state = orch.run({})
    assert calls == ["a", "b"]
    assert final_state["a_done"] is True
    assert final_state["b_done"] is True

def test_orchestrator_conditional_branch():
    """Mirrors the fraud->audit skip-payout branch in the claims demo."""
    visited = []

    def fraud(state):
        visited.append("fraud")
        return {"risk": state["risk_input"]}

    def payout(state):
        visited.append("payout")
        return {"paid": True}

    def audit(state):
        visited.append("audit")
        return {"audited": True}

    orch = Orchestrator("branch_test")
    orch.add_node("fraud", fraud)
    orch.add_node("payout", payout)
    orch.add_node("audit", audit)
    orch.add_edge(Orchestrator.START, "fraud")
    orch.add_edge("fraud", "audit", condition=lambda s: s["risk"] == "HIGH")
    orch.add_edge("fraud", "payout")
    orch.add_edge("payout", "audit")
    orch.add_edge("audit", Orchestrator.END)

    visited.clear()
    orch.run({"risk_input": "HIGH"})
    assert visited == ["fraud", "audit"] # payout skipped

    visited.clear()
    orch.run({"risk_input": "LOW"})
    assert visited == ["fraud", "payout", "audit"] # payout included

if __name__ == "__main__":
    test_orchestrator_linear_routing()
    test_orchestrator_conditional_branch()
    print("All tests passed.")