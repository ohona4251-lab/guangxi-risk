"""Node7: human review with interrupt/resume."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from ...state import RiskWorkflowState


def human_review(state: RiskWorkflowState) -> dict[str, Any]:
    """Human review node using LangGraph interrupt/resume semantics.

    Input dependencies:
    - review_payload
    - case_id
    - object_id

    Output fields:
    - review_decision
    - review_comment

    Notes:
    - This node pauses execution by calling interrupt(...).
    - Caller should resume with Command(resume={...}) and the same thread_id.
    - A checkpointer is required to persist and resume paused execution.
    """
    review_input = interrupt(
        {
            "case_id": state.get("case_id", ""),
            "object_id": state.get("object_id", ""),
            "review_payload": state.get("review_payload", {}),
            "message": "Please provide manual review decision: approved or rejected.",
        }
    )

    if isinstance(review_input, dict):
        decision = str(review_input.get("decision", "")).strip().lower()
        comment = str(review_input.get("comment", "")).strip()
    else:
        decision = str(review_input).strip().lower()
        comment = ""

    if decision not in {"approved", "rejected"}:
        decision = "rejected"
        if not comment:
            comment = "invalid or empty decision from reviewer input; fallback to rejected"

    return {
        "review_decision": decision,
        "review_comment": comment or f"manual review decision: {decision}",
    }
