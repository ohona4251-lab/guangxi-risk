"""Node3: fetch and analyze monitoring placeholder."""

from __future__ import annotations

from typing import Any

from ...state import RiskWorkflowState


def fetch_and_analyze_monitoring(state: RiskWorkflowState) -> dict[str, Any]:
    """Read monitoring data and produce anomaly-analysis placeholders.

    Input dependencies:
    - monitoring_data

    Output fields:
    - anomaly_detected
    - anomaly_list
    - anomaly_summary
    """
    monitoring_data = state.get("monitoring_data", {})
    anomaly_detected = bool(monitoring_data.get("force_anomaly", False))
    anomaly_list = (
        [{"id": "placeholder-anomaly-1", "source": "monitoring_data"}]
        if anomaly_detected
        else []
    )
    return {
        "anomaly_detected": anomaly_detected,
        "anomaly_list": anomaly_list,
        "anomaly_summary": (
            "placeholder: anomaly detected from monitoring input"
            if anomaly_detected
            else "placeholder: no anomaly detected from monitoring input"
        ),
    }
