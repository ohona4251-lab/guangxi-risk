"""Node1: parse inspection rules using per-document prompt extraction."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

from ...state import RiskWorkflowState

load_dotenv()

PROMPT_TEMPLATE = """你是“公路基础设施风险规则抽取助手”。

你的任务是：从输入的规则、指南、标准、规范文本中，抽取并生成以下结构化内容：

“灾害类型” : {
"灾害判断依据": "",
"需要收集的信息": "",
"风险分级规则": ""
}

【总体要求】

1. 仅依据输入文本抽取，不要补充任何外部知识、常识推断或行业经验。
2. 尽量按照原文表述抽取，不要随意改写，不要加入原文没有的信息。
3. 输出要简洁、结构化，不要写成长篇解释。
4. 不同灾害类型必须分别归类，不要混在一起。
5. 如果某类灾害在原文中没有明确给出风险分级规则，则填写：“原文未明确给出具体分级规则”。
6. 如果某类灾害在原文中没有明确给出灾害判断依据或需要收集的信息，则填写：“原文未明确给出”。

【抽取逻辑】

1. 灾害类型

* 从文本中抽取该主体下涉及的灾害或隐患类型。
* 每一种灾害类型单独作为一个键。
* 灾害类型名称尽量采用原文用语。

2. 灾害判断依据

* 针对每一种灾害类型，抽取原文中与其直接相关的崩塌识别的判断依据、灾害的一般规定等。
* 不同灾害类型分别归类，不要混在一起。
* 如果有多条内容，可以整合为一个清晰的字符串，使用分号或换行连接。

3. 需要收集的信息

* 针对每一种灾害类型，抽取原文中明确出现的辨识要点、灾害成因、调查项、信息收集表内容等。
* 可以按原文已有结构整理；如果原文没有明显结构，则直接顺序整理。
* 如果有多条内容，可以整合为一个清晰的字符串，使用分号或换行连接。

4. 风险分级规则

* 针对每一种灾害类型，抽取原文中明确给出的等级划分、等级定义、分级判定依据、对应后果等内容。
* 如果原文没有明确给出，则填写：“原文未明确给出具体分级规则”。

【输出格式要求】

1. 输出必须是一个 JSON 对象。
2. JSON 的最外层以“灾害类型”为键，以对应内容为值。
3. 每个灾害类型对应的值必须严格包含以下三个字段：

   * "灾害判断依据"
   * "需要收集的信息"
   * "风险分级规则"
4. 所有字段内容均使用字符串形式输出。
5. 只输出 JSON，不要输出任何解释、说明、前言、总结或 Markdown 代码块。

【输出示例格式】
{
"崩塌": {
"灾害判断依据": "……",
"需要收集的信息": "……",
"风险分级规则": "……"
},
"滑坡": {
"灾害判断依据": "……",
"需要收集的信息": "……",
"风险分级规则": "……"
}
}
"""

MISSING_GENERAL = "原文未明确给出"
MISSING_GRADE = "原文未明确给出具体分级规则"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
NODE1_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "node1"


@dataclass
class ExtractionConfig:
    """Runtime config for prompt extraction."""

    model: str
    max_input_chars: int
    timeout: float


def _log(message: str) -> None:
    """Print node1 progress logs with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[node1 {ts}] {message}", flush=True)


def _safe_name(raw: str) -> str:
    """Convert filename/string to filesystem-safe name."""
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_") or "unknown"


def _read_pdf_text(path: Path) -> str:
    """Extract plain text from a PDF file."""
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _read_text_file(path: Path) -> str:
    """Read text file with utf-8 fallback decoding."""
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _iter_supported_docs(docs_dir: Path) -> list[Path]:
    """List supported documents under docs_dir."""
    if not docs_dir.exists():
        raise FileNotFoundError(f"docs_dir not found: {docs_dir}")
    files = sorted(
        [p for p in docs_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )
    if not files:
        raise FileNotFoundError(f"no supported docs found in {docs_dir}")
    return files


def _load_doc_payloads(docs_dir: Path) -> list[tuple[str, str]]:
    """Load each supported document as an independent payload."""
    payloads: list[tuple[str, str]] = []
    for file in _iter_supported_docs(docs_dir):
        if file.suffix.lower() == ".pdf":
            text = _read_pdf_text(file)
        else:
            text = _read_text_file(file)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        payloads.append((file.name, text))
    return payloads


def _build_user_prompt(source_text: str, max_input_chars: int) -> str:
    """Build final user message from extracted source text."""
    if len(source_text) > max_input_chars:
        source_text = source_text[:max_input_chars]
    return (
        "请基于以下文档文本执行抽取，严格遵守上面的全部规则，只输出 JSON。\n\n"
        f"{source_text}"
    )


def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Parse JSON object from model output text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError("model output does not contain a JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model output JSON is not an object")
    return data


def _normalize_output(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Normalize model output into required schema."""
    if "灾害类型" in data and isinstance(data["灾害类型"], dict):
        data = data["灾害类型"]
    normalized: dict[str, dict[str, str]] = {}
    for disaster_type, payload in data.items():
        base = payload if isinstance(payload, dict) else {}
        judgement = str(base.get("灾害判断依据", "")).strip() or MISSING_GENERAL
        collect_info = str(base.get("需要收集的信息", "")).strip() or MISSING_GENERAL
        grade = str(base.get("风险分级规则", "")).strip() or MISSING_GRADE
        normalized[str(disaster_type)] = {
            "灾害判断依据": judgement,
            "需要收集的信息": collect_info,
            "风险分级规则": grade,
        }
    return normalized


def _get_openai_client(timeout: float) -> OpenAI:
    """Build OpenAI-compatible client from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    client_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url
    return OpenAI(**client_kwargs)


def _run_prompt_extraction(source_text: str, config: ExtractionConfig) -> dict[str, dict[str, str]]:
    """Run prompt extraction against LLM and return normalized rules."""
    client = _get_openai_client(timeout=config.timeout)
    user_prompt = _build_user_prompt(source_text, config.max_input_chars)
    messages = [
        {"role": "system", "content": PROMPT_TEMPLATE},
        {"role": "user", "content": user_prompt},
    ]
    try:
        completion = client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception:
        completion = client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=0,
        )
    content = completion.choices[0].message.content or "{}"
    parsed = _extract_json_from_text(content)
    return _normalize_output(parsed)


def _merge_doc_rules(
    per_doc_rules: dict[str, dict[str, dict[str, str]]],
) -> dict[str, dict[str, str]]:
    """Merge per-document extraction results into one consolidated map."""

    def _merge_field(old: str, new: str) -> str:
        if not old:
            return new
        if not new or new == old:
            return old
        return f"{old}\n---\n{new}"

    merged: dict[str, dict[str, str]] = {}
    for doc_rules in per_doc_rules.values():
        for disaster_type, fields in doc_rules.items():
            current = merged.setdefault(
                disaster_type,
                {
                    "灾害判断依据": MISSING_GENERAL,
                    "需要收集的信息": MISSING_GENERAL,
                    "风险分级规则": MISSING_GRADE,
                },
            )
            for key in ("灾害判断依据", "需要收集的信息", "风险分级规则"):
                incoming = fields.get(key, "")
                if incoming:
                    current[key] = _merge_field(current.get(key, ""), incoming)
    return merged


def _derive_required_info(parsed_rules: dict[str, Any]) -> list[str]:
    """Derive a flattened required_info list from parsed rules."""
    by_doc = parsed_rules.get("by_doc") if isinstance(parsed_rules, dict) else None
    if isinstance(by_doc, dict):
        iterable = by_doc.values()
    else:
        iterable = [parsed_rules] if isinstance(parsed_rules, dict) else []

    required: list[str] = []
    for doc_rules in iterable:
        if not isinstance(doc_rules, dict):
            continue
        for payload in doc_rules.values():
            if not isinstance(payload, dict):
                continue
            text = payload.get("需要收集的信息", "")
            if not text or text == MISSING_GENERAL:
                continue
            for part in re.split(r"[;\n；]+", text):
                item = part.strip()
                if item:
                    required.append(item)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in required:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped or [MISSING_GENERAL]


def _persist_node1_output(
    parsed_rules: dict[str, Any],
    required_info: list[str],
    state: RiskWorkflowState,
) -> None:
    """Persist node1 output to risk_workflow/outputs/node1 by default."""
    NODE1_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    by_doc_dir = NODE1_OUTPUT_DIR / "by_doc"
    by_doc_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id = str(state.get("case_id", "unknown_case")).strip() or "unknown_case"
    safe_case_id = _safe_name(case_id)

    payload = {
        "case_id": state.get("case_id", ""),
        "object_id": state.get("object_id", ""),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "parsed_rules": parsed_rules,
        "required_info": required_info,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    (NODE1_OUTPUT_DIR / "latest.json").write_text(content, encoding="utf-8")
    (NODE1_OUTPUT_DIR / f"{safe_case_id}_{ts}.json").write_text(content, encoding="utf-8")

    by_doc = parsed_rules.get("by_doc", {}) if isinstance(parsed_rules, dict) else {}
    if isinstance(by_doc, dict):
        for doc_name, doc_rules in by_doc.items():
            safe_doc = _safe_name(doc_name)
            per_doc_payload = {
                "case_id": state.get("case_id", ""),
                "object_id": state.get("object_id", ""),
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "doc_name": doc_name,
                "parsed_rules": doc_rules,
            }
            (by_doc_dir / f"{safe_doc}.json").write_text(
                json.dumps(per_doc_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


def extract_rules_per_doc(
    docs_dir: str | Path = "data/docs",
    model: str | None = None,
    max_input_chars: int = 120000,
    timeout: float = 120.0,
) -> dict[str, dict[str, dict[str, str]]]:
    """Extract rules with one LLM request per document."""
    model_name = model or os.getenv("OPENAI_MODEL", "glm-5")
    config = ExtractionConfig(model=model_name, max_input_chars=max_input_chars, timeout=timeout)
    payloads = _load_doc_payloads(Path(docs_dir))
    total = len(payloads)
    _log(
        f"start extraction: docs={total}, model={config.model}, timeout={config.timeout}s, "
        f"max_input_chars={config.max_input_chars}"
    )

    per_doc: dict[str, dict[str, dict[str, str]]] = {}
    for idx, (doc_name, doc_text) in enumerate(payloads, start=1):
        t0 = perf_counter()
        char_count = len(doc_text)
        _log(f"[{idx}/{total}] start doc={doc_name} chars={char_count}")
        try:
            per_doc[doc_name] = _run_prompt_extraction(doc_text, config)
        except Exception as exc:
            elapsed = perf_counter() - t0
            _log(f"[{idx}/{total}] failed doc={doc_name} elapsed={elapsed:.2f}s error={exc}")
            raise
        elapsed = perf_counter() - t0
        _log(f"[{idx}/{total}] done doc={doc_name} elapsed={elapsed:.2f}s")

    _log(f"all documents processed: total={total}")
    return per_doc


def parse_inspection_rules(state: RiskWorkflowState) -> dict[str, Any]:
    """Node1 implementation using per-document prompt extraction over docs."""
    try:
        docs_dir = os.getenv("RULES_DOCS_DIR", "data/docs")
        per_doc_rules = extract_rules_per_doc(docs_dir=docs_dir)

        # Optional state-provided supplemental request (as an extra virtual document)
        extras: list[str] = []
        raw_docs = state.get("raw_rule_docs", [])
        if raw_docs:
            extras.append("===== 图状态输入 raw_rule_docs =====\n" + "\n\n".join(raw_docs))
        inspection_text = state.get("inspection_text", "")
        if inspection_text:
            extras.append(f"===== 图状态输入 inspection_text =====\n{inspection_text}")
        if extras:
            model_name = os.getenv("OPENAI_MODEL", "glm-5")
            config = ExtractionConfig(model=model_name, max_input_chars=120000, timeout=120.0)
            per_doc_rules["__state_inputs__.txt"] = _run_prompt_extraction(
                "\n\n".join(extras), config
            )

        merged_rules = _merge_doc_rules(per_doc_rules)
        parsed_rules = {"by_doc": per_doc_rules, "merged": merged_rules}
    except Exception as exc:
        return {
            "parsed_rules": {"status": "node1_extraction_failed", "error": str(exc)},
            "required_info": [MISSING_GENERAL],
        }

    required_info = _derive_required_info(parsed_rules)
    _persist_node1_output(parsed_rules=parsed_rules, required_info=required_info, state=state)
    return {"parsed_rules": parsed_rules, "required_info": required_info}


def main() -> None:
    """CLI entry for one-off node1 extraction."""
    parser = argparse.ArgumentParser(
        description="Extract risk rules for node1 with one request per document."
    )
    parser.add_argument("--docs-dir", default="data/docs", help="Directory containing source docs.")
    parser.add_argument("--model", default=None, help="LLM model name. Default from OPENAI_MODEL.")
    parser.add_argument("--max-input-chars", type=int, default=120000)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--output-dir",
        default="data/parsed_rules/node1",
        help="Directory for per-doc outputs.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only show docs summary, no LLM call.")
    args = parser.parse_args()

    payloads = _load_doc_payloads(Path(args.docs_dir))
    if args.dry_run:
        info = {
            "docs_dir": str(args.docs_dir),
            "doc_count": len(payloads),
            "docs": [name for name, _ in payloads],
            "chars_per_doc": {name: len(text) for name, text in payloads},
            "max_input_chars": args.max_input_chars,
            "openai_model": args.model or os.getenv("OPENAI_MODEL", "glm-5"),
        }
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    _log(
        f"cli started: docs_dir={args.docs_dir}, output_dir={args.output_dir}, "
        f"model={args.model or os.getenv('OPENAI_MODEL', 'glm-5')}"
    )
    total_t0 = perf_counter()
    per_doc = extract_rules_per_doc(
        docs_dir=args.docs_dir,
        model=args.model,
        max_input_chars=args.max_input_chars,
        timeout=args.timeout,
    )
    merged = _merge_doc_rules(per_doc)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for doc_name, doc_rules in per_doc.items():
        safe_doc = _safe_name(doc_name)
        (output_dir / f"{safe_doc}.json").write_text(
            json.dumps(doc_rules, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (output_dir / "all_docs.json").write_text(
        json.dumps(per_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "merged.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total_elapsed = perf_counter() - total_t0
    _log(f"saved per-doc outputs to: {output_dir}")
    _log(f"cli finished in {total_elapsed:.2f}s")


if __name__ == "__main__":
    main()
