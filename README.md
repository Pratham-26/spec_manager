# spec_manager

Central, DB-backed spec manager. Makes specs accessible and reusable **across
projects** through governed MCP tools — **no LLM on the server**. Specs follow the
`obra/superpowers` lifecycle (`draft → in_review → approved → planned →
implemented`). Local `.specs/` working copies stay in sync with the central store
via a deterministic script.

> **Pointing an agent at this?** It can install and wire up everything from the
> [Installation](#installation) and [Connecting an agent](#connecting-an-agent)
> sections below, then operate via [Tools & guardrails](#tools--guardrails).

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (recommended) — or any pip/venv flow

## Installation

```bash
git clone https://github.com/Pratham-26/spec_manager.git
cd spec_manager
uv sync
```

`uv sync` creates the venv and installs dependencies (fastapi, uvicorn,
sqlalchemy, pydantic, pyyaml, httpx, mcp). Nothing else to install — the database
auto-creates at `~/.spec_manager/spec_manager.db` on first run.

Configuration is env-driven (no secrets):

| Variable | Default | Purpose |
|----------|---------|---------|
| `SPEC_MANAGER_DATA_DIR` | `~/.spec_manager` | where the SQLite DB lives |
| `SPEC_MANAGER_DB_URL` | `sqlite:///<data_dir>/spec_manager.db` | full DB URL (swap for Postgres) |
| `SPEC_MANAGER_HOST` / `SPEC_MANAGER_PORT` | `127.0.0.1` / `8777` | HTTP API bind address |
| `SPEC_MANAGER_PROJECT` | — | the project an agent is acting as (see below) |

## Running

Three independent access paths to the **same store** — pick what your runtime needs:

| Path | Command | Use when |
|------|---------|----------|
| HTTP API + browser UI | `uv run specm serve` → http://127.0.0.1:8777 | you want the web UI / REST |
| MCP stdio server | `uv run specm-mcp` | an LLM agent should read/write specs |
| CLI | `uv run specm …` | manual ops or scripting |

MCP and the CLI open the SQLite file directly, so **you do not need to run
`specm serve`** for them.

Register each project you work in (run from inside that project's directory):

```bash
uv run specm project register <project-slug>      # e.g. "billing-api"
```

## Connecting an agent

The MCP server is the primary path for agents. Launch it with `uv run specm-mcp`.

**Important — set the current project.** The server must know which project you're
acting as for write-guarding. Set it via `SPEC_MANAGER_PROJECT` (robust) or by
launching from a project root that has `.specs/.project` (created by
`specm project register`). If every write tool returns
`cross-project write not permitted`, the current project isn't set.

Generic JSON config (Cursor `.cursor/mcp.json`, Claude Code `.mcp.json`, Copilot,
Gemini — adjust the config-file path to your tool):

```json
{
  "mcpServers": {
    "spec-manager": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-this-repo>", "specm-mcp"],
      "env": { "SPEC_MANAGER_PROJECT": "<your-project-slug>" }
    }
  }
}
```

Tool-specific one-liners:

- **Claude Code:**
  `claude mcp add spec-manager -- uv run --directory <repo> specm-mcp`
- **Codex** (`~/.codex/config.toml`):
  ```toml
  [mcp_servers.spec-manager]
  command = "uv"
  args = ["run", "--directory", "<repo>", "specm-mcp"]
  env = { SPEC_MANAGER_PROJECT = "<slug>" }
  ```

If your runtime has no MCP support, use the [CLI](#cli) or the [HTTP API](#running) instead.

## CLI

```bash
uv run specm project register <slug> [--path .]    # register the current project
uv run specm sync [--path .] [--force]             # sync local .specs/ <-> central
uv run specm serve [--host 127.0.0.1] [--port 8777] # start the API server + UI
```

## Tools & guardrails

**Read (open across all projects):** `search_specs`, `list_specs`, `get_spec`, `list_versions`.
**Write (guarded):** `update_spec`, `set_status`, `fork_spec`, `sync_specs`.

- Reading any project's specs is always allowed.
- Writing to **another** project's spec is **denied by the server** unless that
  spec has `cross_project_writable` enabled — and agents must **confirm with the
  user** before a cross-project write even then.
- Edits push to central on sync when the body differs by **>10%** (`--force`
  ignores the threshold). The store is append-only whole-spec snapshots with
  monotonic version numbers, so history is never lost.

Lifecycle: `draft → in_review → approved → planned → implemented` (any state →
`deprecated` / `superseded`). Only valid transitions are accepted.

## Design

See [`docs/plans/2026-06-28-spec-manager-design.md`](docs/plans/2026-06-28-spec-manager-design.md)
for the full design.
