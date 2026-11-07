# Hermes Web SearXNG

Web search through your SearXNG JSON API, with optional proxy authentication and per-profile search settings.
A standalone [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin.

## Requirements

- Hermes **0.23.0 or newer**, using its supported Python runtime (currently 3.14).
- A reachable SearXNG server. It can run on the same machine, another computer,
  or a private server. The plugin does not install the server.
- HTTP(S) access from the machine running Hermes to that service.

The plugin uses Python and HTTP; it has no desktop, shell, distro, username,
absolute-path, or local-container dependency. Its service URL is always supplied
by the user. Linux, macOS, and Windows are covered by the CI matrix.

## Install

```sh
hermes plugins install axAilotl/hermes-web-searxng --enable
```

Accept Hermes' dependency prompt. For unattended installation, add `--yes-deps`.
This is a direct GitHub install; catalog inclusion requires separate maintainer review.

Configure the active Hermes profile. If you use profiles, select the intended
one first, or set `HERMES_HOME` to its directory. The default is `~/.hermes`.
Start a new Hermes session after installing, and ensure the standard `web`
toolset is enabled in `hermes tools`.

## Configure

Merge this into your active profile's `config.yaml`, preserving other entries:

```yaml
plugins:
  enabled:
    - hermes-web-searxng
  entries:
    hermes-web-searxng:
      settings:
        api_url: http://localhost:8080

web:
  search_backend: searxng-local
```

Replace `localhost` when the service runs elsewhere. If Hermes itself runs in
Docker, `localhost` means the Hermes container, not your computer; use a shared
Docker network service name or an address reachable from that container.

`api_url` falls back to `SEARXNG_URL`. For a reverse proxy that requires a Bearer
token, store `SEARXNG_API_TOKEN` in the active profile's `.env` or secret source,
or enter it in the plugin's masked API token setting. SearXNG itself normally
needs no authentication. Never put credentials in the URL.

SearXNG must allow JSON output in its server-side `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Follow the [official SearXNG deployment guide](https://docs.searxng.org/admin/installation-docker.html)
if you need a server. A 403 from `/search?format=json` often means JSON output
is disabled; other causes include proxy authentication and rate limiting.

Optional plugin settings: `timeout_seconds` (default 15, bounded 1–120),
`language`, comma-separated `categories`, comma-separated `engines`, and
`safesearch` (0, 1, or 2). Results are ranked by score, deduplicated by URL,
and capped at 1–20. Malformed rows are skipped; HTTP, timeout, and invalid-JSON
failures become tool error results.

The backend ID is `searxng-local`, so it coexists with Hermes' built-in
`searxng`. This standalone implementation adds per-profile settings and
optional Bearer authentication; it does not replace core tools. To return to
the built-in provider, select `web.search_backend: searxng` and disable this plugin.

### Updating from 0.1.0

Version **0.1.1** fixes the synchronous search contract required by Hermes:
0.1.0 could fail with `'coroutine' object has no attribute 'get'` in `web_search`.
Update the plugin, then restart the Hermes process serving the affected profile
(CLI session, gateway, or Desktop backend). Disabling and enabling a plugin in
the same process may retain its already-imported Python module.

```sh
hermes plugins update hermes-web-searxng
```

If searches succeed but contain no results, check the SearXNG instance's engine
health. Captchas, rate limits, and blocked outbound requests are server/engine
problems. The optional `engines` setting can select engines that work for your
instance; no engine list is guaranteed across networks. Selecting this backend
does not configure automatic Tavily fallback.

## Use both plugins together

Install each independently:

```sh
hermes plugins install axAilotl/hermes-web-searxng --enable
hermes plugins install axAilotl/hermes-web-crawl4ai --enable
```

Merge the following configuration with your existing profile:

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

Neither plugin requires the other. You can pair either with another provider.

## Privacy and network behavior

The plugin sends requests only to the configured service. SearXNG forwards
queries to its enabled search engines; Crawl4AI fetches the requested pages.
These services determine where the requests ultimately go. The plugins send
no telemetry, run no shell commands or background services, and persist no
credentials or page content themselves. Hermes may retain tool results in its
normal conversation history. Credentials are resolved through Hermes' active
profile API. HTTP redirects from the service endpoint are refused so its Bearer
token is not forwarded to a different endpoint.

Use HTTPS when connecting across an untrusted network. The service may be on a
private address; model-provided crawl targets remain subject to Hermes' URL
policy. Crawl4AI's own redirect/subresource protections must also be configured:
checking a returned URL cannot undo a request the remote browser already made.

## Testing and development

CI tests Hermes v0.23.0 on Linux, macOS, and Windows, plus Hermes main on Linux.
It exercises HTTP request/response contracts, real plugin discovery from a
copied directory, the actual synchronous `web_search_tool` dispatcher against a
local HTTP server (success and failure), backend selection, manifest validation, and a built wheel
installed outside the source import path.

For development with a working Hermes environment, install `.[dev]` there.
For an isolated test harness, use a fresh Python 3.14 virtual environment and:

```sh
git clone --branch v0.23.0 --depth 1 https://github.com/NousResearch/hermes-agent.git ../hermes-agent
python -m pip install --no-deps -e ../hermes-agent
python -m pip install -r tests/requirements-host.txt '.[dev]' build
python -m pytest -q
ruff check .
hermes plugins doctor . --ci
hermes plugins validate .
python -m build
```

The minimal host requirements are for plugin contract tests, not a complete
Hermes agent installation. Normal users install Hermes using its official
installer and then install this plugin; they should not rebuild Hermes with pip.

To run the real-service tests with Docker available:

```sh
python tests/run_live.py
```

This pulls a pinned official service image, generates disposable credentials,
binds a random localhost port, uses a temporary Hermes home, exercises actual
HTTP calls through Hermes' real search dispatcher, and removes the container afterward. It does not use your configured
server or credentials. External network access is needed for search engines and
test pages. The GitHub **Live service test** workflow runs the same command on
request; external services can fail independently of the plugin.

The live runner pins the official SearXNG image published on 2026-11-06.
`SEARXNG_TEST_URL` can instead point `tests/test_live_searxng.py` at your own
disposable JSON-enabled server.

## Compatibility

Uses the native `plugin.yaml` + `register(ctx)` format, declared Python
dependencies, a configuration schema, and a pip entry point. No private Hermes
APIs, core overrides, custom tool, or privileged capability are required.

## License

MIT
