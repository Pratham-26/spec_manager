"""Bidirectional sync between a local .specs/ folder and the central Store.

Driven by a simple tool call (`specm sync`). Pushes a new central version only
when a spec body diverges by more than the threshold, or when forced. Central is
source of truth, so a newer central version always wins on pull-down.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spec_manager import config
from spec_manager.diff import change_ratio
from spec_manager.frontmatter import dump, parse
from spec_manager.store import Store


@dataclass
class SyncReport:
    created: int = 0
    pushed: int = 0
    pulled: int = 0
    skipped: int = 0


def _write(
    path: Path,
    *,
    slug: str,
    title: str,
    status: str,
    version: int,
    body: str,
    tags: list[str] | None = None,
) -> None:
    meta: dict = {"slug": slug, "title": title, "status": status, "version": version}
    if tags:
        meta["tags"] = list(tags)
    path.write_text(dump(meta, body), encoding="utf-8")


def sync_project(
    store: Store,
    project_slug: str,
    specs_dir: Path | str,
    *,
    force: bool = False,
    threshold: float | None = None,
) -> SyncReport:
    if threshold is None:
        threshold = config.SYNC_DIFF_THRESHOLD
    specs_dir = Path(specs_dir)
    report = SyncReport()

    central = {s.slug: s for s in store.list_specs(project_slug)}
    local: dict[str, Path] = {}
    if specs_dir.exists():
        for p in sorted(specs_dir.glob("*.md")):
            if p.name == "index.md":
                continue
            local[p.stem] = p

    # local -> central
    for slug, path in local.items():
        meta, body = parse(path.read_text(encoding="utf-8"))
        local_version = int(meta.get("version", 0) or 0)
        title = meta.get("title", slug)
        tags = meta.get("tags") or []

        if slug not in central:
            store.create_spec(
                project_slug=project_slug, slug=slug, title=title, body=body, tags=list(tags)
            )
            _write(path, slug=slug, title=title, status="draft", version=1, body=body, tags=tags)
            report.created += 1
            continue

        spec = central[slug]
        if spec.current_version > local_version:
            # Central is ahead — pull it down (last-write-wins; history retained).
            _write(
                path,
                slug=slug,
                title=spec.title,
                status=spec.status,
                version=spec.current_version,
                body=spec.current_body,
                tags=list(spec.tags),
            )
            report.pulled += 1
        elif force or change_ratio(spec.current_body, body) > threshold:
            v = store.update_spec_body(project_slug, slug, body=body, author="sync")
            _write(
                path,
                slug=slug,
                title=title,
                status=spec.status,
                version=v.version,
                body=body,
                tags=tags,
            )
            report.pushed += 1
        else:
            report.skipped += 1

    # central -> local (specs that have no local file yet)
    for slug, spec in central.items():
        if slug not in local:
            _write(
                specs_dir / f"{slug}.md",
                slug=slug,
                title=spec.title,
                status=spec.status,
                version=spec.current_version,
                body=spec.current_body,
                tags=list(spec.tags),
            )
            report.pulled += 1

    return report
