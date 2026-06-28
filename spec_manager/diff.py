"""Body change ratio for the sync gate (stdlib only)."""
from __future__ import annotations

from difflib import SequenceMatcher


def change_ratio(old: str, new: str) -> float:
    """Fraction of the body that changed: 0.0 identical, ~1.0 totally different.

    Defined as ``1 - similarity`` so the sync gate can test ``ratio > 0.10``.
    """
    if old == new:
        return 0.0
    return 1.0 - SequenceMatcher(None, old, new).ratio()
