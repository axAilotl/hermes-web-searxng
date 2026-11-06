"""Directory-plugin entry point for Hermes installation."""

if __package__:
    from .hermes_web_searxng import register
else:
    from hermes_web_searxng import register

__all__ = ["register"]
