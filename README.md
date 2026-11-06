# Hermes Web SearXNG

Standalone SearXNG search plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent).
It connects Hermes' existing `web_search` tool to your SearXNG JSON API.

The backend ID is **`searxng-local`**, so it coexists with Hermes' bundled
`searxng` backend without replacing it. This plugin does not extract pages.
The separate `hermes-web-crawl4ai` plugin can provide that capability, or you
can choose any other extraction backend.

## Install from this checkout

This is a new local repository; it has not yet been published to GitHub.
Replace the source path when installing on another machine:

```bash
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HERMES_HOME/plugins"
git clone /home/vega/Projects/hermes-web-searxng "$HERMES_HOME/plugins/hermes-web-searxng"
hermes plugins enable hermes-web-searxng
```

Enabling uses Hermes' dependency admission workflow to provide `httpx`.
Start a new Hermes session and enable the standard `web` toolset if needed.
For profiles, set `HERMES_HOME` to the intended profile explicitly.

## Configure

Merge into that profile's `config.yaml`, preserving its other entries:

```yaml
plugins:
  enabled:
    - hermes-web-searxng
  entries:
    hermes-web-searxng:
      settings:
        api_url: http://localhost:8080
        timeout_seconds: 15
        language: en
        # categories: general
        # engines: bing,duckduckgo
        # safesearch: 1

web:
  search_backend: searxng-local
```

`api_url` falls back to `SEARXNG_URL` when unset. Settings are read through
`ctx.get_config()` on each call and can be edited in Hermes' plugin settings
form. Hermes' legacy `config` subtree is also accepted by that API.

SearXNG must allow JSON responses in its server-side `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

If your reverse proxy requires a Bearer token, store `SEARXNG_API_TOKEN` in the
profile's `.env` or secret source. Credentials do not belong in `api_url` or
plugin metadata. SearXNG itself usually needs no authentication.

## Pair with Crawl4AI

Install and enable `hermes-web-crawl4ai` separately, then merge these additions:

```yaml
plugins:
  enabled:
    - hermes-web-searxng
    - hermes-web-crawl4ai
  entries:
    hermes-web-searxng:
      settings:
        api_url: http://localhost:8080
    hermes-web-crawl4ai:
      settings:
        api_url: http://localhost:11235

web:
  search_backend: searxng-local
  extract_backend: crawl4ai
```

Each plugin works independently. Switching from bundled SearXNG requires only
installing/enabling this plugin and changing `web.search_backend` from `searxng`
to `searxng-local`; the existing `SEARXNG_URL` still works. To switch back, select
`searxng` again and disable `hermes-web-searxng`.

## Behavior

- Queries use `/search?format=json` with an optional language, engine list,
  category list, and safe-search setting.
- Results are sorted by score, deduplicated by URL, and capped at 1–20 results.
- Malformed result rows are skipped. HTTP errors, invalid JSON, and timeouts
  return Hermes error results; a 403 includes the JSON-format configuration hint.
- Service redirects are refused, so a proxy cannot forward the Bearer token
  to another endpoint. Private service addresses are allowed for self-hosting.
- Search returns links and snippets; it does not fetch the result URLs.

## Development and validation

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ../hermes-agent
pip install -e '.[dev]'
pytest -q
ruff check .
hermes plugins doctor . --ci
hermes plugins validate .
```

Uses the current native `plugin.yaml` + `register(ctx)` format and a pip entry
point. It declares its dependencies, configuration schema, and web provider.
No custom tool or privileged capability is needed.

Validated on Python 3.11 and 3.14 on 2026-11-06 against Hermes main commit
`6b21d0564de0492e2ebd0d8f63fca86c03b5c892`: HTTP contract tests, real directory
and pip discovery, Plugin Doctor, and catalog validation. The pair was also
loaded together in an isolated profile. No live SearXNG service was exercised.
CI follows Hermes main to catch host compatibility changes.

Reference: [Hermes plugin guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
and [web provider contract](https://hermes-agent.nousresearch.com/docs/developer-guide/web-search-provider-plugin).

## License

MIT
