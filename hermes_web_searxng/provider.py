"""Independent SearXNG backend for Hermes' web_search tool."""

from __future__ import annotations

import math
from typing import Any
from urllib.parse import urlparse

import httpx
from agent.web_search_provider import WebSearchProvider, get_provider_env


class SearXNGWebSearchProvider(WebSearchProvider):
    def __init__(self, get_config=None):
        self.get_config = get_config or (lambda key, default=None: default)

    @property
    def name(self) -> str:
        # Keep the bundled searxng provider available independently.
        return "searxng-local"

    @property
    def display_name(self) -> str:
        return "SearXNG (standalone)"

    def _api_url(self) -> str:
        value = str(self.get_config("api_url") or get_provider_env("SEARXNG_URL")).strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Set a valid HTTP(S) api_url in this plugin's settings or SEARXNG_URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("SearXNG api_url must not contain credentials, a query, or a fragment")
        return value.rstrip("/")

    def is_available(self) -> bool:
        try:
            return bool(self._api_url())
        except ValueError:
            return False

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        try:
            if not isinstance(query, str) or not query.strip():
                return {"success": False, "error": "A non-empty search query is required"}
            limit = max(1, min(int(limit), 20))
            base_url = self._api_url()
            timeout = max(1, min(int(self.get_config("timeout_seconds", 15)), 120))
            params = {"q": query, "format": "json", "pageno": 1}
            for key in ("language", "categories", "engines"):
                value = self.get_config(key)
                if value:
                    params[key] = str(value)
            safesearch = self.get_config("safesearch")
            if safesearch is not None:
                params["safesearch"] = max(0, min(int(safesearch), 2))
            headers = {"Accept": "application/json"}
            token = get_provider_env("SEARXNG_API_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                response = client.get(f"{base_url}/search", params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                return {"success": False, "error": "SearXNG returned an invalid results envelope"}

            def score(item):
                try:
                    value = float(item.get("score", 0))
                    return value if math.isfinite(value) else 0
                except (TypeError, ValueError, OverflowError):
                    return 0

            results = []
            seen = set()
            for item in sorted(
                (item for item in data["results"] if isinstance(item, dict)),
                key=score,
                reverse=True,
            ):
                url = item.get("url")
                if not isinstance(url, str):
                    continue
                try:
                    parsed = urlparse(url)
                except ValueError:
                    continue
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or url in seen
                ):
                    continue
                seen.add(url)
                results.append(
                    {
                        "title": str(item.get("title") or ""),
                        "url": url,
                        "description": str(item.get("content") or ""),
                        "position": len(results) + 1,
                    }
                )
                if len(results) == limit:
                    break
            return {"success": True, "data": {"web": results}}
        except httpx.HTTPStatusError as exc:
            hint = (
                " Enable search.formats: [html, json] on the server."
                if exc.response.status_code == 403
                else ""
            )
            return {
                "success": False,
                "error": f"SearXNG returned HTTP {exc.response.status_code}.{hint}",
            }
        except httpx.RequestError:
            return {
                "success": False,
                "error": "Could not reach SearXNG; check its URL and availability",
            }
        except (ValueError, TypeError, OverflowError):
            return {
                "success": False,
                "error": "Invalid SearXNG settings, arguments, or JSON response",
            }

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "free · self-hosted",
            "tag": "Search only; pair with an extraction backend such as Crawl4AI.",
            "env_vars": [{"key": "SEARXNG_URL", "prompt": "SearXNG instance URL"}],
        }
