"""Node7: human review with interrupt/resume."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph.types import interrupt

from ...state import RiskWorkflowState

NODE7_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "node7"


def _safe_name(raw: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_") or "unknown"


def _persist_pending_review(state: RiskWorkflowState) -> str:
    """Persist the risk point payload that needs manual review."""
    NODE7_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = _safe_name(str(state.get("case_id", "unknown_case")))
    path = NODE7_OUTPUT_DIR / f"{case_id}_{ts}.json"
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "status": "pending_manual_review",
        "risk_point": {
            "object_meta": state.get("object_meta", {}),
            "monitoring_data": state.get("monitoring_data", {}),
            "inspection_text": state.get("inspection_text", ""),
        },
        "node6_input": {
            "candidate_risk_level": state.get("candidate_risk_level", ""),
            "grading_basis": state.get("grading_basis", {}),
            "explanation": state.get("explanation", ""),
            "history_validation_report": state.get("history_validation_report", {}),
            "validated_result": state.get("validated_result", {}),
            "review_payload": state.get("review_payload", {}),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (NODE7_OUTPUT_DIR / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


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
    pending_review_output_path = _persist_pending_review(state)
    review_input = interrupt(
        {
            "case_id": state.get("case_id", ""),
            "object_id": state.get("object_id", ""),
            "review_payload": state.get("review_payload", {}),
            "pending_review_output_path": pending_review_output_path,
            "message": "Please provide manual review decision: approved or rejected.",
        }
    )

    manual_review: dict[str, Any] = {}
    if isinstance(review_input, dict):
        manual_review = dict(review_input)
        decision = str(review_input.get("decision", "")).strip().lower()
        is_correct = review_input.get("is_correct")
        if decision not in {"approved", "rejected"} and isinstance(is_correct, bool):
            decision = "approved" if is_correct else "rejected"
        comment_parts = [
            str(review_input.get("comment", "")).strip(),
            str(review_input.get("basis", "")).strip(),
        ]
        comment = "\n".join(part for part in comment_parts if part)
    else:
        decision = str(review_input).strip().lower()
        comment = ""
        manual_review = {"decision": decision}

    if decision not in {"approved", "rejected"}:
        decision = "rejected"
        if not comment:
            comment = "invalid or empty decision from reviewer input; fallback to rejected"

    return {
        "review_decision": decision,
        "review_comment": comment or f"manual review decision: {decision}",
        "manual_review": manual_review,
        "pending_review_output_path": pending_review_output_path,
    }
