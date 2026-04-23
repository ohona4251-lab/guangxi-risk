"""Node6: validate with history placeholder."""

from __future__ import annotations

from typing import Any

from ...state import RiskWorkflowState


def validate_with_history(state: RiskWorkflowState) -> dict[str, Any]:
    """Validate candidate result against history with placeholder logic.

    Input dependencies:
    - candidate_risk_level
    - grading_basis
    - history_records

    Output fields:
    - history_validation_report
    - validated_result
    - review_payload
    """
    history_records = state.get("history_records", [])
    report = {
        "status": "placeholder_history_validation",
        "history_count": len(history_records),
        "consistency": "unknown",
    }
    validated_result = {
        "candidate_risk_level": state.get("candidate_risk_level", "unknown"),
        "needs_manual_review": True,
    }
    return {
        "history_validation_report": report,
        "validated_result": validated_result,
        "review_payload": {
            "report": report,
            "validated_result": validated_result,
            "grading_basis": state.get("grading_basis", {}),
            "explanation": state.get("explanation", ""),
        },
    }
