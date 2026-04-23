"""Serve the risk grading front-end and workflow review API.

This module keeps the existing command shape:
python -m risk_workflow.grading.server --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse

from api_server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve risk grading UI and review API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
