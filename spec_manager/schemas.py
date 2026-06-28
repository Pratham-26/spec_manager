"""Pydantic DTOs returned by the store and serialized by the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectOut(BaseModel):
    slug: str
    path: str | None = None
    created_at: datetime


class SpecOut(BaseModel):
    id: int
    project_slug: str
    slug: str
    title: str
    type: str = "feature"
    tags: list[str] = Field(default_factory=list)
    status: str = "draft"
    is_template: bool = False
    cross_project_writable: bool = False
    current_version: int = 1
    plan_ref: str | None = None
    superseded_by: str | None = None
    forked_from: int | None = None
    created_at: datetime
    updated_at: datetime
    current_body: str = ""


class SpecVersionOut(BaseModel):
    id: int
    spec_id: int
    version: int
    body: str
    author: str
    message: str | None = None
    created_at: datetime


class ReviewOut(BaseModel):
    id: int
    spec_id: int
    version: int
    outcome: str
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    reviewer: str = "skill"
    created_at: datetime


class StatusEventOut(BaseModel):
    id: int
    spec_id: int
    from_status: str | None = None
    to_status: str
    actor: str = "local"
    note: str | None = None
    created_at: datetime
