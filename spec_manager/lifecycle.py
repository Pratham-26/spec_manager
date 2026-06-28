"""Spec lifecycle state-machine (follows the obra/superpowers flow)."""
from __future__ import annotations

STATUSES = (
    "draft",
    "in_review",
    "approved",
    "planned",
    "implemented",
    "deprecated",
    "superseded",
)

_TERMINAL = {"deprecated", "superseded"}

# Explicit forward/revise transitions. Reaching deprecated/superseded is
# allowed from any non-terminal state (handled separately below).
_FORWARD = {
    ("draft", "in_review"),
    ("in_review", "approved"),
    ("in_review", "draft"),
    ("approved", "planned"),
    ("planned", "implemented"),
}


class InvalidTransition(Exception):
    """Raised when a status transition is not permitted."""


def is_valid_status(status: str) -> bool:
    return status in STATUSES


def can_transition(frm: str, to: str) -> bool:
    if not is_valid_status(frm) or not is_valid_status(to):
        return False
    if frm in _TERMINAL:
        return False
    if to in _TERMINAL:
        return True  # any non-terminal -> deprecated/superseded
    return (frm, to) in _FORWARD


def transition(frm: str, to: str) -> str:
    if not can_transition(frm, to):
        raise InvalidTransition(f"cannot transition {frm!r} -> {to!r}")
    return to
