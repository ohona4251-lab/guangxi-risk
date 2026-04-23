"""Local HTTP API for the risk review UI.

The review UI works on already-produced grading data. It does not rerun
workflow nodes 1-5 when a reviewer opens the form.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from risk_workflow.rules.node6 import validate_with_history
from risk_workflow.rules.node7 import _persist_pending_review
from risk_workflow.state import RiskWorkflowState

ROOT = Path(__file__).resolve().parent
NODE7_OUTPUT_DIR = ROOT / "risk_workflow" / "outputs" / "node7"
NODE8_OUTPUT_DIR = ROOT / "risk_workflow" / "outputs" / "node8"
RULE_LIBRARY_DIR = ROOT / "risk_workflow" / "outputs" / "rule_library"
FRONT_REVIEW_SESSIONS: dict[str, RiskWorkflowState] = {}

load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")


def _json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    payload = json.loads(raw or "{}")
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _safe_name(raw: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_") or "unknown"


def _grade_result(point: dict[str, Any]) -> dict[str, Any]:
    grade_result = point.get("gradeResult")
    return grade_result if isinstance(grade_result, dict) else {}


def _state_from_point(point: dict[str, Any]) -> RiskWorkflowState:
    point_id = str(point.get("id") or point.get("object_id") or "front-review-case")
    grade_result = _grade_result(point)
    inspection_records = point.get("inspectionRecords") or point.get("inspection_records") or []
    monitoring_points = point.get("monitoringPoints") or point.get("monitoring_points") or []
    inspection_text_parts: list[str] = []
    if isinstance(inspection_records, list):
        for record in inspection_records:
            if isinstance(record, dict):
                inspection_text_parts.append(str(record.get("summary", "")).strip())

    candidate_level = (
        grade_result.get("level")
        or point.get("riskLevel")
        or point.get("risk_level")
        or "\u672a\u77e5"
    )
    explanation = grade_result.get("desc") or point.get("review", {}).get("text", "")
    if not explanation:
        explanation = "\u524d\u7aef\u5df2\u6709\u98ce\u9669\u5206\u7ea7\u7ed3\u679c\u3002"

    return {
        "case_id": f"front-review-{point_id}-{uuid4().hex[:8]}",
        "object_id": point_id,
        "raw_rule_docs": [],
        "inspection_text": "\n\n".join(part for part in inspection_text_parts if part)
        or str(point.get("inspectionSummary") or point.get("inspection_summary") or ""),
        "object_meta": {
            "name": point.get("name", ""),
            "type": point.get("type") or point.get("category") or "",
            "location": point.get("locationText") or point.get("location") or "",
            "risk_level": point.get("riskLevel") or point.get("risk_level") or candidate_level,
        },
        "monitoring_data": {
            "records": monitoring_points,
            "force_anomaly": any(
                isinstance(item, dict) and str(item.get("status", "")).strip() in {"\u5f02\u5e38", "\u544a\u8b66", "\u9884\u8b66"}
                for item in monitoring_points
            ),
        },
        "history_records": point.get("historyRecords") or point.get("history_records") or [],
        "candidate_risk_level": candidate_level,
        "grading_basis": {
            "source": "front_existing_result",
            "description": grade_result.get("desc", ""),
            "inspection_summary": point.get("inspectionSummary") or point.get("inspection_summary") or "",
            "monitoring_points": monitoring_points,
        },
        "explanation": explanation,
        "parsed_rules": {
            "\u5f53\u524d\u98ce\u9669\u5206\u7ea7\u89c4\u5219": "\u7531\u8282\u70b9\u4e00\u5230\u4e94\u7684\u5df2\u6267\u884c\u7ed3\u679c\u63d0\u4f9b\u3002"
        },
    }


def _review_state_from_payload(payload: dict[str, Any]) -> RiskWorkflowState:
    initial_state = payload.get("initial_state")
    if isinstance(initial_state, dict):
        state: RiskWorkflowState = dict(initial_state)
        state.setdefault("case_id", f"front-review-{uuid4().hex[:8]}")
        state.setdefault("object_id", state.get("case_id", "front-review-case"))
        return state

    point = payload.get("point")
    if not isinstance(point, dict):
        raise ValueError("point or initial_state is required")
    return _state_from_point(point)


def _write_review_result(thread_id: str, state: RiskWorkflowState) -> str:
    NODE7_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    case_id = _safe_name(str(state.get("case_id", thread_id)))
    path = NODE7_OUTPUT_DIR / f"{case_id}_review_result.json"
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "pending_review_output_path": state.get("pending_review_output_path", ""),
        "manual_review": state.get("manual_review", {}),
        "review_decision": state.get("review_decision", ""),
        "review_comment": state.get("review_comment", ""),
        "status": "completed" if state.get("review_decision") == "approved" else "rejected_go_node8",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError("model output does not contain a JSON object")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model output JSON is not an object")
    return parsed


def _llm_client(timeout: float = 120.0) -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ZAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY or ZAI_API_KEY is required")
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _call_review_revision_model(state: RiskWorkflowState) -> dict[str, Any]:
    model = os.getenv("OPENAI_MODEL", "glm-5")
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "risk_point": {
            "object_meta": state.get("object_meta", {}),
            "inspection_text": state.get("inspection_text", ""),
            "monitoring_data": state.get("monitoring_data", {}),
        },
        "previous_result": {
            "candidate_risk_level": state.get("candidate_risk_level", ""),
            "grading_basis": state.get("grading_basis", {}),
            "explanation": state.get("explanation", ""),
            "history_validation_report": state.get("history_validation_report", {}),
            "validated_result": state.get("validated_result", {}),
            "review_payload": state.get("review_payload", {}),
        },
        "previous_rules": state.get("parsed_rules", {}),
        "manual_review": state.get("manual_review", {}),
        "review_comment": state.get("review_comment", ""),
    }
    system = (
        "你是公路基础设施风险分级规则复核助手。"
        "你只处理节点7和节点8：节点1到节点5已经执行完成，不能重新生成前序结果，不能改写节点2规则文件。"
        "当人工复核判定原结果错误时，你需要根据人工复核依据，提出规则调整建议，并用建议规则重新判断当前风险点。"
        "必须只输出JSON对象，不要输出解释性正文。"
    )
    user = (
        "请基于以下已完成的风险分级结果和人工复核依据，输出JSON，字段必须包括：\n"
        "updated_rules: 对原规则的建议修订结果；\n"
        "changes: 数组，每项包含 path、before、after、reason；\n"
        "rationale: 为什么这样调整；\n"
        "rerun_result: 对当前风险点按建议规则重新执行后的结果，包含 candidate_risk_level_before、candidate_risk_level_after、basis_after。\n"
        "注意：updated_rules只是建议，不要声称已经写入节点2。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    client = _llm_client()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
    content = completion.choices[0].message.content or "{}"
    parsed = _extract_json_object(content)
    changes = parsed.get("changes", [])
    if not isinstance(changes, list):
        changes = []
    rerun_result = parsed.get("rerun_result", {})
    if not isinstance(rerun_result, dict):
        rerun_result = {}
    return {
        "updated_rules": parsed.get("updated_rules", state.get("parsed_rules", {})),
        "changes": changes,
        "rationale": str(parsed.get("rationale", "")).strip(),
        "rerun_result": rerun_result,
        "model": model,
    }


def _propose_rule_revision(state: RiskWorkflowState) -> dict[str, Any]:
    try:
        return _call_review_revision_model(state)
    except Exception as exc:
        return _fallback_rule_revision(state, exc)


def _fallback_rule_revision(state: RiskWorkflowState, error: Exception) -> dict[str, Any]:
    manual_review = state.get("manual_review", {})
    manual_grade = str(manual_review.get("manual_grade") or "")
    before_level = str(state.get("candidate_risk_level", ""))
    after_level = manual_grade or before_level
    basis = str(manual_review.get("basis") or manual_review.get("comment") or state.get("review_comment") or "")
    conclusion = str(manual_review.get("conclusion") or "\u4eba\u5de5\u590d\u6838\u5224\u5b9a\u539f\u7ed3\u679c\u4e0d\u6b63\u786e")

    rule_name = f"{state.get('object_meta', {}).get('type', '\u98ce\u9669\u70b9')}-\u4eba\u5de5\u590d\u6838\u4fee\u6b63"
    previous_rule = str(state.get("parsed_rules", {}).get(rule_name, "\u6682\u65e0\u5bf9\u5e94\u4eba\u5de5\u590d\u6838\u4fee\u6b63\u89c4\u5219"))
    proposed_rule = (
        f"\u5f53\u4eba\u5de5\u590d\u6838\u7ed3\u8bba\u4e3a\u201c{conclusion}\u201d\uff0c"
        f"\u4e14\u590d\u6838\u4f9d\u636e\u652f\u6301\u98ce\u9669\u7b49\u7ea7\u7531{before_level}\u8c03\u6574\u4e3a{after_level}\u65f6\uff0c"
        f"\u8be5\u98ce\u9669\u70b9\u5efa\u8bae\u6309{after_level}\u91cd\u65b0\u8f93\u51fa\u3002"
    )
    updated_rules = dict(state.get("parsed_rules", {}))
    updated_rules[rule_name] = proposed_rule

    revision = {
        "updated_rules": updated_rules,
        "changes": [
            {
                "path": rule_name,
                "before": previous_rule,
                "after": proposed_rule,
                "reason": basis or "\u4eba\u5de5\u590d\u6838\u5224\u5b9a\u539f\u7ed3\u679c\u4e0d\u6b63\u786e\u3002",
            }
        ],
        "rationale": (
            "\u5927\u6a21\u578b\u8c03\u7528\u5931\u8d25\uff0c\u5df2\u6839\u636e\u4eba\u5de5\u590d\u6838\u4f9d\u636e"
            "\u751f\u6210\u4fdd\u5e95\u89c4\u5219\u8c03\u6574\u5efa\u8bae\uff1b\u4ec5\u5199\u5165\u8282\u70b9\u516b\u8f93\u51fa\uff0c"
            "\u4e0d\u6539\u5199\u8282\u70b9\u4e8c\u89c4\u5219\u3002"
        ),
        "rerun_result": {
            "candidate_risk_level_before": before_level,
            "candidate_risk_level_after": after_level,
            "basis_after": basis or "\u4eba\u5de5\u590d\u6838\u5224\u5b9a\u539f\u7ed3\u679c\u4e0d\u6b63\u786e\u3002",
        },
        "model": os.getenv("OPENAI_MODEL", "glm-5"),
        "error": str(error),
    }
    return revision


def _write_node8_revision(state: RiskWorkflowState, revision: dict[str, Any]) -> str:
    NODE8_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = _safe_name(str(state.get("case_id", "unknown_case")))
    path = NODE8_OUTPUT_DIR / f"{case_id}_{ts}_rule_revision.json"
    manual_review = state.get("manual_review", {})
    rerun_result = revision.get("rerun_result") if isinstance(revision.get("rerun_result"), dict) else {}
    rerun_result.setdefault("candidate_risk_level_before", state.get("candidate_risk_level", ""))
    rerun_result.setdefault(
        "candidate_risk_level_after",
        manual_review.get("manual_grade") or state.get("candidate_risk_level", ""),
    )
    rerun_result.setdefault("basis_after", manual_review.get("basis") or state.get("review_comment", ""))
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "pending_review_output_path": state.get("pending_review_output_path", ""),
        "adjusted_risk_point": {
            "object_meta": state.get("object_meta", {}),
            "candidate_risk_level": state.get("candidate_risk_level", ""),
            "manual_grade": manual_review.get("manual_grade", ""),
            "validated_result": state.get("validated_result", {}),
        },
        "manual_review": manual_review,
        "revision": revision,
        "rerun_result": rerun_result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (NODE8_OUTPUT_DIR / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    state["rerun_result"] = rerun_result
    return str(path)


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def list_review_history() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    revisions_by_object: dict[str, dict[str, Any]] = {}
    if NODE8_OUTPUT_DIR.exists():
        for path in NODE8_OUTPUT_DIR.glob("*_rule_revision.json"):
            data = _read_json_file(path)
            object_id = str(data.get("object_id", ""))
            if object_id:
                revisions_by_object[object_id] = data
    if NODE7_OUTPUT_DIR.exists():
        for path in NODE7_OUTPUT_DIR.glob("*_review_result.json"):
            data = _read_json_file(path)
            object_id = str(data.get("object_id", ""))
            revision_data = revisions_by_object.get(object_id, {})
            revision = revision_data.get("revision", {}) if isinstance(revision_data.get("revision"), dict) else {}
            items.append(
                {
                    "id": path.stem,
                    "type": "review",
                    "title": f"{data.get('object_id', path.stem)} \u590d\u6838\u7ed3\u679c",
                    "saved_at": data.get("saved_at", ""),
                    "path": str(path),
                    "summary": {
                        "review_decision": data.get("review_decision", ""),
                        "review_comment": data.get("review_comment", ""),
                        "manual_review": data.get("manual_review", {}),
                        "changes": revision.get("changes", []),
                        "rationale": revision.get("rationale", ""),
                        "rerun_result": revision_data.get("rerun_result", {}),
                    },
                }
            )
    if NODE8_OUTPUT_DIR.exists():
        for path in NODE8_OUTPUT_DIR.glob("*_rule_revision.json"):
            data = _read_json_file(path)
            revision = data.get("revision", {}) if isinstance(data.get("revision"), dict) else {}
            items.append(
                {
                    "id": path.stem,
                    "type": "rule_revision",
                    "title": f"{data.get('object_id', path.stem)} \u89c4\u5219\u8c03\u6574",
                    "saved_at": data.get("saved_at", ""),
                    "path": str(path),
                    "summary": {
                        "manual_review": data.get("manual_review", {}),
                        "changes": revision.get("changes", []),
                        "rationale": revision.get("rationale", ""),
                        "rerun_result": data.get("rerun_result", {}),
                    },
                }
            )
    items.sort(key=lambda item: str(item.get("saved_at", "")), reverse=True)
    return {"items": items[:50]}


def commit_rules(payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = str(payload.get("thread_id") or "").strip()
    state = FRONT_REVIEW_SESSIONS.get(thread_id)
    if state is None:
        raise ValueError("review session not found; submit a review first")
    revision = state.get("rule_revision", {})
    if not isinstance(revision, dict) or not revision.get("updated_rules"):
        raise ValueError("no rule revision is available to commit")

    RULE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    rules_path = RULE_LIBRARY_DIR / "rules.json"
    log_path = RULE_LIBRARY_DIR / "commit_log.jsonl"
    commit_payload = {
        "committed_at": datetime.now().isoformat(timespec="seconds"),
        "thread_id": thread_id,
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "source_output_path": revision.get("output_path", ""),
        "updated_rules": revision.get("updated_rules", {}),
        "changes": revision.get("changes", []),
        "rationale": revision.get("rationale", ""),
        "model": revision.get("model", ""),
    }
    rules_path.write_text(json.dumps(commit_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(commit_payload, ensure_ascii=False) + "\n")
    state["rule_commit_path"] = str(rules_path)
    return {
        "status": "committed",
        "rule_library_path": str(rules_path),
        "log_path": str(log_path),
    }


def start_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    state = _review_state_from_payload(payload)
    state.update(validate_with_history(state))
    pending_review_output_path = _persist_pending_review(state)
    state["pending_review_output_path"] = pending_review_output_path

    thread_id = str(payload.get("thread_id") or state.get("case_id") or f"front-review-{uuid4().hex[:8]}")
    FRONT_REVIEW_SESSIONS[thread_id] = state
    return {
        "thread_id": thread_id,
        "status": "awaiting_review",
        "interrupt": {
            "case_id": state.get("case_id", ""),
            "object_id": state.get("object_id", ""),
            "review_payload": state.get("review_payload", {}),
            "pending_review_output_path": pending_review_output_path,
            "message": "\u5df2\u57fa\u4e8e\u73b0\u6709\u6267\u884c\u7ed3\u679c\u751f\u6210\u8282\u70b9\u4e03\u590d\u6838\u8f93\u5165\u3002",
        },
        "state": state,
    }


def submit_review(payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = str(payload.get("thread_id") or "").strip()
    if not thread_id:
        raise ValueError("thread_id is required")

    review = payload.get("review")
    if not isinstance(review, dict):
        raise ValueError("review is required")

    state = FRONT_REVIEW_SESSIONS.get(thread_id)
    if state is None:
        raise ValueError("review session not found; open the review form again")

    is_correct = bool(review.get("is_correct"))
    decision = "approved" if is_correct else "rejected"
    comment_parts = [
        str(review.get("comment", "")).strip(),
        str(review.get("basis", "")).strip(),
    ]
    state.update(
        {
            "review_decision": decision,
            "review_comment": "\n".join(part for part in comment_parts if part)
            or f"manual review decision: {decision}",
            "manual_review": {
                "decision": decision,
                "is_correct": is_correct,
                "manual_grade": review.get("manual_grade", ""),
                "conclusion": review.get("conclusion", ""),
                "basis": review.get("basis", ""),
                "comment": review.get("comment", ""),
            },
        }
    )
    review_result_path = _write_review_result(thread_id, state)
    state["review_result_path"] = review_result_path

    if decision == "approved":
        FRONT_REVIEW_SESSIONS[thread_id] = state
        return {
            "thread_id": thread_id,
            "status": "completed",
            "interrupt": None,
            "state": state,
        }

    revision = _propose_rule_revision(state)
    output_path = _write_node8_revision(state, revision)
    state["updated_rules"] = revision["updated_rules"]
    state["rule_revision"] = revision | {"output_path": output_path}
    changes = revision.get("changes", [])
    if not isinstance(changes, list):
        changes = []
    state["rule_update_log"] = [
        {
            "status": "rule_revision_proposed",
            "reason": state.get("review_comment", ""),
            "change_count": len(changes),
            "changes": changes,
            "rationale": revision.get("rationale", ""),
            "output_path": output_path,
        }
    ]
    rerun_level = state.get("rerun_result", {}).get("candidate_risk_level_after")
    if not rerun_level:
        rerun_level = state.get("manual_review", {}).get("manual_grade") or state.get("candidate_risk_level", "")
    state["review_payload"] = {
        "report": state.get("history_validation_report", {}),
        "validated_result": {
            "candidate_risk_level": rerun_level,
            "needs_manual_review": True,
        },
        "grading_basis": state.get("grading_basis", {}),
        "explanation": state.get("rerun_result", {}).get("basis_after", ""),
    }
    FRONT_REVIEW_SESSIONS[thread_id] = state
    return {
        "thread_id": thread_id,
        "status": "awaiting_review",
        "interrupt": {
            "case_id": state.get("case_id", ""),
            "object_id": state.get("object_id", ""),
            "review_payload": state.get("review_payload", {}),
            "pending_review_output_path": state.get("pending_review_output_path", ""),
            "message": "\u8282\u70b9\u516b\u5df2\u751f\u6210\u89c4\u5219\u8c03\u6574\u5efa\u8bae\uff0c\u5e76\u8f93\u51fa\u91cd\u65b0\u6267\u884c\u7ed3\u679c\u3002",
        },
        "state": state,
    }


class RiskRequestHandler(SimpleHTTPRequestHandler):
    """Serve front-end assets and review API endpoints."""

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/":
            path = "/front/index.html"
        return str(ROOT / path.lstrip("/"))

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        if self.path.startswith("/front/") or self.path == "/":
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/api/review/history":
            _json_response(self, HTTPStatus.OK, list_review_history())
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            payload = _read_json(self)
            if self.path == "/api/workflow/start":
                _json_response(self, HTTPStatus.OK, start_workflow(payload))
                return
            if self.path == "/api/workflow/review":
                _json_response(self, HTTPStatus.OK, submit_review(payload))
                return
            if self.path == "/api/rules/commit":
                _json_response(self, HTTPStatus.OK, commit_rules(payload))
                return
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})
        except Exception as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def guess_type(self, path: str) -> str:
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), RiskRequestHandler)
    print(f"Serving risk review UI at http://{host}:{port}/front/")
    print(f"Review API available at http://{host}:{port}/api/workflow/start")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve risk review UI and API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run(host=args.host, port=args.port)
