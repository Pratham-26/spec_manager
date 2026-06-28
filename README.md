# spec_manager

Central, DB-backed spec manager. Makes specs accessible and reusable **across projects** through governed MCP tools (no LLM on the server). Local `.specs/` working copies stay in sync with the central store via a deterministic script.

See [`docs/plans/2026-06-28-spec-manager-design.md`](docs/plans/2026-06-28-spec-manager-design.md) for the full design.

## Quick start

```bash
uv sync                                  # install
uv run specm serve                       # start the API server (127.0.0.1:8777)
uv run specm project register my-app     # register a project
uv run specm sync                        # sync local .specs/ <-> central
```
