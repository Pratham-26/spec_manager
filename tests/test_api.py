def test_create_project_and_spec_and_read(client):
    r = client.post("/projects", json={"slug": "app"})
    assert r.status_code == 201
    assert r.json()["slug"] == "app"
    r = client.post(
        "/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "# Auth\nOAuth2."}
    )
    assert r.status_code == 201
    spec = client.get("/projects/app/specs/auth").json()
    assert spec["current_version"] == 1
    assert spec["current_body"] == "# Auth\nOAuth2."


def test_update_body_creates_version(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "v1"})
    r = client.put("/projects/app/specs/auth", json={"body": "v2", "message": "edit"})
    assert r.status_code == 200
    assert r.json()["current_version"] == 2
    versions = client.get("/projects/app/specs/auth/versions").json()
    assert [v["version"] for v in versions] == [1, 2]
    assert client.get("/projects/app/specs/auth/versions/1").json()["body"] == "v1"


def test_status_transition_enforced(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "x"})
    r = client.post("/projects/app/specs/auth/status", json={"to_status": "in_review"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_review"
    bad = client.post("/projects/app/specs/auth/status", json={"to_status": "implemented"})
    assert bad.status_code == 400


def test_cross_project_write_forbidden_without_flag(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects", json={"slug": "other"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "x"})
    r = client.put(
        "/projects/app/specs/auth", json={"body": "hacked"}, headers={"X-Project": "other"}
    )
    assert r.status_code == 403


def test_cross_project_write_allowed_with_flag(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects", json={"slug": "other"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "x"})
    client.put("/projects/app/specs/auth/cross-project-writable", json={"value": True})
    r = client.put(
        "/projects/app/specs/auth", json={"body": "ok"}, headers={"X-Project": "other"}
    )
    assert r.status_code == 200
    assert r.json()["current_body"] == "ok"


def test_cross_project_create_forbidden(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects", json={"slug": "other"})
    r = client.post(
        "/projects/app/specs",
        json={"slug": "x", "title": "X", "body": "y"},
        headers={"X-Project": "other"},
    )
    assert r.status_code == 403


def test_search_across_projects(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects", json={"slug": "billing"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "oauth"})
    client.post(
        "/projects/billing/specs", json={"slug": "inv", "title": "Invoices", "body": "auth-codes"}
    )
    hits = client.get("/search", params={"q": "auth"}).json()
    slugs = {(h["project_slug"], h["slug"]) for h in hits}
    assert ("app", "auth") in slugs
    assert ("billing", "inv") in slugs


def test_fork(client):
    client.post("/projects", json={"slug": "tmpl"})
    client.post("/projects", json={"slug": "app"})
    client.post("/projects/tmpl/specs", json={"slug": "adr", "title": "ADR", "body": "decision"})
    r = client.post(
        "/projects/tmpl/specs/adr/fork", json={"into_project": "app", "new_slug": "adr-001"}
    )
    assert r.status_code == 201
    j = r.json()
    assert j["project_slug"] == "app"
    assert j["slug"] == "adr-001"
    assert j["current_body"] == "decision"


def test_review_and_rollback(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "v1"})
    client.put("/projects/app/specs/auth", json={"body": "v2"})
    rev = client.post(
        "/projects/app/specs/auth/reviews", json={"version": 2, "outcome": "approved"}
    )
    assert rev.status_code == 201
    rb = client.post("/projects/app/specs/auth/rollback", json={"target_version": 1})
    assert rb.status_code == 200
    assert rb.json()["version"] == 3
    assert client.get("/projects/app/specs/auth").json()["current_body"] == "v1"


def test_list_all_specs_across_projects(client):
    client.post("/projects", json={"slug": "app"})
    client.post("/projects", json={"slug": "billing"})
    client.post("/projects/app/specs", json={"slug": "auth", "title": "Auth", "body": "x"})
    client.post("/projects/billing/specs", json={"slug": "inv", "title": "Inv", "body": "y"})
    r = client.get("/specs")
    assert r.status_code == 200
    slugs = {(s["project_slug"], s["slug"]) for s in r.json()}
    assert ("app", "auth") in slugs
    assert ("billing", "inv") in slugs


def test_ui_index_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
