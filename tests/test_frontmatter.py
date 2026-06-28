from spec_manager.frontmatter import dump, parse


def test_parse_frontmatter_and_body():
    text = "---\nslug: auth\ntitle: Auth\nversion: 1\n---\n# Auth\nOAuth2."
    meta, body = parse(text)
    assert meta == {"slug": "auth", "title": "Auth", "version": 1}
    assert body == "# Auth\nOAuth2."


def test_dump_roundtrips_through_parse():
    meta = {"slug": "auth", "title": "Auth", "version": 1, "tags": ["security"]}
    body = "# Auth\nOAuth2."
    m2, b2 = parse(dump(meta, body))
    assert m2 == meta
    assert b2 == body


def test_parse_text_without_frontmatter_returns_empty_meta():
    meta, body = parse("just a body, no frontmatter")
    assert meta == {}
    assert body == "just a body, no frontmatter"
