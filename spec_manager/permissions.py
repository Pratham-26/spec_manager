"""Cross-project write permission (reads are always open)."""
from __future__ import annotations


def can_write(*, owner_project: str, current_project: str, cross_project_writable: bool) -> bool:
    """A write to a spec is allowed if it's the owning project, or the spec
    has explicitly opted into cross-project writes."""
    if current_project == owner_project:
        return True
    return bool(cross_project_writable)
