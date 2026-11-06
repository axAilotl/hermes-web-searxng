"""Check directory installation through the current Hermes loader."""

from pathlib import Path

import yaml


def test_real_hermes_discovery_and_backend_resolution(tmp_path, monkeypatch):
    from agent import web_search_registry
    from hermes_cli.plugins import PluginManager

    home = tmp_path / "hermes"
    (home / "plugins").mkdir(parents=True)
    (home / "plugins" / "hermes-web-searxng").symlink_to(Path(__file__).resolve().parents[1])
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "plugins": {
                    "enabled": ["hermes-web-searxng"],
                    "entries": {
                        "hermes-web-searxng": {"settings": {"api_url": "http://localhost:8080"}},
                    },
                },
                "web": {"search_backend": "searxng-local"},
            }
        )
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    manager = PluginManager()
    try:
        manager.discover_and_load()
        loaded = manager._plugins["hermes-web-searxng"]
        assert loaded.enabled and loaded.error is None
        provider = web_search_registry.get_provider("searxng-local")
        assert provider.is_available()
        assert provider._api_url() == "http://localhost:8080"
        assert web_search_registry.get_provider("searxng") is not provider
        assert web_search_registry.get_active_search_provider() is provider
    finally:
        manager.unload()
