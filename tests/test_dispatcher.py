"""Exercise Hermes' actual synchronous tool entry point over real HTTP."""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml


@pytest.mark.parametrize("status", [200, 403])
def test_real_dispatcher(tmp_path, status):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(urlsplit(self.path))
            body = json.dumps({"results": [
                {"url": "https://example.com/result", "title": "Dispatcher result"},
                {"url": "https://example.com/second", "title": "Second result"},
            ]}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        home = tmp_path / "hermes"
        source = Path(__file__).resolve().parents[1]
        plugin = home / "plugins/hermes-web-searxng"
        # Only the native install payload, with no editable checkout on sys.path.
        plugin.mkdir(parents=True)
        for name in ("__init__.py", "plugin.yaml", "pyproject.toml"):
            shutil.copy2(source / name, plugin / name)
        shutil.copytree(source / "hermes_web_searxng", plugin / "hermes_web_searxng")
        (home / "config.yaml").write_text(yaml.safe_dump({
            "plugins": {
                "enabled": ["hermes-web-searxng"],
                "entries": {"hermes-web-searxng": {"settings": {
                    "api_url": f"http://127.0.0.1:{server.server_port}",
                }}},
            },
            "web": {"search_backend": "searxng-local", "keyless_rescue": False},
        }), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-I", "-c", (
                "from tools.web_tools import web_search_tool; "
                "print(web_search_tool('dispatcher contract', limit=1))"
            )],
            env={**os.environ, "HERMES_HOME": str(home)},
            cwd=tmp_path, capture_output=True, text=True, timeout=30, check=True,
        )
        result = json.loads(completed.stdout)
        if status == 200:
            assert result.get("success") is True, result
            assert result["data"]["web"] == [{
                "title": "Dispatcher result", "url": "https://example.com/result",
                "description": "", "position": 1,
            }]
        else:
            assert result.get("success") is False, result
            assert "HTTP 403" in result["error"], result
        assert len(requests) == 1
        assert requests[0].path == "/search"
        assert parse_qs(requests[0].query)["q"] == ["dispatcher contract"]
        assert "was never awaited" not in completed.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
