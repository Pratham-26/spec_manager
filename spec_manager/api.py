"""FastAPI app: thin HTTP layer over the Store. No LLM, no AI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from spec_manager.lifecycle import InvalidTransition
from spec_manager.permissions import can_write
from spec_manager.store import ProjectNotFound, SpecNotFound, Store


# ---------------------------------------------------------------- request models

class ProjectIn(BaseModel):
    slug: str
    path: str | None = None


class SpecCreate(BaseModel):
    slug: str
    title: str
    body: str
    type: str = "feature"
    tags: list[str] = Field(default_factory=list)
    status: str = "draft"
    is_template: bool = False


class SpecUpdate(BaseModel):
    body: str
    message: str | None = None


class StatusIn(BaseModel):
    to_status: str
    note: str | None = None


class FlagIn(BaseModel):
    value: bool


class ReviewIn(BaseModel):
    version: int
    outcome: str
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class RollbackIn(BaseModel):
    target_version: int


class ForkIn(BaseModel):
    into_project: str
    new_slug: str


def create_app(store: Store | None = None) -> FastAPI:
    if store is None:
        from spec_manager.db import init_db, make_engine

        engine = make_engine()
        init_db(engine)
        store = Store(engine)

    app = FastAPI(title="spec_manager", version="0.1.0")
    app.state.store = store

    @app.exception_handler(SpecNotFound)
    @app.exception_handler(ProjectNotFound)
    async def _not_found(_request, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidTransition)
    async def _bad_request(_request, exc):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def _ensure_write(spec, project_slug: str, x_project: str | None) -> None:
        current = x_project or project_slug
        if not can_write(
            owner_project=project_slug,
            current_project=current,
            cross_project_writable=spec.cross_project_writable,
        ):
            raise HTTPException(status_code=403, detail="cross-project write not permitted")

    def _get(spec):
        if spec is None:
            raise HTTPException(status_code=404, detail="spec not found")
        return spec

    # ------------------------------------------------------------------ projects

    @app.post("/projects", status_code=201)
    def create_project(body: ProjectIn):
        return store.create_project(body.slug, path=body.path)

    @app.get("/projects/{project_slug}/specs", response_model=None)
    def list_specs(project_slug: str):
        return store.list_specs(project_slug)

    @app.get("/specs")
    def list_all_specs(project: str | None = Query(default=None)):
        return store.list_specs(project)

    # --------------------------------------------------------------------- specs

    @app.post("/projects/{project_slug}/specs", status_code=201)
    def create_spec(
        project_slug: str,
        body: SpecCreate,
        x_project: str | None = Header(default=None, alias="X-Project"),
    ):
        if x_project is not None and x_project != project_slug:
            raise HTTPException(status_code=403, detail="cross-project create not permitted")
        return store.create_spec(
            project_slug=project_slug,
            slug=body.slug,
            title=body.title,
            body=body.body,
            type=body.type,
            tags=body.tags,
            status=body.status,
            is_template=body.is_template,
        )

    @app.get("/projects/{project_slug}/specs/{slug}")
    def get_spec(project_slug: str, slug: str):
        return _get(store.get_spec(project_slug, slug))

    @app.put("/projects/{project_slug}/specs/{slug}")
    def update_spec(
        project_slug: str,
        slug: str,
        body: SpecUpdate,
        x_project: str | None = Header(default=None, alias="X-Project"),
    ):
        spec = _get(store.get_spec(project_slug, slug))
        _ensure_write(spec, project_slug, x_project)
        store.update_spec_body(project_slug, slug, body=body.body, message=body.message)
        return store.get_spec(project_slug, slug)

    # ------------------------------------------------------------------ versions

    @app.get("/projects/{project_slug}/specs/{slug}/versions")
    def list_versions(project_slug: str, slug: str):
        return store.list_versions(project_slug, slug)

    @app.get("/projects/{project_slug}/specs/{slug}/versions/{version}")
    def get_version(project_slug: str, slug: str, version: int):
        return store.get_version(project_slug, slug, version)

    @app.post("/projects/{project_slug}/specs/{slug}/rollback")
    def rollback(
        project_slug: str,
        slug: str,
        body: RollbackIn,
        x_project: str | None = Header(default=None, alias="X-Project"),
    ):
        spec = _get(store.get_spec(project_slug, slug))
        _ensure_write(spec, project_slug, x_project)
        return store.rollback(project_slug, slug, body.target_version)

    # ----------------------------------------------------- status / lifecycle

    @app.post("/projects/{project_slug}/specs/{slug}/status")
    def set_status(
        project_slug: str,
        slug: str,
        body: StatusIn,
        x_project: str | None = Header(default=None, alias="X-Project"),
    ):
        spec = _get(store.get_spec(project_slug, slug))
        _ensure_write(spec, project_slug, x_project)
        return store.set_status(project_slug, slug, body.to_status, note=body.note)

    @app.get("/projects/{project_slug}/specs/{slug}/events")
    def list_events(project_slug: str, slug: str):
        return store.list_status_events(project_slug, slug)

    @app.put("/projects/{project_slug}/specs/{slug}/cross-project-writable")
    def set_cross_project_writable(
        project_slug: str,
        slug: str,
        body: FlagIn,
        x_project: str | None = Header(default=None, alias="X-Project"),
    ):
        spec = _get(store.get_spec(project_slug, slug))
        _ensure_write(spec, project_slug, x_project)
        return store.set_cross_project_writable(project_slug, slug, body.value)

    # ------------------------------------------------------------------ reviews

    @app.post("/projects/{project_slug}/specs/{slug}/reviews", status_code=201)
    def add_review(project_slug: str, slug: str, body: ReviewIn):
        _get(store.get_spec(project_slug, slug))
        return store.add_review(
            project_slug,
            slug,
            version=body.version,
            outcome=body.outcome,
            issues=body.issues,
            recommendations=body.recommendations,
        )

    @app.get("/projects/{project_slug}/specs/{slug}/reviews")
    def list_reviews(project_slug: str, slug: str):
        return store.list_reviews(project_slug, slug)

    # ----------------------------------------------------------- search & fork

    @app.get("/search")
    def search(q: str = Query(...), project: str | None = Query(default=None)):
        return store.search(q, project_slug=project)

    @app.post("/projects/{project_slug}/specs/{slug}/fork", status_code=201)
    def fork(project_slug: str, slug: str, body: ForkIn):
        return store.fork(project_slug, slug, into_project=body.into_project, new_slug=body.new_slug)

    @app.get("/health")
    def health():
        return {"ok": True}

    ui_dir = Path(__file__).parent / "ui"
    if ui_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app
