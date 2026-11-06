"""Hermes registration entry point."""

from .provider import SearXNGWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(SearXNGWebSearchProvider(ctx.get_config))


__all__ = ["register"]
