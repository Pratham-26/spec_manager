---
name: spec-manager
description: Manage specs in the central spec_manager store across all projects via MCP tools. Use when creating, reading, searching, updating, forking, version-rolling-back, or advancing the lifecycle status of a spec. Enforces cross-project write guardrails — always confirm with the user before writing to another project's specs.
---

# spec-manager

A central, DB-backed store of specs shared across projects. Specs follow the
`obra/superpowers` lifecycle: `draft → in_review → approved → planned →
implemented` (+ `deprecated` / `superseded`). The server has **no LLM**; you
reach the store only through the MCP tools below.

## Setup (one-time)

The project you're working in must be registered so writes are scoped:

```bash
specm project register <project-slug> --path .
```

Keep the local `.specs/` folder in sync with central after edits:

```bash
specm sync            # pushes edits that differ >10%, pulls newer central versions
specm sync --force    # push regardless of diff
```

## Tools (MCP)

**Read (open across all projects):**
- `search_specs(query, project?)` — search title/slug/body.
- `list_specs(project?)` — list specs.
- `get_spec(project, slug)` — read a spec's current body + metadata.
- `list_versions(project, slug)` — version history.

**Write (guarded — see below):**
- `update_spec(project, slug, body, message?)` — new version.
- `set_status(project, slug, to_status, note?)` — advance lifecycle.
- `fork_spec(from_project, slug, into_project, new_slug)` — copy as a new spec.
- `sync_specs(specs_dir?)` — sync the local folder for the current project.

## Guardrails — read open, writes confirmed

- **Reading** any project's specs is always allowed (that's the point).
- **Writing** to *another* project's spec is **denied by the server** unless that
  spec has `cross_project_writable` enabled. Even then: **always ask the user and
  get explicit confirmation before a cross-project write.** State which project's
  spec you intend to change and why.
- Writes to the *current* project are fine without extra confirmation.
- Never bypass the guardrail by editing local files of another project directly.

## Lifecycle

Only valid transitions are accepted (the server rejects illegal jumps):
`draft→in_review→approved→planned→implemented`. A spec can move to
`deprecated`/`superseded` from anywhere. Reviews (approved/issues) are recorded
against a version; advance to `approved` only after a review passes and the user
agrees.

## Working copy

Specs also exist as local markdown files in `.specs/<slug>.md` (frontmatter +
body). You may read these directly. To push local edits to central, run
`specm sync`; don't hand-edit central state out-of-band.
