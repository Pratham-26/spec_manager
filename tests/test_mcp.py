from spec_manager.mcp_server import (
    tool_get_spec,
    tool_search,
    tool_set_status,
    tool_update_spec,
)


def test_tool_search(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="oauth")
    hits = tool_search(store, "auth")
    assert any(h["slug"] == "auth" for h in hits)


def test_tool_get_spec(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    res = tool_get_spec(store, "app", "auth")
    assert res["slug"] == "auth" and res["current_body"] == "x"


def test_tool_get_missing_spec_returns_none(store):
    store.create_project("app")
    assert tool_get_spec(store, "app", "nope") is None


def test_tool_update_same_project_ok(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    res = tool_update_spec(
        store, current_project="app", project="app", slug="auth", body="y"
    )
    assert res["current_body"] == "y"


def test_tool_update_cross_project_denied(store):
    store.create_project("app")
    store.create_project("other")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    res = tool_update_spec(
        store, current_project="other", project="app", slug="auth", body="hacked"
    )
    assert "error" in res


def test_tool_update_cross_project_allowed_with_flag(store):
    store.create_project("app")
    store.create_project("other")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    store.set_cross_project_writable("app", "auth", True)
    res = tool_update_spec(
        store, current_project="other", project="app", slug="auth", body="ok"
    )
    assert res["current_body"] == "ok"


def test_tool_set_status(store):
    store.create_project("app")
    store.create_spec(project_slug="app", slug="auth", title="Auth", body="x")
    res = tool_set_status(
        store, current_project="app", project="app", slug="auth", to_status="in_review"
    )
    assert res["status"] == "in_review"


def test_build_server_registers_tools(store):
    import asyncio

    from spec_manager.mcp_server import build_server

    server = build_server(store, "app")
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert {"search_specs", "get_spec", "update_spec", "set_status", "fork_spec"}.issubset(names)
