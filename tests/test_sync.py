from spec_manager.frontmatter import dump, parse
from spec_manager.sync import sync_project


def write_spec(directory, slug, body, *, version=1, title=None):
    p = directory / f"{slug}.md"
    p.write_text(
        dump({"slug": slug, "title": title or slug, "version": version}, body), encoding="utf-8"
    )
    return p


def test_new_local_file_creates_central_spec(store, tmp_path):
    store.create_project("app")
    write_spec(tmp_path, "auth", "# Auth\nOAuth2.")
    report = sync_project(store, "app", tmp_path)
    assert report.created == 1
    assert store.get_spec("app", "auth").current_body == "# Auth\nOAuth2."
    meta, _ = parse((tmp_path / "auth.md").read_text(encoding="utf-8"))
    assert meta["version"] == 1


def test_local_large_change_pushes_new_version(store, tmp_path):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="# Auth\nOAuth2 PKCE clients.")
    write_spec(tmp_path, "auth", "# Billing\nNightly worker emails receipts and taxes.", version=1)
    report = sync_project(store, "app", tmp_path)
    assert report.pushed == 1
    assert store.get_spec("app", "auth").current_version == 2
    meta, _ = parse((tmp_path / "auth.md").read_text(encoding="utf-8"))
    assert meta["version"] == 2


def test_small_change_is_skipped(store, tmp_path):
    body = "# Auth\nOAuth2 with PKCE for all clients."
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body=body)
    write_spec(tmp_path, "auth", body + "!", version=1)
    report = sync_project(store, "app", tmp_path)
    assert report.skipped == 1
    assert store.get_spec("app", "auth").current_version == 1


def test_force_pushes_even_small_change(store, tmp_path):
    body = "# Auth\nOAuth2 with PKCE for all clients."
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body=body)
    write_spec(tmp_path, "auth", body + "!", version=1)
    report = sync_project(store, "app", tmp_path, force=True)
    assert report.pushed == 1
    assert store.get_spec("app", "auth").current_version == 2


def test_central_newer_is_pulled_down(store, tmp_path):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="v1")
    store.update_spec_body("app", "auth", body="v2 from central")
    write_spec(tmp_path, "auth", "v1", version=1)
    report = sync_project(store, "app", tmp_path)
    assert report.pulled == 1
    meta, body = parse((tmp_path / "auth.md").read_text(encoding="utf-8"))
    assert body == "v2 from central"
    assert meta["version"] == 2


def test_matching_local_and_central_is_skipped(store, tmp_path):
    body = "# Auth\nOAuth2 with PKCE for all clients."
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body=body)
    write_spec(tmp_path, "auth", body, version=1)
    report = sync_project(store, "app", tmp_path)
    assert report.skipped == 1


def test_central_only_spec_is_pulled_to_local(store, tmp_path):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="central only")
    report = sync_project(store, "app", tmp_path)
    assert report.pulled == 1
    _, body = parse((tmp_path / "auth.md").read_text(encoding="utf-8"))
    assert body == "central only"
