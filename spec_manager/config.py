"""Configuration (env-driven, no secrets). Config is test-exempt per TDD skill."""
from __future__ import annotations

import os
from pathlib import Path


def default_db_path() -> Path:
    base = os.environ.get("SPEC_MANAGER_DATA_DIR")
    if base:
        return Path(base) / "spec_manager.db"
    return Path.home() / ".spec_manager" / "spec_manager.db"


def database_url() -> str:
    return os.environ.get("SPEC_MANAGER_DB_URL") or f"sqlite:///{default_db_path()}"


SERVER_HOST = os.environ.get("SPEC_MANAGER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SPEC_MANAGER_PORT", "8777"))

# Body-diff ratio above which a local edit auto-pushes a new version.
SYNC_DIFF_THRESHOLD = 0.10
