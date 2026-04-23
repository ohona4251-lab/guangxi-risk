"""Small stdlib HTTP server for the static frontend and grading API."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .engine import ROOT, run_batch_grading


class GradingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "front"), **kwargs)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/grading/run":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {}
        payload = run_batch_grading(point_ids=body.get("point_ids"))
        self._send_json(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/grading/latest":
            latest = ROOT / "risk_workflow" / "outputs" / "node5" / "latest.json"
            if not latest.exists():
                self._send_json({"generated_at": None, "total": 0, "results": []})
                return
            self._send_json(json.loads(latest.read_text(encoding="utf-8")))
            return
        if self.path.startswith("/risk_workflow/") or self.path.startswith("/data/"):
            self._serve_repo_file(self.path)
            return
        super().do_GET()

    def _serve_repo_file(self, request_path: str) -> None:
        relative = Path(unquote(request_path.lstrip("/")))
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents and target != ROOT.resolve():
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        self.path = "/" + str(relative).replace("\\", "/")
        self.directory = str(ROOT)
        super().do_GET()

    def _send_json(self, payload: object) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve frontend with grading API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), GradingHandler)
    print(f"Serving frontend and grading API at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
