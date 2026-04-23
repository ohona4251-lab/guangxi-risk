"""Minimal entrypoint for running the risk workflow graph."""

from __future__ import annotations

from pprint import pprint
from typing import Any
from uuid import uuid4

from langgraph.types import Command

from risk_workflow.graph import get_graph, sqlite_checkpointer
from risk_workflow.state import RiskWorkflowState


def build_sample_state() -> RiskWorkflowState:
    """Create a minimal sample state for the skeleton workflow."""
    return {
        "case_id": "case-001",
        "object_id": "slope-A-17",
        "raw_rule_docs": ["rule doc placeholder"],
        "inspection_text": "placeholder inspection description",
        "object_meta": {"region": "GX", "category": "slope"},
        "monitoring_data": {"force_anomaly": True},
        "history_records": [{"id": "hist-001", "result": "placeholder"}],
    }


def run() -> dict[str, Any]:
    """Run the graph with true interrupt/resume manual review flow.

    Demo sequence:
    1) Initial invoke reaches human_review and pauses.
    2) Resume with rejected decision to trigger update -> loop.
    3) Resume with approved decision to finish.
    """
    thread_id = f"demo-thread-interrupt-{uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = build_sample_state()
    demo_decisions = [
        {"decision": "rejected", "comment": "demo: please refine inspection rules"},
        {"decision": "approved", "comment": "demo: updated result is acceptable"},
    ]
    decision_index = 0

    with sqlite_checkpointer("data/checkpoints/risk_workflow.sqlite") as checkpointer:
        graph = get_graph(checkpointer=checkpointer)
        print(f"Using thread_id: {thread_id}")
        result = graph.invoke(initial_state, config=config)

        while "__interrupt__" in result:
            interrupt_info = result["__interrupt__"][0]
            print("\nExecution paused at human_review.")
            print("Interrupt payload:")
            pprint(interrupt_info.value, sort_dicts=False)

            if decision_index >= len(demo_decisions):
                raise RuntimeError(
                    "No more demo review decisions. Provide additional resume input."
                )
            resume_payload = demo_decisions[decision_index]
            decision_index += 1
            print("Resuming with manual decision:")
            pprint(resume_payload, sort_dicts=False)

            result = graph.invoke(Command(resume=resume_payload), config=config)

    return result


if __name__ == "__main__":
    final_state = run()
    print("Workflow finished. Final state:")
    pprint(final_state, sort_dicts=False)
