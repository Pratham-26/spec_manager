"""`specm` command-line entrypoint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spec_manager import config
from spec_manager.store import Store
from spec_manager.sync import sync_project


def current_project(specs_dir: Path | str) -> str | None:
    marker = Path(specs_dir) / ".project"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip() or None
    return None


def _default_store() -> Store:
    from spec_manager.db import init_db, make_engine

    engine = make_engine()
    init_db(engine)
    return Store(engine)


def _register(store: Store, slug: str, path: str) -> int:
    root = Path(path)
    specs_dir = root / ".specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / ".project").write_text(slug, encoding="utf-8")
    if store.get_project(slug) is None:
        store.create_project(slug, path=str(root.resolve()))
    return 0


def _sync(store: Store, path: str, force: bool) -> int:
    specs_dir = Path(path) / ".specs"
    slug = current_project(specs_dir)
    if slug is None:
        print(
            "error: no project registered here (run `specm project register <slug> --path .`)",
            file=sys.stderr,
        )
        return 2
    report = sync_project(store, slug, specs_dir, force=force)
    print(
        f"sync [{slug}]: created={report.created} pushed={report.pushed} "
        f"pulled={report.pulled} skipped={report.skipped}"
    )
    return 0


def _serve(host: str, port: int) -> None:
    import uvicorn

    from spec_manager.api import create_app

    uvicorn.run(create_app(), host=host, port=port)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specm", description="Central spec manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_project = sub.add_parser("project", help="project registration")
    proj_sub = p_project.add_subparsers(dest="project_cmd", required=True)
    p_reg = proj_sub.add_parser("register")
    p_reg.add_argument("slug")
    p_reg.add_argument("--path", default=".")

    p_sync = sub.add_parser("sync", help="sync local .specs/ <-> central")
    p_sync.add_argument("--path", default=".")
    p_sync.add_argument("--force", action="store_true")

    p_serve = sub.add_parser("serve", help="run the HTTP API server")
    p_serve.add_argument("--host", default=config.SERVER_HOST)
    p_serve.add_argument("--port", type=int, default=config.SERVER_PORT)
    return parser


def main(argv: list[str] | None = None, store: Store | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if store is None:
        store = _default_store()

    if args.cmd == "project" and args.project_cmd == "register":
        return _register(store, args.slug, args.path)
    if args.cmd == "sync":
        return _sync(store, args.path, args.force)
    if args.cmd == "serve":
        _serve(args.host, args.port)
        return 0
    return 1


def console() -> None:
    sys.exit(main())
