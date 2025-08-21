"""Common integration utilities and base interfaces for integrations."""

# Import lazily to avoid circular dependencies
try:
    from .watchers import BaseIntegrationWatcher  # noqa: F401
except Exception:
    # Watcher base may not be imported during partial app init
    pass
