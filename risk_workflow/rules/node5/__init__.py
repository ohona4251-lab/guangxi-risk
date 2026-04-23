"""Node5: generate risk grade and basis from existing rules and KG artifacts."""

from __future__ import annotations

from typing import Any

from ...grading.engine import Point, grade_point, _load_rules, _monitor_kg_paths_by_point
from ...state import RiskWorkflowState


def generate_risk_grade_and_basis(state: RiskWorkflowState) -> dict[str, Any]:
    """Generate a candidate risk level and grading basis.

    Input dependencies:
    - parsed_rules
    - initial_kg / reconstructed_kg
    - anomaly_detected

    Output fields:
    - candidate_risk_level
    - grading_basis
    - explanation
    """
    object_meta = state.get("object_meta", {})
    point = Point(
        id=str(state.get("object_id") or object_meta.get("id") or "unknown"),
        name=str(object_meta.get("name") or state.get("object_id") or "unknown"),
        subject_type=str(object_meta.get("category") or object_meta.get("type") or ""),
        location=str(object_meta.get("location") or ""),
        lnglat=object_meta.get("lnglat"),
    )
    rules = state.get("parsed_rules")
    if not isinstance(rules, dict) or not rules:
        rules = _load_rules()
    if "merged" in rules and isinstance(rules["merged"], dict):
        rules = rules["merged"]

    result = grade_point(point, rules, _monitor_kg_paths_by_point())
    return {
        "candidate_risk_level": result["risk_level"],
        "grading_basis": result["grading_basis"],
        "explanation": result["explanation"],
    }
