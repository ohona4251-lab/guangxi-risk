"""Node5 risk grading strategy from existing rules and KG artifacts."""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parents[3]
NODE1_DIR = ROOT / "risk_workflow" / "outputs" / "node1"
NODE2_DIR = ROOT / "risk_workflow" / "outputs" / "node2"
NODE3_DIR = ROOT / "risk_workflow" / "outputs" / "node3"
NODE5_DIR = ROOT / "risk_workflow" / "outputs" / "node5"

RISK_CLASS = {"I级": "risk-i", "II级": "risk-ii", "III级": "risk-iii", "IV级": "risk-iv"}
VALID_RISK_LEVELS = set(RISK_CLASS)

INSPECTION_STEMS_BY_POINT = {
    "BR-BY01": ["bridge_br_by01_record1", "bridge_br_by01_record2"],
    "SP-LB13": ["bridge_sp_lb13_record1", "bridge_sp_lb13_record2"],
    "BR-LZ02": ["bridge_br_lz02_record1", "bridge_br_lz02_record2"],
    "BR-HZ07": ["bridge_br_hz07_record1", "bridge_br_hz07_record2"],
    "BR-QS09": ["bridge_br_qs09_record1", "bridge_br_qs09_record2"],
    "EX-BR-001": ["example2_bridge_joint"],
    "SL-GZ01": ["scope_sl_gz01_record1", "scope_sl_gz01_record2"],
    "SL-BH02": ["scope_sl_bh02_record1", "scope_sl_bh02_record2"],
    "SL-HC03": ["scope_sl_hc03_record1", "scope_sl_hc03_record2"],
    "EX-SL-001": ["example1_rainfall_slope"],
    "EX-SL-002": ["example3_tunnel_slope"],
}


@dataclass(frozen=True)
class Point:
    id: str
    name: str
    subject_type: str
    location: str
    lnglat: Any


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _read_canon_kg(path: Path) -> list[list[str]]:
    triples: list[list[str]] = []
    if not path.exists():
        return triples
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = ast.literal_eval(line)
        except (SyntaxError, ValueError):
            continue
        for item in parsed if isinstance(parsed, list) else []:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                triples.append([str(item[0]), str(item[1]), str(item[2])])
    return _dedupe_triples(triples)


def _dedupe_triples(triples: list[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[list[str]] = []
    for triple in triples:
        key = (triple[0], triple[1], triple[2])
        if key in seen:
            continue
        seen.add(key)
        result.append(triple)
    return result


def _load_points() -> list[Point]:
    points: list[Point] = []
    for path in (ROOT / "data" / "info" / "bridge.json", ROOT / "data" / "info" / "scope.json"):
        payload = _read_json(path, {})
        for item in payload.get("points", []):
            points.append(
                Point(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    subject_type=str(item.get("category") or item.get("type") or ""),
                    location=str(item.get("location", "")),
                    lnglat=item.get("lnglat"),
                )
            )
    return [point for point in points if point.id]


def _find_latest_inspection_kg(stem: str) -> list[Path]:
    paths = sorted(NODE2_DIR.glob(f"front_inspection_records_*_{stem}_*/iter0/canon_kg.txt"))
    if paths:
        return [paths[-1]]
    fallback = {
        "example1_rainfall_slope": "batch_examples_1_example1_rainfall_slope_20260422_232429",
        "example2_bridge_joint": "batch_examples_2_example2_bridge_joint_20260422_232822",
        "example3_tunnel_slope": "batch_examples_3_example3_tunnel_slope_20260422_233255",
    }.get(stem)
    if fallback:
        path = NODE2_DIR / fallback / "iter0" / "canon_kg.txt"
        return [path] if path.exists() else []
    return []


def _monitor_kg_paths_by_point() -> dict[str, list[Path]]:
    index = _read_json(NODE3_DIR / "node3_monitor_records_new_index.json", [])
    result: dict[str, list[Path]] = {}
    if not isinstance(index, list):
        return result
    for item in index:
        file_name = str(item.get("file", ""))
        point_id = file_name.replace("_monitor_01.txt", "")
        kg_path = item.get("canon_kg")
        if point_id and kg_path:
            result.setdefault(point_id, []).append(ROOT / str(kg_path))
    return result


def _load_rules() -> dict[str, Any]:
    rules = _read_json(NODE1_DIR / "merged.json", {})
    return rules if isinstance(rules, dict) else {}


def _inspection_text(point_id: str) -> str:
    parts: list[str] = []
    for stem in INSPECTION_STEMS_BY_POINT.get(point_id, []):
        parts.append(_read_text(ROOT / "data" / "examples" / f"{stem}.txt"))
    return "\n".join(part for part in parts if part)


def _monitor_text(point_id: str) -> str:
    return _read_text(ROOT / "data" / "monitor_data" / f"{point_id}_monitor_01.txt")


def _build_point_kg(point: Point, monitor_paths: dict[str, list[Path]]) -> dict[str, Any]:
    inspection_paths = [
        path
        for stem in INSPECTION_STEMS_BY_POINT.get(point.id, [])
        for path in _find_latest_inspection_kg(stem)
    ]
    monitor_kg_paths = monitor_paths.get(point.id, [])
    inspection_triples = _dedupe_triples([t for path in inspection_paths for t in _read_canon_kg(path)])
    monitor_triples = _dedupe_triples([t for path in monitor_kg_paths for t in _read_canon_kg(path)])
    merged_triples = _dedupe_triples(inspection_triples + monitor_triples)
    return {
        "inspection_paths": [str(path.relative_to(ROOT)) for path in inspection_paths],
        "monitor_paths": [str(path.relative_to(ROOT)) for path in monitor_kg_paths],
        "inspection_triples": inspection_triples,
        "monitor_triples": monitor_triples,
        "merged_triples": merged_triples,
    }


def _combined_text(kg_payload: dict[str, Any], inspection_text: str, monitor_text: str) -> str:
    triple_text = "\n".join(" ".join(triple) for triple in kg_payload["merged_triples"])
    return "\n".join(part for part in (triple_text, inspection_text, monitor_text) if part)


def _detect_hazard(point: Point, text: str) -> str:
    if point.subject_type == "桥梁":
        if any(word in text for word in ("伸缩缝", "错台", "跳车", "接缝")):
            return "桥梁伸缩缝及桥面病害"
        if any(word in text for word in ("支座", "挠度", "索力", "位移")):
            return "桥梁结构位移异常"
        if any(word in text for word in ("水位", "河床", "冲刷", "淤积", "泄水")):
            return "洪水灾害"
        return "桥梁一般病害"
    if any(word in text for word in ("滑塌", "滑坡", "失稳", "渗压")):
        return "滑坡"
    if any(word in text for word in ("落石", "掉块", "崩塌")):
        return "崩塌"
    if any(word in text for word in ("泥石流", "沟道", "冲淤")):
        return "泥石流"
    if any(word in text for word in ("水毁", "冲刷", "排水", "积水")):
        return "水毁"
    return "边坡一般病害"


def _select_rule_snippet(hazard: str, rules: dict[str, Any]) -> dict[str, str]:
    if hazard in rules and isinstance(rules[hazard], dict):
        payload = rules[hazard]
    else:
        payload = {}
        for name, item in rules.items():
            if name in hazard or hazard in name:
                payload = item if isinstance(item, dict) else {}
                hazard = name
                break
    return {
        "hazard_type": hazard,
        "judgement_basis": str(payload.get("灾害判断依据", "按知识图谱中异常现象和监测事实进行判定。")),
        "collect_info": str(payload.get("需要收集的信息", "")),
        "grading_rule": str(payload.get("风险分级规则", "按异常程度、数值大小、发展趋势和处置紧迫性进行等级划分。")),
    }


def _get_openai_client(timeout: float = 120.0) -> OpenAI:
    api_key = os.getenv("ZAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("ZAI_API_KEY or OPENAI_API_KEY is required")
    client_kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": timeout,
        # Avoid stale local proxy environment variables causing WinError 10061.
        "http_client": httpx.Client(timeout=timeout, trust_env=False),
    }
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url
    return OpenAI(**client_kwargs)


def _extract_json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty model response")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("model response JSON is not an object")
    return data


def _truncate_text(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[内容已截断]"


def _format_triples(triples: list[list[str]], limit: int = 30) -> str:
    if not triples:
        return "无"
    rows = []
    for index, triple in enumerate(triples[:limit], start=1):
        rows.append(f"{index}. {triple[0]} --{triple[1]}--> {triple[2]}")
    if len(triples) > limit:
        rows.append(f"...其余 {len(triples) - limit} 条已省略")
    return "\n".join(rows)


def _triple_to_sentence(triple: list[str]) -> str:
    if len(triple) < 3:
        return " ".join(str(item) for item in triple)
    subject, predicate, obj = (str(triple[0]).strip(), str(triple[1]).strip(), str(triple[2]).strip())
    return f"{subject}的{predicate}为{obj}。"


def _format_evidence_sentences(triples: list[list[str]], limit: int = 30) -> str:
    if not triples:
        return "无"
    rows = []
    for index, triple in enumerate(triples[:limit], start=1):
        rows.append(f"{index}. {_triple_to_sentence(triple)}")
    if len(triples) > limit:
        rows.append(f"...其余 {len(triples) - limit} 条已省略")
    return "\n".join(rows)


def _normalize_evidence_matches(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            normalized.append(
                {
                    "evidence_sentence": item,
                    "kg_evidence": item,
                    "rule_part": "",
                    "rule_text": "",
                    "reasoning": "",
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        kg_evidence = str(
            item.get("evidence_sentence")
            or item.get("证据句子")
            or item.get("kg_evidence")
            or item.get("evidence")
            or item.get("命中证据")
            or item.get("知识图谱证据")
            or ""
        ).strip()
        if not kg_evidence:
            continue
        normalized.append(
            {
                "evidence_sentence": kg_evidence[:800],
                "kg_evidence": kg_evidence[:800],
                "disaster_type": str(item.get("disaster_type") or item.get("对应灾害类型") or item.get("灾害类型") or "").strip()[:120],
                "rule_part": str(item.get("rule_part") or item.get("对应规则部分") or "").strip()[:80],
                "rule_text": str(item.get("rule_text") or item.get("规则原文") or "").strip()[:1000],
                "reasoning": str(item.get("reasoning") or item.get("匹配说明") or "").strip()[:800],
            }
        )
    return normalized[:12]


def _normalize_llm_grading(data: dict[str, Any], point: Point, rule_payload: dict[str, str]) -> dict[str, Any]:
    level = str(data.get("risk_level") or data.get("风险等级") or "").strip()
    if level not in VALID_RISK_LEVELS:
        level = "III级"
    evidence_matches = _normalize_evidence_matches(
        data.get("evidence_rule_matches") or data.get("matched_evidence") or data.get("命中证据")
    )
    summary = str(data.get("summary") or data.get("分级结论") or "").strip()
    if not summary:
        summary = f"{point.name}当前判定为{level}风险。"
    explanation = str(data.get("explanation") or data.get("解释说明") or summary).strip()
    return {
        "level": level,
        "summary": summary,
        "explanation": explanation,
        "evidence_rule_matches": evidence_matches,
    }


def _llm_grade_point(
    point: Point,
    kg_payload: dict[str, Any],
    inspection_text: str,
    monitor_text: str,
    rule_payload: dict[str, str],
) -> dict[str, Any]:
    client = _get_openai_client()
    model = os.getenv("GRADING_MODEL") or os.getenv("OPENAI_MODEL", "glm-5")
    system_prompt = (
        "你是公路承灾体风险分级专家。你必须只根据输入的知识图谱三元组、巡检/监测文本和抽取出的规则文本判定风险等级。"
        "不要判断总体灾害类型，不要使用评分、分值或阈值映射。"
        "你需要找出知识图谱中的命中证据，并说明每条证据对应哪个灾害类型以及哪段规则文本。"
        "只输出 JSON，不要输出 Markdown。"
    )
    user_prompt = f"""
请完成风险等级判定。

输出 JSON 结构必须为：
{{
  "risk_level": "I级/II级/III级/IV级",
  "summary": "一句话风险等级结论，不要包含总体灾害类型判断",
  "evidence_rule_matches": [
    {{
      "evidence_sentence": "将巡检/监测知识图谱三元组整合后的自然语言证据句子",
      "kg_evidence": "该证据句子对应的原始三元组或三元组组合",
      "disaster_type": "该条证据对应的灾害类型",
      "rule_part": "灾害判断依据/需要收集的信息/风险分级规则/其他",
      "rule_text": "该证据对应的规则原文片段",
      "reasoning": "为什么该证据命中该规则片段"
    }}
  ],
  "explanation": "解释说明：基于命中证据、对应灾害类型、对应规则文本说明为什么最终判定为该风险等级，不要输出判断过程列表"
}}

要求：
1. risk_level 只能是 I级、II级、III级、IV级。
2. evidence_rule_matches 必须体现“命中证据、对应灾害类型、对应规则文本”的关系。
3. evidence_sentence 必须是由下方“融合知识图谱证据句子”中的巡检记录和监测记录三元组整合而成的自然句，不要只写关键词。
4. 不要输出综合评分、分数、分值、score。
5. 不要判断总体灾害类型，只判断风险分级等级；disaster_type 仅用于标注每条证据对应的规则灾害类型。
6. 规则原文没有明确等级阈值时，按异常严重程度、发展趋势、影响范围、处置紧迫性综合判断。

点位信息：
- 编号：{point.id}
- 名称：{point.name}
- 类型：{point.subject_type}
- 位置：{point.location}

融合知识图谱三元组：
{_format_triples(kg_payload["merged_triples"])}

融合知识图谱证据句子：
{_format_evidence_sentences(kg_payload["merged_triples"])}

巡检文本：
{_truncate_text(inspection_text, 1200) or "无"}

监测文本：
{_truncate_text(monitor_text, 900) or "无"}

候选规则灾害类型：
{rule_payload["hazard_type"]}

灾害判断依据：
{_truncate_text(rule_payload["judgement_basis"], 1200)}

需要收集的信息：
{_truncate_text(rule_payload.get("collect_info", ""), 600) or "规则未明确给出"}

风险分级规则：
{_truncate_text(rule_payload["grading_rule"], 1200)}
""".strip()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
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
    return _normalize_llm_grading(_extract_json_from_text(content), point, rule_payload)


def grade_point(point: Point, rules: dict[str, Any], monitor_paths: dict[str, list[Path]]) -> dict[str, Any]:
    kg_payload = _build_point_kg(point, monitor_paths)
    inspection_text = _inspection_text(point.id)
    monitor_text = _monitor_text(point.id)
    text = _combined_text(kg_payload, inspection_text, monitor_text)
    hazard = _detect_hazard(point, text)
    rule_payload = _select_rule_snippet(hazard, rules)
    llm_result = _llm_grade_point(point, kg_payload, inspection_text, monitor_text, rule_payload)
    level = llm_result["level"]
    evidence_matches = llm_result["evidence_rule_matches"]
    explanation = llm_result["explanation"]
    conclusion = llm_result["summary"]
    return {
        "point_id": point.id,
        "point_name": point.name,
        "subject_type": point.subject_type,
        "hazard_type": "",
        "risk_level": level,
        "risk_class": RISK_CLASS[level],
        "summary": conclusion,
        "grading_basis": {
            "matched_evidence": evidence_matches,
            "matched_rules": [
                {
                    "hazard_type": rule_payload["hazard_type"],
                    "judgement_basis": rule_payload["judgement_basis"][:1000],
                    "collect_info": rule_payload.get("collect_info", "")[:1000],
                    "grading_rule": rule_payload["grading_rule"][:1500],
                }
            ],
            "kg_sources": {
                "inspection_paths": kg_payload["inspection_paths"],
                "monitor_paths": kg_payload["monitor_paths"],
                "triple_count": len(kg_payload["merged_triples"]),
            },
        },
        "explanation": explanation,
        "suggestion": _suggestion(level),
    }


def _suggestion(level: str) -> str:
    return {
        "I级": "建议立即组织现场复核，必要时采取交通管控和应急处置。",
        "II级": "建议安排专项复测和病害处治，并提高监测频率。",
        "III级": "建议纳入跟踪观察，按周期复测关键指标。",
        "IV级": "建议维持常规巡检和例行监测。",
    }[level]


def run_batch_grading(point_ids: list[str] | None = None) -> dict[str, Any]:
    rules = _load_rules()
    monitor_paths = _monitor_kg_paths_by_point()
    wanted = set(point_ids or [])
    points = [point for point in _load_points() if not wanted or point.id in wanted]
    results = [grade_point(point, rules, monitor_paths) for point in points]
    generated_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "generated_at": generated_at,
        "total": len(results),
        "results": results,
    }
    NODE5_DIR.mkdir(parents=True, exist_ok=True)
    (NODE5_DIR / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    run_dir = NODE5_DIR / f"grading_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        (run_dir / f"{result['point_id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return payload
