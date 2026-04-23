"""State schema for the risk workflow graph."""

from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class RiskWorkflowState(TypedDict, total=False):
    """Unified graph state used by all workflow nodes."""

    case_id: str
    object_id: str

    # Input payloads
    raw_rule_docs: list[str]
    inspection_text: str
    object_meta: dict[str, Any]
    monitoring_data: dict[str, Any]
    history_records: list[dict[str, Any]]

    # Rule-related fields
    parsed_rules: dict[str, Any]
    updated_rules: dict[str, Any]
    required_info: list[str]
    rule_update_log: list[dict[str, Any]]

    # KG-related fields
    initial_kg: dict[str, Any]
    reconstructed_kg: dict[str, Any]
    kg_updated: bool

    # Monitoring anomaly-related fields
    anomaly_detected: bool
    anomaly_list: list[dict[str, Any]]
    anomaly_summary: str

    # Risk grading-related fields
    candidate_risk_level: str
    grading_basis: dict[str, Any]
    explanation: str

    # History validation-related fields
    history_validation_report: dict[str, Any]
    validated_result: dict[str, Any]

    # Human review-related fields
    review_payload: dict[str, Any]
    review_decision: str
    review_comment: str
    manual_review: dict[str, Any]
    pending_review_output_path: str
    rule_revision: dict[str, Any]
