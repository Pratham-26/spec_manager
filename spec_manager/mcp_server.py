"""Thin stdio MCP server exposing the spec store to LLM skills.

Reuses the Store in-process (shares the SQLite file, same as the CLI) to stay
lean — no HTTP round-trip. Write tools enforce the cross-project guardrail
using the current project as the actor; the skill layer adds confirmation UX.
"""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from spec_manager.permissions import can_write
from spec_manager.store import Store


def _denied(owner_project: str, current_project: str, spec) -> bool:
    return not can_write(
        owner_project=owner_project,
        current_project=current_project,
        cross_project_writable=spec.cross_project_writable,
    )


# --------------------------------------------------------------- read tools

def tool_search(store: Store, query: str, project: str | None = None) -> list[dict]:
    return [s.model_dump(mode="json") for s in store.search(query, project_slug=project)]


def tool_get_spec(store: Store, project: str, slug: str) -> dict | None:
    spec = store.get_spec(project, slug)
    return spec.model_dump(mode="json") if spec else None


def tool_list_specs(store: Store, project: str | None = None) -> list[dict]:
    return [s.model_dump(mode="json") for s in store.list_specs(project_slug=project)]


def tool_list_versions(store: Store, project: str, slug: str) -> list[dict]:
    return [v.model_dump(mode="json") for v in store.list_versions(project, slug)]


# -------------------------------------------------------------- write tools

def tool_update_spec(
    store: Store, current_project: str, project: str, slug: str, body: str, message: str | None = None
) -> dict:
    spec = store.get_spec(project, slug)
    if spec is None:
        return {"error": "spec not found"}
    if _denied(project, current_project, spec):
        return {"error": "cross-project write not permitted (enable cross_project_writable on the spec)"}
    store.update_spec_body(project, slug, body=body, message=message)
    return store.get_spec(project, slug).model_dump(mode="json")  # type: ignore[union-attr]


def tool_set_status(
    store: Store, current_project: str, project: str, slug: str, to_status: str, note: str | None = None
) -> dict:
    spec = store.get_spec(project, slug)
    if spec is None:
        return {"error": "spec not found"}
    if _denied(project, current_project, spec):
        return {"error": "cross-project write not permitted"}
    try:
        return store.set_status(project, slug, to_status, note=note).model_dump(mode="json")
    except Exception as exc:  # invalid transition, etc.
        return {"error": str(exc)}


def tool_fork(store: Store, from_project: str, slug: str, into_project: str, new_slug: str) -> dict:
    return store.fork(from_project, slug, into_project=into_project, new_slug=new_slug).model_dump(
        mode="json"
    )


def tool_sync(store: Store, current_project: str, specs_dir: str = ".specs") -> dict:
    from spec_manager.sync import sync_project

    report = sync_project(store, current_project, specs_dir)
    return {
        "created": report.created,
        "pushed": report.pushed,
        "pulled": report.pulled,
        "skipped": report.skipped,
    }


# ------------------------------------------------------------- server wiring

def build_server(store: Store, current_project: str | None) -> FastMCP:
    mcp = FastMCP("spec-manager")

    @mcp.tool()
    def search_specs(query: str, project: str | None = None) -> list[dict]:
        """Search specs (title / slug / body) across all projects, or within one."""
        return tool_search(store, query, project)

    @mcp.tool()
    def get_spec(project: str, slug: str) -> dict | None:
        """Fetch a single spec with its current body and metadata."""
        return tool_get_spec(store, project, slug)

    @mcp.tool()
    def list_specs(project: str | None = None) -> list[dict]:
        """List specs in a project (or across all projects if omitted)."""
        return tool_list_specs(store, project)

    @mcp.tool()
    def list_versions(project: str, slug: str) -> list[dict]:
        """List all versions of a spec."""
        return tool_list_versions(store, project, slug)

    @mcp.tool()
    def update_spec(
        project: str, slug: str, body: str, message: str | None = None
    ) -> dict:
        """Update a spec's body (creates a new version). Cross-project writes are denied."""
        return tool_update_spec(
            store, current_project or "", project, slug, body, message
        )

    @mcp.tool()
    def set_status(
        project: str, slug: str, to_status: str, note: str | None = None
    ) -> dict:
        """Advance a spec's lifecycle status (draft/in_review/approved/planned/implemented)."""
        return tool_set_status(
            store, current_project or "", project, slug, to_status, note
        )

    @mcp.tool()
    def fork_spec(from_project: str, slug: str, into_project: str, new_slug: str) -> dict:
        """Copy a spec's latest version into another project as a new spec."""
        return tool_fork(store, from_project, slug, into_project, new_slug)

    @mcp.tool()
    def sync_specs(specs_dir: str = ".specs") -> dict:
        """Sync the local .specs/ folder with central for the current project."""
        if not current_project:
            return {"error": "no current project (run `specm project register` or set SPEC_MANAGER_PROJECT)"}
        return tool_sync(store, current_project, specs_dir)

    return mcp


def _resolve_current_project() -> str | None:
    env = os.environ.get("SPEC_MANAGER_PROJECT")
    if env:
        return env
    marker = Path.cwd() / ".specs" / ".project"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip() or None
    return None


def main() -> None:
    from spec_manager.db import init_db, make_engine

    engine = make_engine()
    init_db(engine)
    build_server(Store(engine), _resolve_current_project()).run()


if __name__ == "__main__":
    main()
