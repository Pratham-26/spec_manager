"""YAML-frontmatter + markdown body parsing (stdlib + pyyaml only)."""
from __future__ import annotations

import yaml


def parse(text: str) -> tuple[dict, str]:
    """Split a spec file into (frontmatter dict, markdown body).

    Frontmatter is a leading ``---`` ... ``---`` block. Files without it return
    ``({}, text)``.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    fm_lines: list[str] = []
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        fm_lines.append(lines[i])
        i += 1
    meta = yaml.safe_load("".join(fm_lines)) or {}
    body = "".join(lines[i + 1 :]) if i < len(lines) else ""
    return meta, body


def dump(meta: dict, body: str) -> str:
    """Serialize frontmatter + body back to a spec file string."""
    fm = yaml.safe_dump(meta, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n{body}"
