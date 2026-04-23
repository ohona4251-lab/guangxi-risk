"""Node2: build initial KG by running EDC with env-configured LLM/embeddings."""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ...state import RiskWorkflowState

load_dotenv()

NODE2_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "node2"
EDC_ROOT = Path(__file__).resolve().parent / "edc-main" / "edc-main"


def _safe_name(raw: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw).strip("_") or "unknown"


def _ensure_edc_import() -> None:
    edc_root_str = str(EDC_ROOT.resolve())
    if edc_root_str not in sys.path:
        sys.path.insert(0, edc_root_str)


def _build_input_texts(state: RiskWorkflowState) -> list[str]:
    texts: list[str] = []
    inspection_text = str(state.get("inspection_text", "")).strip()
    if inspection_text:
        texts.append(inspection_text)

    raw_rule_docs = state.get("raw_rule_docs", [])
    if raw_rule_docs:
        texts.extend([str(x).strip() for x in raw_rule_docs if str(x).strip()])

    if not texts and state.get("parsed_rules"):
        texts.append(json.dumps(state["parsed_rules"], ensure_ascii=False))

    return texts or ["No input text provided."]


def _read_canon_triplets(output_dir: Path, refinement_iterations: int) -> list[list[list[str]]]:
    canon_path = output_dir / f"iter{refinement_iterations}" / "canon_kg.txt"
    if not canon_path.exists():
        return []
    triplets_per_line: list[list[list[str]]] = []
    for line in canon_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = ast.literal_eval(line)
            if isinstance(parsed, list):
                triplets_per_line.append(parsed)
        except Exception:
            continue
    return triplets_per_line


def _run_edc(texts: list[str], output_dir: Path) -> list[list[list[str]]]:
    _ensure_edc_import()
    from edc.edc_framework import EDC  # type: ignore

    model = os.getenv("OPENAI_MODEL", "glm-5")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "embedding-3")
    refinement_iterations = int(os.getenv("NODE2_EDC_REFINEMENT_ITERATIONS", "0"))

    config = {
        "oie_llm": model,
        "oie_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "oie_template.txt"),
        "oie_few_shot_example_file_path": str(
            EDC_ROOT / "few_shot_examples" / "example" / "oie_few_shot_examples.txt"
        ),
        "sd_llm": model,
        "sd_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "sd_template.txt"),
        "sd_few_shot_example_file_path": str(
            EDC_ROOT / "few_shot_examples" / "example" / "sd_few_shot_examples.txt"
        ),
        "sc_llm": model,
        "sc_embedder": embedding_model,
        "sc_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "sc_template.txt"),
        "sr_adapter_path": None,
        "sr_embedder": embedding_model,
        "oie_refine_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "oie_r_template.txt"),
        "oie_refine_few_shot_example_file_path": str(
            EDC_ROOT / "few_shot_examples" / "example" / "oie_few_shot_refine_examples.txt"
        ),
        "ee_llm": model,
        "ee_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "ee_template.txt"),
        "ee_few_shot_example_file_path": str(
            EDC_ROOT / "few_shot_examples" / "example" / "ee_few_shot_examples.txt"
        ),
        "em_prompt_template_file_path": str(EDC_ROOT / "prompt_templates" / "em_template.txt"),
        "target_schema_path": str(EDC_ROOT / "schemas" / "example_schema.csv"),
        "enrich_schema": True,
        "loglevel": None,
    }

    edc = EDC(**config)
    edc.extract_kg(texts, str(output_dir), refinement_iterations=refinement_iterations)
    return _read_canon_triplets(output_dir, refinement_iterations)


def build_initial_kg(state: RiskWorkflowState) -> dict[str, Any]:
    """Build initial KG by running EDC and persisting outputs."""
    case_id = str(state.get("case_id", "unknown_case")).strip() or "unknown_case"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    NODE2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = NODE2_OUTPUT_DIR / f"{_safe_name(case_id)}_{ts}"

    texts = _build_input_texts(state)

    try:
        triplets = _run_edc(texts, output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "input_texts.json").write_text(
            json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "initial_kg": {
                "status": "node2_edc_failed",
                "error": str(exc),
                "edc_output_dir": str(output_dir),
                "source_rules_ready": bool(state.get("parsed_rules")),
                "object_meta_keys": sorted(state.get("object_meta", {}).keys()),
                "nodes": [],
                "edges": [],
            }
        }

    (output_dir / "input_texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "initial_kg": {
            "status": "node2_edc_completed",
            "edc_output_dir": str(output_dir),
            "source_rules_ready": bool(state.get("parsed_rules")),
            "object_meta_keys": sorted(state.get("object_meta", {}).keys()),
            "triplets": triplets,
            "nodes": [],
            "edges": [],
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run node2 EDC extraction standalone.")
    parser.add_argument(
        "--inspection-text",
        default="广西某高速路段边坡有松动，降雨后出现渗水和小规模坍塌。",
        help="Single text input for one-shot run. Ignored when --input-dir is provided.",
    )
    parser.add_argument(
        "--case-id",
        default="node2_cli_case",
        help="Case id prefix. In --input-dir mode, filename/index will be appended.",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing *.txt files. If set, run node2 once per txt file.",
    )
    args = parser.parse_args()

    if args.input_dir:
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            raise FileNotFoundError(f"input directory not found: {input_dir}")
        files = sorted(input_dir.glob("*.txt"))
        if not files:
            raise FileNotFoundError(f"no .txt files found in: {input_dir}")

        results: list[dict[str, Any]] = []
        for idx, txt_file in enumerate(files, start=1):
            text = txt_file.read_text(encoding="utf-8", errors="ignore").strip()
            state: RiskWorkflowState = {
                "case_id": f"{args.case_id}_{idx}_{_safe_name(txt_file.stem)}",
                "inspection_text": text,
                "parsed_rules": {"status": "cli_input_dir"},
            }
            out = build_initial_kg(state)
            initial_kg = out.get("initial_kg", {})
            results.append(
                {
                    "file": txt_file.name,
                    "case_id": state["case_id"],
                    "status": initial_kg.get("status"),
                    "edc_output_dir": initial_kg.get("edc_output_dir"),
                    "error": initial_kg.get("error"),
                }
            )
        print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))
        return

    state: RiskWorkflowState = {
        "case_id": args.case_id,
        "inspection_text": args.inspection_text,
        "parsed_rules": {"status": "cli_input"},
    }
    result = build_initial_kg(state)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
