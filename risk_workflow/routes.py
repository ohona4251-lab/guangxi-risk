"""Routing functions used by conditional edges in the graph."""

from __future__ import annotations

from typing import Literal

from .state import RiskWorkflowState


def route_after_monitoring(
    state: RiskWorkflowState,
) -> Literal["reconstruct_kg_with_anomaly", "generate_risk_grade_and_basis"]:
    """Route after monitoring analysis based on anomaly flag."""
    if state.get("anomaly_detected", False):
        return "reconstruct_kg_with_anomaly"
    return "generate_risk_grade_and_basis"


def route_after_human_review(
    state: RiskWorkflowState,
) -> Literal["__end__", "update_inspection_rules"]:
    """Route after human review.

    approved -> end
    rejected (or any non-approved value) -> update_inspection_rules
    """
    decision = state.get("review_decision", "pending")
    if decision == "approved":
        return "__end__"
    return "update_inspection_rules"
