from spec_manager.cli import current_project, main


def test_current_project_none_without_marker(tmp_path):
    assert current_project(tmp_path) is None


def test_register_creates_project_and_marker(store, tmp_path):
    code = main(["project", "register", "app", "--path", str(tmp_path)], store=store)
    assert code == 0
    assert store.get_project("app") is not None
    marker = tmp_path / ".specs" / ".project"
    assert marker.read_text(encoding="utf-8").strip() == "app"
    assert current_project(tmp_path / ".specs") == "app"


def test_register_is_idempotent(store, tmp_path):
    main(["project", "register", "app", "--path", str(tmp_path)], store=store)
    code = main(["project", "register", "app", "--path", str(tmp_path)], store=store)
    assert code == 0


def test_sync_command_syncs_local_specs(store, tmp_path):
    main(["project", "register", "app", "--path", str(tmp_path)], store=store)
    (tmp_path / ".specs" / "auth.md").write_text(
        "---\nslug: auth\ntitle: Auth\nversion: 0\n---\n# Auth\nOAuth2.",
        encoding="utf-8",
    )
    code = main(["sync", "--path", str(tmp_path)], store=store)
    assert code == 0
    spec = store.get_spec("app", "auth")
    assert spec is not None
    assert spec.current_body.startswith("# Auth")


def test_sync_without_registered_project_fails(store, tmp_path):
    code = main(["sync", "--path", str(tmp_path)], store=store)
    assert code != 0
