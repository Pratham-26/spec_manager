from spec_manager.diff import change_ratio


def test_identical_bodies_have_zero_change():
    body = "# Auth\n\nWe use OAuth2 with PKCE for all clients."
    assert change_ratio(body, body) == 0.0


def test_trivial_typo_is_below_threshold():
    old = "# Auth\n\nWe use OAuth2 with PKCE for all clients."
    new = "# Auth\n\nWe use OAuth2 with PKCE for all clients!"  # one char
    assert change_ratio(old, new) < 0.10


def test_large_rewrite_exceeds_threshold():
    old = "# Auth\n\nWe use OAuth2 with PKCE for all clients."
    new = "Billing runs nightly via a background worker and emails receipts."
    assert change_ratio(old, new) > 0.10
