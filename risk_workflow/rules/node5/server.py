"""Small stdlib HTTP server for the static frontend and Node5 grading API."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from openai import AuthenticationError

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
        try:
            payload = run_batch_grading(point_ids=body.get("point_ids"))
        except AuthenticationError:
            traceback.print_exc()
            key = os.getenv("ZAI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
            key_hint = f"{key[:6]}...{key[-4:]}" if len(key) >= 12 else "未读取到"
            self._send_json(
                {
                    "error": (
                        "BigModel 拒绝认证：当前 API Key 无效、过期或不是智谱 BigModel 平台的 key。"
                        f"当前服务读取到的 key 片段为 {key_hint}。"
                        "请到 open.bigmodel.cn 控制台复制新的 API Key，写入 .env 的 ZAI_API_KEY 或 OPENAI_API_KEY，"
                        "然后重启 python -m risk_workflow.rules.node5.server。"
                    )
                },
                status=401,
            )
            return
        except Exception as error:
            traceback.print_exc()
            self._send_json({"error": str(error)}, status=500)
            return
        self._send_json(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/grading/latest":
            latest = ROOT / "risk_workflow" / "outputs" / "node5" / "latest.json"
            if not latest.exists():
                self._send_json({"generated_at": None, "total": 0, "results": []})
                return
            self._send_json(json.loads(latest.read_text(encoding="utf-8")))
            return
        if (
            self.path.startswith("/risk_workflow/")
            or self.path.startswith("/data/examples/")
            or self.path.startswith("/data/monitor_data/")
            or self.path.startswith("/data/info/")
        ):
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

    def _send_json(self, payload: object, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve frontend with Node5 grading API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), GradingHandler)
    print(f"Serving frontend and Node5 grading API at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
