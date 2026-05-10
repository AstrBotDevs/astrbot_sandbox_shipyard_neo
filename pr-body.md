## Summary

This change adds persistent sandbox recovery support to the Shipyard Neo provider.

Previously the provider always created a fresh sandbox through `create_sandbox(...)` and only stored display-oriented metadata in connect info. That meant AstrBot could retain a persistent sandbox record, but it could not reconnect to the existing Bay sandbox after restart because the stable sandbox id was not preserved or reused.

This patch records both a persistent runtime name and the actual `sandbox_id` in connect info, marks the provider as supporting persistent reconnect, and teaches the booter to distinguish between sandbox creation and sandbox recovery. Recovery now uses `get_sandbox(existing_sandbox_id)` while normal creation still uses `create_sandbox(...)`.

## Validation

- `uv run ruff check provider.py booters/shipyard_neo.py test_persistence.py`
- `uv run pytest test_persistence.py`
