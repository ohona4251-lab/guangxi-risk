"""CLI entry for the Node5 risk grading strategy."""

from __future__ import annotations

import argparse
import json
import sys

from .engine import run_batch_grading


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run Node5 risk grading from existing KG outputs.")
    parser.add_argument(
        "--point-id",
        action="append",
        dest="point_ids",
        help="Limit grading to one point id. Can be provided multiple times.",
    )
    args = parser.parse_args()

    payload = run_batch_grading(point_ids=args.point_ids)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
