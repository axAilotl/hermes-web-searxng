"""Opt-in real SearXNG JSON API test (no mocked HTTP)."""

import json
import os
import subprocess
import sys

import pytest
import yaml

pytestmark = pytest.mark.skipif(
    not os.getenv("SEARXNG_TEST_URL"), reason="set SEARXNG_TEST_URL for a real-service test"
)


def test_live_search(tmp_path):
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({
        "plugins": {
            "enabled": ["hermes-web-searxng"],
            "entries": {"hermes-web-searxng": {"settings": {
                "api_url": os.environ["SEARXNG_TEST_URL"], "timeout_seconds": 60,
            }}},
        },
        "web": {"search_backend": "searxng-local", "keyless_rescue": False},
    }), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-I", "-c", (
            "from tools.web_tools import web_search_tool; "
            "print(web_search_tool('Hermes Agent NousResearch', limit=3))"
        )],
        env={**os.environ, "HERMES_HOME": str(tmp_path)},
        capture_output=True, text=True, timeout=90, check=True,
    )
    result = json.loads(completed.stdout)
    assert result["success"], result
    results = result["data"]["web"]
    assert 1 <= len(results) <= 3, "No engines returned results; check service connectivity"
    assert all(item["url"].startswith(("https://", "http://")) for item in results)
    assert [item["position"] for item in results] == list(range(1, len(results) + 1))
    assert "was never awaited" not in completed.stderr
