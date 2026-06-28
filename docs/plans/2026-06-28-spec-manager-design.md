# Spec Manager — Design (Draft)

**Status:** Draft — in active discussion. Do not implement until the *Open Questions* are resolved.
**Date:** 2026-06-28
**Repo:** `C:\Coding\spec_manager` → `origin: https://github.com/Pratham-26/spec_manager.git` (branch `main`)

---

## Context / Problem

Today, specs live in **per-project isolation** — each project has its own `.specs/` folder (the `spec-architect` pattern: `index.md` + one markdown file per feature). Specs are treated as "take inspiration when needed," which means manually digging through other projects to recall a design or copy a pattern.

**Pain moments:**
1. *Recall across projects* — "I'm in project B and want to recall a decision, but it lives in project A's `.specs/`; I have to hunt for it."
2. *Reuse across projects* — "I keep rewriting the same spec patterns; I want a shared library to start from."

**Intended outcome:** one **central, DB-backed store** that makes specs accessible (and reusable) across all projects, accessed by LLMs *only* through governed tools — never directly.

---

## Goals

1. **Read aggregator** — find / search / recall any spec across all projects from one place.
2. **Template / registry** — reuse spec patterns as starting points for new work.

## Non-goals

- **No LLM / AI on the server.** The server is a pure data + API layer. Intelligence lives in Claude Code skills, locally.
- **No direct LLM→server access.** The LLM reaches the store *only* through MCP tools wrapped by skills.

---

## Decided (so far)

- **Layered architecture** with a hard separation: dumb data server ↔ governed tool layer ↔ LLM.
- **Server is DB-backed**, central source of truth, with **versioning** for every spec change.
- **Access is via an MCP server** exposing tools; **Claude Code skills** wrap those tools and encode the **guardrails**.
- **Guardrails:** specs are project-scoped. Managing (creating/editing/deleting) **another project's** specs requires **explicit permission**. (Read access policy TBD — see Open Q6.)
- **Versioning:** every change to a spec is recorded (history, diff, rollback). Exact model TBD — see Open Q5.
- **Deployment:** **single-user local** server (runs on `localhost`) is the **v1 base**; **team/hosted** is a **future expansion**. Architect from day one so multi-user can be added later without a rewrite — i.e. bake in an `owner` field on specs, an auth seam, and a swappable DB layer now, even though v1 only has one user.
- **Stack:** **Python + FastAPI** for the server/API; **SQLAlchemy** for the data layer.
- **Database:** **SQLite for v1** (via SQLAlchemy ORM) so **Postgres is a config swap** when team/hosted (B) arrives.
- **MCP topology:** a thin **`stdio` MCP client** (launched per Claude Code session) calls the always-running **HTTP API server**. Server stays the single source of truth; the (later) web UI and the MCP layer share one backend.
- **UI:** **pure HTML/CSS/JS** (no framework, no build step) served by FastAPI. Read/search browser first; editing stays via MCP/skills; UI editing later.
- **Repo initialised:** `git init`, branch `main`, `origin` wired, minimal `.gitignore` (`.claude/settings.local.json`).

## Proposed Architecture

```
┌──────────────────────────────────────────────────────┐
│  Your projects (each a local Claude Code session)     │
│                                                       │
│   ┌──────────────┐      Guardrails + "how to use"     │
│   │ Spec skills  │      rules live HERE (markdown).   │
│   └──────┬───────┘                                    │
│          │ MCP tool calls                             │
│   ┌──────▼───────┐      Thin tool surface.            │
│   │  MCP server  │      No business logic.            │
│   └──────┬───────┘                                    │
└──────────┼───────────────────────────────────────────┘
           │ HTTP API  (plain data — no LLM, no AI)
    ┌──────▼───────────────────────────────┐
    │  Spec Manager Server                  │
    │  • data model + persistence           │
    │  • versioning engine                  │
    │  • permission / guardrail enforcement │
    │  • search                             │
    └──────┬───────────────────┬───────────┘
           │                   │
    ┌──────▼──────┐     ┌──────▼──────────────┐
    │  Database   │     │  Web UI  (later)    │
    └─────────────┘     └─────────────────────┘
```

**Data flow for a typical "find a spec" (Goal 1):**
LLM → skill → MCP tool `search_specs(query, project?)` → HTTP GET `/specs?q=…` → DB → results back up the chain.

**Data flow for "edit a spec in another project" (guardrail):**
LLM → skill → MCP tool `request_cross_project_edit(spec_id)` → server checks permission → **explicit grant required** (mechanics TBD, Open Q7) → only then `update_spec` creates a new version.

---

## Core Concepts (proposed — needs confirmation)

| Concept | Working definition | Status |
|---|---|---|
| **Project** | A registered project (unique slug) that owns specs. | Resolved (D2) |
| **Spec** | Markdown body + YAML-frontmatter metadata; the managed unit. | Resolved (B1) |
| **SpecVersion** | Immutable whole-body snapshot of a spec (monotonic version no). | Resolved (B3) |
| **Lifecycle status** | A spec's stage in the obra/superpowers flow (draft→…→implemented). | Resolved (below) |
| **Review** | A review record (approved/issues) attached to a spec version. | Resolved (below) |
| **Permission** | Grant allowing writes to another project's specs (opt-in flag + confirm). | Resolved (C2) |
| **Template** | Any spec flagged `is_template`; forked into a target project. | Resolved (D1) |

## Spec Lifecycle (follows obra/superpowers)

Every spec carries a **`status`** field drawn from the `obra/superpowers` brainstorm→plan→implement flow. The server stores status and enforces valid transitions (a guardrail). **The review itself runs client-side** via a skill (no LLM on the server) using the `spec-document-reviewer-prompt` criteria (Completeness, Consistency, Clarity, Scope, YAGNI) — the server only records the outcome.

**States:** `draft` → `in_review` → `approved` → `planned` → `implemented`   (+ `deprecated` / `superseded` reachable from any state)

**Transitions (enforced by server):**
- `draft → in_review` — spec written/committed, review requested.
- `in_review → approved` — reviewer returns *Approved* **and** user approves. (`in_review → draft` if issues found.)
- `approved → planned` — an implementation plan is linked (`plan_ref`).
- `planned → implemented` — build complete.
- any → `deprecated` (retired) / `superseded` (replaced; links to successor via `superseded_by`).

**Artifacts stored server-side:** status-transition events (from/to/when/actor/note), and a `Review` record per reviewed version `{outcome: approved|issues, issues[], recommendations[], reviewed_at, reviewer}`. Lifecycle status is **independent of content versioning** (B3) — edit body without changing status, or advance status without editing body.

---

## Open Questions (resolve before implementation)

Grouped by how much they gate the design. **My tentative default is in italics** where I have one — treat as a starting point to react to, not a decision.

### A. Foundational — decide first

**A1. ✅ RESOLVED.** Build on **(A) single-user local** as the v1 base; **(B) team/hosted** is a later expansion. Architect now (owner field, auth seam, swappable DB) so B can be layered on without a rewrite.

**A2. ✅ RESOLVED.** **Python + FastAPI** (SQLAlchemy data layer).

**A3. ✅ RESOLVED.** **SQLite for v1** via SQLAlchemy ORM; **Postgres is a later swap** for team/hosted (B).

**A4. ✅ RESOLVED.** Thin **`stdio` MCP client** (launched per session) → always-running **HTTP API server**. One backend shared by MCP + (later) web UI.

### B. Modeling — what is the data

**B1. ✅ RESOLVED.** A spec = **YAML frontmatter (metadata) + markdown body**, one file per spec.
- Frontmatter: `slug`, `project`, `title`, `type` (loose category — `feature`/`decision`/`adr`/`api`/`pattern`), `tags`, `status` (lifecycle — see Spec Lifecycle), `is_template`, `created_at`, `updated_at`, `version`, `plan_ref` (when planned), `superseded_by` (when superseded).
- Body: free-form markdown — this is what the 10%-diff sync gate compares.
- On disk: `<project>/.specs/<slug>.md` (+ generated `.specs/index.md`). In DB: `Spec` (live metadata) + `SpecVersion` (immutable body snapshots).
- Follows the `obra/superpowers` design-doc authoring style (Context/Objective/etc.) but slug-keyed as a persistent entity.

**B2. ✅ RESOLVED — hybrid (central + local, script-synced).** Both exist:
- **Central DB = source of truth** (versioning, permissions, cross-project search, templates).
- **Local `.specs/<project>/` = per-project working copy** of readable/editable markdown files — so humans *and* the LLM's `Read` tool can read specs as plain files (fast local read path), and existing `spec-architect` flow keeps working.
- **Sync is deterministic scripts, NOT an LLM/agent** (agents are too expensive for sync). Mechanism: a file-watcher for "always in sync" + a manual `specm sync` command. No MCP/LLM in the sync path.
- **Cross-project reads are NOT synced into your local folder** — they go through central/MCP (Goal 1). Local sync is scoped to the *current project's* specs only (so sync never touches another project → never trips the cross-project guardrail).
- Existing `spec-architect` `.specs/` folders = one-time import source into central, then continue as the synced working copy.

**B2a. ✅ RESOLVED.** Local working copy is **editable** (bidirectional).

**B2b. ✅ RESOLVED — sync policy (no watcher; one command/tool).** No always-on daemon. Sync is a single `specm sync` command (also exposable as an MCP tool the skill can call). Per-spec rules:
- **Auto-push** local→central (creating a new version) only when the spec **body differs from central by >10%** (sequence-similarity ratio) — avoids versioning trivial typos/whitespace.
- **Force-sync** any spec when the user explicitly asks (ignores the 10% gate).
- **Pull-down** central→local whenever central has a newer version than local (central is source of truth).
- **Conflict (both sides changed):** v1 = last-write-wins, with the superseded content retained as a prior version (lossless). Refine later if it bites.
- The 10% is measured on the **markdown body**; metadata changes (status/tags) sync regardless.

**B3. ✅ RESOLVED.** **Append-only whole-spec snapshots**: each save = a new immutable `SpecVersion` with a monotonic integer (`v1, v2, …`) + author/timestamp/message. No branches/DAG (YAGNI). **Rollback** = create a *new* version whose content equals the target (history is never destroyed). Diff = simple text diff between two versions.

### C. Guardrails & access — the distinctive part

**C1. ✅ RESOLVED.** **Read open** across all projects (that's Goal 1). Only **create/edit/delete/status-change** of another project's specs requires explicit permission (C2).

**C2. ✅ RESOLVED.** Two-layer:
- **Server (enforcer):** a per-spec `cross_project_writable` flag (default **off**). Cross-project write/status-change calls are **rejected with 403** unless the flag is on for that spec. (v1 single-user: the "owner" is you; the flag is the consent switch.)
- **Skill (UX):** before any cross-project write, the skill surfaces a confirmation to the user and only proceeds on yes. Belt-and-suspenders; the server is the real gate.

### D. Product/UX details — can firm up slightly later

**D1. ✅ RESOLVED.** Any spec can be flagged `is_template`. A `fork_spec(spec_id, into_project, new_slug)` tool copies its **latest version** into the target project as a **new, independent spec** (status `draft`, its own version history). The fork records `forked_from` for traceability.

**D2. ✅ RESOLVED.** **Explicit registration** with a unique slug (`specm project register <slug>`). A local checkout declares its project via a `.specs/.project` file (contains the slug) or env var; the sync tool / MCP client reads it to scope operations. Multiple checkouts may map to one slug.

**D3. UI tech ✅ RESOLVED:** pure HTML/CSS/JS (no framework, no build step), served by FastAPI. **Scope (still default):** read/search browser first; editing via MCP/skills; UI editing later.

---

## v1 Implementation Scope (end-to-end, lean)

```
spec_manager/
├── server/            # FastAPI app
│   ├── db.py          # engine/session (SQLite; Postgres-swappable URL)
│   ├── models.py      # Project, Spec, SpecVersion, Review, StatusEvent
│   ├── lifecycle.py   # status state-machine + transition validation
│   ├── permissions.py # cross_project_writable enforcement
│   └── main.py        # FastAPI routes + static UI mount
├── mcp_server/        # thin stdio MCP client → HTTP API (tool surface)
├── sync.py            # `specm sync` — bidirectional, 10%-gate, force, pull-down
├── cli.py             # `specm` entrypoint: serve / sync / project register
├── skills/            # Claude Code skill(s): wrap MCP tools + guardrails
├── ui/                # static HTML/CSS/JS (read/search browser)
├── tests/             # pytest
└── pyproject.toml     # fastapi, uvicorn, sqlalchemy, pydantic, mcp, pytest
```

**v1 delivers:** project registration · spec CRUD + versioning + diff/rollback · lifecycle state-machine + review-record storage · cross-project read (open) + write (permission-gated) · template flag + fork · `specm sync` (bidirectional, 10%-gate) · cross-project search · read-only web UI · MCP tool surface + one governing skill.

**Lean by design:** SQLite (no DB server), no JS build step, no ORM magic, minimal deps, one config (DB URL + port).

## Test Plan (must pass before "done")

- **Models/DB:** create project/spec/version; version immutability; rollback creates a new version.
- **Lifecycle:** all valid transitions pass; invalid transitions rejected; status independent of version.
- **Permissions:** cross-project read OK; cross-project write → 403 when flag off, OK when on.
- **API:** CRUD, search, fork, version list/diff, rollback — via FastAPI `TestClient`.
- **Sync:** >10% diff pushes a new version; <10% skipped; force pushes; pull-down overwrites stale local; conflict = last-write-wins + history retained. (tmp dirs.)
- **MCP tools:** smoke-test the tool surface against the API.
- **CLI:** `specm project register` + `specm sync` happy paths.

Run `pytest` — all green before marking complete.

---

## Out-of-scope / parked

- Multi-user auth, RBAC, hosting infra — until A1 says otherwise.
- AI/LLM features server-side (summarization, semantic search) — explicitly excluded; revisit only if Goals 1/2 demand it.
- Real-time collaboration / concurrent-edit merging.
