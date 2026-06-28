"""Data-access layer. Returns detached Pydantic DTOs (session-agnostic)."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from spec_manager import models as M
from spec_manager.lifecycle import InvalidTransition, can_transition
from spec_manager.schemas import (
    ProjectOut,
    ReviewOut,
    SpecOut,
    SpecVersionOut,
    StatusEventOut,
)


class SpecNotFound(LookupError):
    pass


class ProjectNotFound(LookupError):
    pass


class Store:
    def __init__(self, engine):
        self._engine = engine
        self._Session = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def session(self):
        s = self._Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # ------------------------------------------------------------------ projects

    def create_project(self, slug: str, path: str | None = None) -> ProjectOut:
        with self.session() as s:
            proj = M.Project(slug=slug, path=path)
            s.add(proj)
            s.flush()
            return ProjectOut(slug=proj.slug, path=proj.path, created_at=proj.created_at)

    def get_project(self, slug: str) -> ProjectOut | None:
        with self.session() as s:
            proj = s.get(M.Project, slug)
            if proj is None:
                return None
            return ProjectOut(slug=proj.slug, path=proj.path, created_at=proj.created_at)

    # --------------------------------------------------------------------- specs

    def create_spec(
        self,
        *,
        project_slug: str,
        slug: str,
        title: str,
        body: str,
        type: str = "feature",
        tags: list[str] | None = None,
        status: str = "draft",
        is_template: bool = False,
        author: str = "local",
        message: str | None = None,
        forked_from: int | None = None,
    ) -> SpecOut:
        with self.session() as s:
            if s.get(M.Project, project_slug) is None:
                raise ProjectNotFound(f"project {project_slug!r} not found")
            spec = M.Spec(
                project_slug=project_slug,
                slug=slug,
                title=title,
                type=type,
                tags=list(tags or []),
                status=status,
                is_template=is_template,
                current_version=1,
                forked_from=forked_from,
            )
            s.add(spec)
            s.flush()
            s.add(
                M.SpecVersion(
                    spec_id=spec.id, version=1, body=body, author=author, message=message or "initial"
                )
            )
            s.flush()
            return self._spec_out(s, spec)

    def get_spec(self, project_slug: str, slug: str) -> SpecOut | None:
        with self.session() as s:
            spec = self._get_spec(s, project_slug, slug)
            if spec is None:
                return None
            return self._spec_out(s, spec)

    def list_specs(self, project_slug: str | None = None) -> list[SpecOut]:
        with self.session() as s:
            stmt = select(M.Spec).order_by(M.Spec.project_slug, M.Spec.slug)
            if project_slug is not None:
                stmt = stmt.where(M.Spec.project_slug == project_slug)
            return [self._spec_out(s, spec) for spec in s.execute(stmt).scalars().all()]

    # ------------------------------------------------------------------ versions

    def update_spec_body(
        self,
        project_slug: str,
        slug: str,
        *,
        body: str,
        message: str | None = None,
        author: str = "local",
    ) -> SpecVersionOut:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            next_version = spec.current_version + 1
            version = M.SpecVersion(
                spec_id=spec.id, version=next_version, body=body, author=author, message=message
            )
            s.add(version)
            spec.current_version = next_version
            s.flush()
            return self._version_out(version)

    def get_version(self, project_slug: str, slug: str, version: int) -> SpecVersionOut:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            row = s.execute(
                select(M.SpecVersion).where(
                    M.SpecVersion.spec_id == spec.id, M.SpecVersion.version == version
                )
            ).scalar_one_or_none()
            if row is None:
                raise SpecNotFound(f"version {version} of {project_slug}/{slug} not found")
            return self._version_out(row)

    def list_versions(self, project_slug: str, slug: str) -> list[SpecVersionOut]:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            rows = s.execute(
                select(M.SpecVersion)
                .where(M.SpecVersion.spec_id == spec.id)
                .order_by(M.SpecVersion.version.asc())
            ).scalars().all()
            return [self._version_out(r) for r in rows]

    def rollback(
        self,
        project_slug: str,
        slug: str,
        target_version: int,
        *,
        author: str = "local",
        message: str | None = None,
    ) -> SpecVersionOut:
        """Create a NEW version whose body copies the target (history preserved)."""
        target = self.get_version(project_slug, slug, target_version)
        return self.update_spec_body(
            project_slug,
            slug,
            body=target.body,
            author=author,
            message=message or f"rollback to v{target_version}",
        )

    # ----------------------------------------------------- status / lifecycle

    def set_status(
        self,
        project_slug: str,
        slug: str,
        to_status: str,
        *,
        actor: str = "local",
        note: str | None = None,
    ) -> SpecOut:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            if not can_transition(spec.status, to_status):
                raise InvalidTransition(f"cannot transition {spec.status!r} -> {to_status!r}")
            s.add(
                M.StatusEvent(
                    spec_id=spec.id,
                    from_status=spec.status,
                    to_status=to_status,
                    actor=actor,
                    note=note,
                )
            )
            spec.status = to_status
            s.flush()
            return self._spec_out(s, spec)

    def list_status_events(self, project_slug: str, slug: str) -> list[StatusEventOut]:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            rows = (
                s.execute(
                    select(M.StatusEvent)
                    .where(M.StatusEvent.spec_id == spec.id)
                    .order_by(M.StatusEvent.id.asc())
                )
                .scalars()
                .all()
            )
            return [
                StatusEventOut(
                    id=r.id,
                    spec_id=r.spec_id,
                    from_status=r.from_status,
                    to_status=r.to_status,
                    actor=r.actor,
                    note=r.note,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    def set_cross_project_writable(
        self, project_slug: str, slug: str, value: bool
    ) -> SpecOut:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            spec.cross_project_writable = bool(value)
            s.flush()
            return self._spec_out(s, spec)

    # ----------------------------------------------------------------- reviews

    def add_review(
        self,
        project_slug: str,
        slug: str,
        *,
        version: int,
        outcome: str,
        issues: list[str] | None = None,
        recommendations: list[str] | None = None,
        reviewer: str = "skill",
    ) -> ReviewOut:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            rev = M.Review(
                spec_id=spec.id,
                version=version,
                outcome=outcome,
                issues=list(issues or []),
                recommendations=list(recommendations or []),
                reviewer=reviewer,
            )
            s.add(rev)
            s.flush()
            return self._review_out(rev)

    def list_reviews(self, project_slug: str, slug: str) -> list[ReviewOut]:
        with self.session() as s:
            spec = self._require_spec(s, project_slug, slug)
            rows = (
                s.execute(
                    select(M.Review)
                    .where(M.Review.spec_id == spec.id)
                    .order_by(M.Review.id.asc())
                )
                .scalars()
                .all()
            )
            return [self._review_out(r) for r in rows]

    # ------------------------------------------------------- search & fork

    def search(self, query: str, project_slug: str | None = None) -> list[SpecOut]:
        pattern = f"%{query.lower()}%"
        with self.session() as s:
            stmt = (
                select(M.Spec)
                .join(
                    M.SpecVersion,
                    (M.SpecVersion.spec_id == M.Spec.id)
                    & (M.SpecVersion.version == M.Spec.current_version),
                )
                .where(
                    M.Spec.title.ilike(pattern)
                    | M.Spec.slug.ilike(pattern)
                    | M.SpecVersion.body.ilike(pattern)
                )
                .order_by(M.Spec.project_slug, M.Spec.slug)
            )
            if project_slug is not None:
                stmt = stmt.where(M.Spec.project_slug == project_slug)
            return [self._spec_out(s, sp) for sp in s.execute(stmt).scalars().all()]

    def fork(
        self, project_slug: str, slug: str, *, into_project: str, new_slug: str
    ) -> SpecOut:
        source = self.get_spec(project_slug, slug)
        if source is None:
            raise SpecNotFound(f"spec {project_slug}/{slug} not found")
        if self.get_project(into_project) is None:
            raise ProjectNotFound(f"project {into_project!r} not found")
        return self.create_spec(
            project_slug=into_project,
            slug=new_slug,
            title=source.title,
            body=source.current_body,
            type=source.type,
            tags=list(source.tags),
            status="draft",
            is_template=False,
            author="fork",
            message=f"forked from {project_slug}/{slug}",
            forked_from=source.id,
        )

    # ----------------------------------------------------------------- internals

    @staticmethod
    def _review_out(r: M.Review) -> ReviewOut:
        return ReviewOut(
            id=r.id,
            spec_id=r.spec_id,
            version=r.version,
            outcome=r.outcome,
            issues=list(r.issues or []),
            recommendations=list(r.recommendations or []),
            reviewer=r.reviewer,
            created_at=r.created_at,
        )

    @staticmethod
    def _require_spec(s, project_slug: str, slug: str) -> M.Spec:
        spec = Store._get_spec(s, project_slug, slug)
        if spec is None:
            raise SpecNotFound(f"spec {project_slug}/{slug} not found")
        return spec

    @staticmethod
    def _version_out(v: M.SpecVersion) -> SpecVersionOut:
        return SpecVersionOut(
            id=v.id,
            spec_id=v.spec_id,
            version=v.version,
            body=v.body,
            author=v.author,
            message=v.message,
            created_at=v.created_at,
        )

    @staticmethod
    def _get_spec(s, project_slug: str, slug: str):
        return s.execute(
            select(M.Spec).where(M.Spec.project_slug == project_slug, M.Spec.slug == slug)
        ).scalar_one_or_none()

    @staticmethod
    def _spec_out(s, spec: M.Spec) -> SpecOut:
        body = (
            s.execute(
                select(M.SpecVersion.body).where(
                    M.SpecVersion.spec_id == spec.id,
                    M.SpecVersion.version == spec.current_version,
                )
            ).scalar_one_or_none()
            or ""
        )
        return SpecOut(
            id=spec.id,
            project_slug=spec.project_slug,
            slug=spec.slug,
            title=spec.title,
            type=spec.type,
            tags=list(spec.tags or []),
            status=spec.status,
            is_template=spec.is_template,
            cross_project_writable=spec.cross_project_writable,
            current_version=spec.current_version,
            plan_ref=spec.plan_ref,
            superseded_by=spec.superseded_by,
            forked_from=spec.forked_from,
            created_at=spec.created_at,
            updated_at=spec.updated_at,
            current_body=body,
        )
