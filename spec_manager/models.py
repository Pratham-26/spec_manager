"""ORM models. Spec carries live metadata; SpecVersion holds immutable bodies."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from spec_manager.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Spec(Base):
    __tablename__ = "specs"
    __table_args__ = (UniqueConstraint("project_slug", "slug", name="uq_spec_project_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(ForeignKey("projects.slug"), index=True)
    slug: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(512))
    type: Mapped[str] = mapped_column(String(60), default="feature")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    cross_project_writable: Mapped[bool] = mapped_column(Boolean, default=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    plan_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    forked_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SpecVersion(Base):
    __tablename__ = "spec_versions"
    __table_args__ = (UniqueConstraint("spec_id", "version", name="uq_version_spec"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        ForeignKey("specs.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(120), default="local")
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        ForeignKey("specs.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120), default="local")
    note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        ForeignKey("specs.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))  # approved | issues
    issues: Mapped[list] = mapped_column(JSON, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    reviewer: Mapped[str] = mapped_column(String(120), default="skill")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
