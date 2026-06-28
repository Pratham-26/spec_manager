import pytest

from spec_manager.lifecycle import InvalidTransition
from spec_manager.store import Store  # noqa: F401


def test_create_and_get_project(store):
    p = store.create_project("app", path="/code/app")
    assert p.slug == "app"
    fetched = store.get_project("app")
    assert fetched is not None and fetched.slug == "app"
    assert store.get_project("missing") is None


def test_create_spec_stores_body_with_initial_version(store):
    store.create_project("app")
    spec = store.create_spec(
        project_slug="app", slug="auth", title="Auth", body="# Auth\nOAuth2."
    )
    assert spec.slug == "auth"
    assert spec.project_slug == "app"
    assert spec.status == "draft"
    assert spec.current_version == 1
    fetched = store.get_spec("app", "auth")
    assert fetched.current_body == "# Auth\nOAuth2."


def test_spec_slugs_are_scoped_per_project(store):
    store.create_project("app")
    store.create_project("billing")
    store.create_spec(project_slug="app", slug="auth", title="A", body="app body")
    store.create_spec(project_slug="billing", slug="auth", title="B", body="billing body")
    assert store.get_spec("app", "auth").current_body == "app body"
    assert store.get_spec("billing", "auth").current_body == "billing body"


def test_update_creates_new_version_and_bumps_current(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="v1 body")
    v2 = store.update_spec_body("app", "auth", body="v2 body", message="tweak")
    assert v2.version == 2
    fetched = store.get_spec("app", "auth")
    assert fetched.current_version == 2
    assert fetched.current_body == "v2 body"


def test_old_version_body_is_immutable(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="v1 body")
    store.update_spec_body("app", "auth", body="v2 body")
    v1 = store.get_version("app", "auth", 1)
    assert v1.body == "v1 body"
    assert v1.version == 1


def test_versions_are_monotonic_and_listed(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="one")
    store.update_spec_body("app", "auth", body="two")
    store.update_spec_body("app", "auth", body="three")
    versions = store.list_versions("app", "auth")
    assert [v.version for v in versions] == [1, 2, 3]
    assert store.get_spec("app", "auth").current_version == 3


def test_rollback_creates_new_version_copying_target_and_keeps_history(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="v1 body")
    store.update_spec_body("app", "auth", body="v2 body")
    rb = store.rollback("app", "auth", target_version=1)
    assert rb.version == 3
    fetched = store.get_spec("app", "auth")
    assert fetched.current_version == 3
    assert fetched.current_body == "v1 body"
    # history intact
    assert store.get_version("app", "auth", 2).body == "v2 body"


def test_list_specs_scoped_to_project(store):
    store.create_project("app")
    store.create_project("billing")
    store.create_spec(project_slug="app", slug="auth", title="A", body="x")
    store.create_spec(project_slug="app", slug="db", title="DB", body="y")
    store.create_spec(project_slug="billing", slug="invoices", title="Inv", body="z")
    app_specs = store.list_specs("app")
    assert {s.slug for s in app_specs} == {"auth", "db"}
    all_specs = store.list_specs()
    assert {s.slug for s in all_specs} == {"auth", "db", "invoices"}


def test_set_status_advances_lifecycle_and_records_event(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    store.set_status("app", "auth", "in_review")
    assert store.get_spec("app", "auth").status == "in_review"
    store.set_status("app", "auth", "approved")
    assert store.get_spec("app", "auth").status == "approved"
    events = store.list_status_events("app", "auth")
    assert [e.to_status for e in events] == ["in_review", "approved"]


def test_set_status_rejects_invalid_transition(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    with pytest.raises(InvalidTransition):
        store.set_status("app", "auth", "implemented")


def test_cross_project_writable_flag_defaults_off_and_can_be_set(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    assert store.get_spec("app", "auth").cross_project_writable is False
    store.set_cross_project_writable("app", "auth", True)
    assert store.get_spec("app", "auth").cross_project_writable is True


def test_add_review_records_outcome_for_version(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    rev = store.add_review(
        "app", "auth", version=1, outcome="approved", recommendations=["add diagram"]
    )
    assert rev.outcome == "approved"
    revs = store.list_reviews("app", "auth")
    assert len(revs) == 1 and revs[0].version == 1


def test_search_matches_title_slug_body_across_projects(store):
    store.create_project("app")
    store.create_project("billing")
    store.create_spec(project_slug="app", slug="auth", title="Auth & Sessions", body="OAuth2 flows")
    store.create_spec(project_slug="billing", slug="invoices", title="Invoices", body="tax and auth-codes")
    hits = store.search("auth")
    slugs = {(h.project_slug, h.slug) for h in hits}
    assert ("app", "auth") in slugs
    assert ("billing", "invoices") in slugs  # body mentions "auth-codes"


def test_search_scoped_to_project(store):
    store.create_project("app")
    store.create_project("billing")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    store.create_spec(project_slug="billing", slug="auth2", title="Auth", body="x")
    hits = store.search("auth", project_slug="app")
    assert {h.slug for h in hits} == {"auth"}


def test_fork_copies_latest_version_into_new_project(store):
    store.create_project("tmpl")
    store.create_project("app")
    store.create_spec(project_slug="tmpl", slug="adr-tmpl", title="ADR", body="decision body", is_template=True)
    forked = store.fork("tmpl", "adr-tmpl", into_project="app", new_slug="adr-001")
    assert forked.project_slug == "app"
    assert forked.slug == "adr-001"
    assert forked.status == "draft"
    assert forked.current_body == "decision body"
    assert forked.forked_from is not None
