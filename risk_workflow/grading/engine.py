"""Rule-based risk grading from existing rule and KG artifacts."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NODE1_DIR = ROOT / "risk_workflow" / "outputs" / "node1"
NODE2_DIR = ROOT / "risk_workflow" / "outputs" / "node2"
NODE3_DIR = ROOT / "risk_workflow" / "outputs" / "node3"
NODE5_DIR = ROOT / "risk_workflow" / "outputs" / "node5"

RISK_ORDER = {"IV级": 0, "III级": 1, "II级": 2, "I级": 3}
RISK_CLASS = {"I级": "risk-i", "II级": "risk-ii", "III级": "risk-iii", "IV级": "risk-iv"}

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


def _numeric_facts(text: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    pattern = re.compile(r"(?P<label>[\u4e00-\u9fffA-Za-z0-9\-（）()]{1,18})\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m|%|kPa|g|°|毫米|厘米|米)")
    seen: set[str] = set()
    for match in pattern.finditer(text):
        raw = match.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        facts.append(
            {
                "field": match.group("label"),
                "value": float(match.group("value")),
                "unit": match.group("unit"),
                "raw": raw,
            }
        )
    return facts


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


def _score_text(text: str, facts: list[dict[str, Any]]) -> tuple[int, list[str]]:
    score = 0
    evidence: list[str] = []
    stable_signal = any(word in text for word in ("稳定", "通畅", "完整", "未发现明显", "低风险", "正常"))
    severe_signal = any(word in text for word in ("立即", "交通管控", "明显异常", "持续异响", "扩展趋势明显", "失稳风险"))
    risk_text = re.sub(
        r"[^，。；\n]*(?:未见|未发现|无)[^，。；\n]*(?:异常|病害|裂缝|松动)[^，。；\n]*",
        "",
        text,
    )
    risk_text = re.sub(r"螺栓松动数\s*0", "", risk_text)
    keyword_weights = [
        (("立即", "交通管控", "明显异常", "持续异响", "扩展趋势明显", "失稳风险"), 4),
        (("异常", "明显", "扩大", "滑塌", "松动", "渗水增强", "同步异常"), 3),
        (("错台", "跳车", "裂纹", "裂缝", "位移", "渗水", "堵塞", "杂物堆积"), 2),
        (("轻微", "局部", "小幅", "细小", "关注", "复测"), 1),
    ]
    for words, weight in keyword_weights:
        matched = [word for word in words if word in risk_text]
        if "未发现明显" in text and "明显" in matched:
            matched.remove("明显")
        if matched:
            score += weight
            evidence.append(f"文本命中关键词：{'、'.join(matched[:5])}")

    if stable_signal:
        score -= 6
        evidence.append("文本包含稳定或低风险状态描述")

    numeric_score = 0
    for fact in facts:
        value = fact["value"]
        unit = fact["unit"]
        raw = fact["raw"]
        field = str(fact["field"])
        if "通畅率" in field or ("松动数" in field and value == 0):
            continue
        if unit in ("mm", "毫米"):
            if value >= 25:
                numeric_score += 3
                evidence.append(f"数值较大：{raw}")
            elif value >= 10:
                numeric_score += 1
                evidence.append(f"数值达到关注范围：{raw}")
        elif unit in ("cm", "厘米") and value >= 5:
            numeric_score += 2
            evidence.append(f"厘米级异常：{raw}")
        elif unit in ("%",) and value >= 5:
            numeric_score += 2
            evidence.append(f"百分比偏差达到关注范围：{raw}")
        elif unit in ("kPa", "g") and value > 0:
            numeric_score += 2
            evidence.append(f"监测指标异常：{raw}")

    if stable_signal and not severe_signal:
        numeric_score = min(numeric_score, 1)
    else:
        numeric_score = min(numeric_score, 6)
    score += numeric_score

    return max(score, 0), evidence[:10]


def _level_from_score(score: int) -> str:
    if score >= 14:
        return "I级"
    if score >= 7:
        return "II级"
    if score >= 3:
        return "III级"
    return "IV级"


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
        "grading_rule": str(payload.get("风险分级规则", "按异常程度、数值大小、发展趋势和处置紧迫性进行等级划分。")),
    }


def grade_point(point: Point, rules: dict[str, Any], monitor_paths: dict[str, list[Path]]) -> dict[str, Any]:
    kg_payload = _build_point_kg(point, monitor_paths)
    inspection_text = _inspection_text(point.id)
    monitor_text = _monitor_text(point.id)
    text = _combined_text(kg_payload, inspection_text, monitor_text)
    facts = _numeric_facts(text)
    hazard = _detect_hazard(point, text)
    score, evidence = _score_text(text, facts)
    level = _level_from_score(score)
    rule_payload = _select_rule_snippet(hazard, rules)
    conclusion = f"{point.name}当前判定为{level}风险，主要隐患类型为{rule_payload['hazard_type']}。"
    process_steps = [
        f"主体分类：根据点位类型和编号识别为{point.subject_type or '未知'}。",
        f"图谱融合：合并巡检知识图谱、监测知识图谱和原始文本，共获得{len(kg_payload['merged_triples'])}条去重三元组。",
        f"隐患识别：从图谱实体、关系和文本关键词中识别主要隐患类型为{rule_payload['hazard_type']}。",
        f"事实抽取：抽取位移、裂缝、错台、堆积厚度等可量化事实{len(facts)}项。",
        f"规则匹配：结合分级规则中的灾害判断依据、风险分级规则和异常发展描述进行匹配。",
        f"等级计算：异常程度综合评分为{score}，映射为{level}风险。",
    ]
    explanation = (
        f"{conclusion}判断过程为："
        f"{'；'.join(process_steps)}"
        f"主要证据包括：{'；'.join(evidence) if evidence else '未发现明显异常证据'}。"
    )
    return {
        "point_id": point.id,
        "point_name": point.name,
        "subject_type": point.subject_type,
        "hazard_type": rule_payload["hazard_type"],
        "risk_level": level,
        "risk_class": RISK_CLASS[level],
        "score": score,
        "summary": conclusion,
        "grading_basis": {
            "matched_facts": facts[:20],
            "matched_evidence": evidence,
            "process_steps": process_steps,
            "matched_rules": [
                {
                    "hazard_type": rule_payload["hazard_type"],
                    "judgement_basis": rule_payload["judgement_basis"][:1000],
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
