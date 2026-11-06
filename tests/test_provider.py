import json

import httpx
import pytest

from hermes_web_searxng import provider as module
from hermes_web_searxng.provider import SearXNGWebSearchProvider


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    monkeypatch.setattr(module, "get_provider_env", lambda key: "")


@pytest.fixture
def provider():
    return SearXNGWebSearchProvider({"api_url": "http://localhost:8080/base"}.get)


def mock_http(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )


async def test_search_request_and_result_contract(monkeypatch):
    settings = {
        "api_url": "http://localhost:8080/base/",
        "language": "en",
        "categories": "general",
        "engines": "bing",
        "safesearch": 0,
    }
    provider = SearXNGWebSearchProvider(settings.get)
    monkeypatch.setattr(
        module, "get_provider_env", lambda key: "test-token" if key == "SEARXNG_API_TOKEN" else ""
    )

    def respond(request):
        assert request.url.path == "/base/search"
        assert request.url.params["q"] == "some words & symbols"
        assert request.url.params["format"] == "json"
        assert request.url.params["safesearch"] == "0"
        assert request.url.params["engines"] == "bing"
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": "https://low.example", "score": None},
                    {
                        "url": "https://high.example",
                        "score": 10,
                        "title": "High",
                        "content": "Text",
                    },
                    {"url": "https://high.example", "score": 9},
                    {"url": "javascript:alert(1)", "score": 100},
                    {"url": "https://user:secret@example.com", "score": 100},
                    {"url": "http://[bad", "score": 100},
                    None,
                    {"url": "https://last.example", "score": "invalid"},
                ]
            },
        )

    mock_http(monkeypatch, respond)
    result = await provider.search("some words & symbols", limit=2)
    assert result == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "High",
                    "url": "https://high.example",
                    "description": "Text",
                    "position": 1,
                },
                {"title": "", "url": "https://low.example", "description": "", "position": 2},
            ]
        },
    }


@pytest.mark.parametrize(
    "status,body", [(403, {}), (500, {}), (200, []), (200, {"results": {}}), (200, "not json")]
)
async def test_errors_are_tool_results(monkeypatch, provider, status, body):
    mock_http(
        monkeypatch,
        lambda request: httpx.Response(
            status, content=(body if isinstance(body, str) else json.dumps(body))
        ),
    )
    result = await provider.search("test")
    assert result["success"] is False
    if status == 403:
        assert "formats" in result["error"]


async def test_timeout_is_contained(monkeypatch, provider):
    def respond(request):
        raise httpx.ReadTimeout("timeout", request=request)

    mock_http(monkeypatch, respond)
    assert (await provider.search("test"))["success"] is False


async def test_service_redirect_is_not_followed(monkeypatch, provider):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://other.example/search"})

    mock_http(monkeypatch, respond)
    assert (await provider.search("test"))["success"] is False
    assert len(requests) == 1


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///etc/passwd",
        "https://user:password@example.com",
        "http://[bad",
        "https://example.com?token=secret",
    ],
)
async def test_bad_configuration_never_makes_request(monkeypatch, url):
    def no_http(**kwargs):
        pytest.fail("invalid configuration opened an HTTP client")

    monkeypatch.setattr(module.httpx, "AsyncClient", no_http)
    provider = SearXNGWebSearchProvider({"api_url": url}.get)
    assert provider.is_available() is False
    assert (await provider.search("test"))["success"] is False


def test_settings_are_dynamic_and_env_is_fallback(monkeypatch):
    monkeypatch.setattr(module, "get_provider_env", lambda key: "http://localhost:8080")
    settings = {}
    first = SearXNGWebSearchProvider(settings.get)
    second = SearXNGWebSearchProvider({"api_url": "http://second.example"}.get)
    assert first._api_url() == "http://localhost:8080"
    settings["api_url"] = "http://first.example"
    assert first._api_url() == "http://first.example"
    assert second._api_url() == "http://second.example"
    assert first.supports_search() and not first.supports_extract()


@pytest.mark.parametrize("limit,expected", [(-1, 1), (0, 1), (100, 20)])
async def test_limits_are_bounded(monkeypatch, provider, limit, expected):
    mock_http(
        monkeypatch,
        lambda request: httpx.Response(
            200, json={"results": [{"url": f"https://example.com/{i}"} for i in range(30)]}
        ),
    )
    assert len((await provider.search("test", limit))["data"]["web"]) == expected
