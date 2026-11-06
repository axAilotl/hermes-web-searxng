"""Opt-in real SearXNG JSON API test (no mocked HTTP)."""

import os

import pytest

from hermes_web_searxng.provider import SearXNGWebSearchProvider

pytestmark = pytest.mark.skipif(
    not os.getenv("SEARXNG_TEST_URL"), reason="set SEARXNG_TEST_URL for a real-service test"
)


async def test_live_search():
    provider = SearXNGWebSearchProvider(
        {"api_url": os.environ["SEARXNG_TEST_URL"], "timeout_seconds": 60}.get
    )
    result = await provider.search("Hermes Agent NousResearch", limit=3)
    assert result["success"], result
    results = result["data"]["web"]
    assert 1 <= len(results) <= 3, "No engines returned results; check service connectivity"
    assert all(item["url"].startswith(("https://", "http://")) for item in results)
    assert [item["position"] for item in results] == list(range(1, len(results) + 1))
