"""Node8: revise inspection rules from manual review feedback."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from ...state import RiskWorkflowState

load_dotenv()

NODE8_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "node8"


def _safe_name(raw: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_") or "unknown"


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


def _client(timeout: float = 120.0) -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _build_revision_prompt(state: RiskWorkflowState) -> list[dict[str, str]]:
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "pending_review_output_path": state.get("pending_review_output_path", ""),
        "previous_rules": state.get("parsed_rules", {}),
        "node6_review_payload": state.get("review_payload", {}),
        "manual_review": state.get("manual_review", {}),
        "review_comment": state.get("review_comment", ""),
    }
    system = (
        "你是公路基础设施风险分级规则修订助手。"
        "请只根据人工复核依据修订已有规则，不要编造依据。"
        "输出必须是 JSON 对象，包含 updated_rules、changes、rationale 三个字段。"
        "changes 是数组，每项包含 path、before、after、reason。"
        "如果依据不足以修改规则，updated_rules 返回原规则，changes 返回空数组，并在 rationale 说明原因。"
    )
    user = (
        "请根据以下工作流状态修订规则，并明确列出改动位置。\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _revise_rules_with_llm(state: RiskWorkflowState) -> dict[str, Any]:
    model = os.getenv("OPENAI_MODEL", "glm-5")
    messages = _build_revision_prompt(state)
    client = _client()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )
    content = completion.choices[0].message.content or "{}"
    parsed = _extract_json_object(content)
    updated_rules = parsed.get("updated_rules", state.get("parsed_rules", {}))
    changes = parsed.get("changes", [])
    if not isinstance(changes, list):
        changes = []
    return {
        "updated_rules": updated_rules,
        "changes": changes,
        "rationale": str(parsed.get("rationale", "")).strip(),
        "model": model,
    }


def _fallback_revision(state: RiskWorkflowState, error: Exception) -> dict[str, Any]:
    previous_rules = state.get("parsed_rules", {})
    comment = state.get("review_comment", "")
    manual_review = state.get("manual_review", {})
    return {
        "updated_rules": previous_rules,
        "changes": [],
        "rationale": (
            "规则修订模型调用失败，暂未自动改写规则；已记录人工复核依据，"
            "可在模型服务恢复后重新提交。"
        ),
        "model": os.getenv("OPENAI_MODEL", "glm-5"),
        "error": str(error),
        "manual_review": manual_review,
        "review_comment": comment,
    }


def _persist_revision(state: RiskWorkflowState, revision: dict[str, Any]) -> str:
    NODE8_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = _safe_name(str(state.get("case_id", "unknown_case")))
    path = NODE8_OUTPUT_DIR / f"{case_id}_{ts}.json"
    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "pending_review_output_path": state.get("pending_review_output_path", ""),
        "adjusted_risk_point": {
            "object_meta": state.get("object_meta", {}),
            "candidate_risk_level": state.get("candidate_risk_level", ""),
            "grading_basis": state.get("grading_basis", {}),
            "validated_result": state.get("validated_result", {}),
        },
        "review_comment": state.get("review_comment", ""),
        "manual_review": state.get("manual_review", {}),
        "revision": revision,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (NODE8_OUTPUT_DIR / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def update_inspection_rules(state: RiskWorkflowState) -> dict[str, Any]:
    """Propose rule revisions after rejected review without mutating node2 input rules."""
    existing_log = list(state.get("rule_update_log", []))

    try:
        revision = _revise_rules_with_llm(state)
    except Exception as exc:
        revision = _fallback_revision(state, exc)

    output_path = _persist_revision(state, revision)
    changes = revision.get("changes", [])
    update_entry = {
        "status": "rule_revision_proposed",
        "reason": state.get("review_comment", "no review comment"),
        "change_count": len(changes) if isinstance(changes, list) else 0,
        "changes": changes,
        "rationale": revision.get("rationale", ""),
        "output_path": output_path,
    }
    if revision.get("error"):
        update_entry["status"] = "rule_revision_failed"
        update_entry["error"] = revision["error"]
    existing_log.append(update_entry)

    updated_rules = revision.get("updated_rules", state.get("parsed_rules", {}))
    return {
        "updated_rules": updated_rules,
        "rule_revision": revision | {"output_path": output_path},
        "rule_update_log": existing_log,
    }
