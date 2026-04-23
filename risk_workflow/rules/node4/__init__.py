"""Node4: reconstruct KG with anomaly placeholder."""

from __future__ import annotations

from typing import Any

from ...state import RiskWorkflowState


def reconstruct_kg_with_anomaly(state: RiskWorkflowState) -> dict[str, Any]:
    """Reconstruct KG placeholder when anomaly branch is selected.

    Input dependencies:
    - initial_kg
    - anomaly_list

    Output fields:
    - reconstructed_kg
    - kg_updated
    """
    return {
        "reconstructed_kg": {
            "status": "placeholder_reconstructed_kg",
            "base_kg_present": bool(state.get("initial_kg")),
            "anomaly_count": len(state.get("anomaly_list", [])),
            "nodes": [],
            "edges": [],
        },
        "kg_updated": True,
    }
