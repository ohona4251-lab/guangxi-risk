"""Node5: generate risk grade and basis placeholder."""

from __future__ import annotations

from typing import Any

from ...state import RiskWorkflowState


def generate_risk_grade_and_basis(state: RiskWorkflowState) -> dict[str, Any]:
    """Generate a candidate risk level and grading basis placeholders.

    Input dependencies:
    - parsed_rules
    - initial_kg / reconstructed_kg
    - anomaly_detected

    Output fields:
    - candidate_risk_level
    - grading_basis
    - explanation
    """
    anomaly_detected = bool(state.get("anomaly_detected", False))
    return {
        "candidate_risk_level": "candidate_high" if anomaly_detected else "candidate_normal",
        "grading_basis": {
            "status": "placeholder_grading_basis",
            "used_reconstructed_kg": bool(state.get("kg_updated", False)),
            "anomaly_detected": anomaly_detected,
        },
        "explanation": "placeholder explanation for candidate risk result",
    }
