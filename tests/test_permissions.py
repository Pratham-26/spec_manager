from spec_manager.permissions import can_write


def test_same_project_write_always_allowed():
    assert can_write(owner_project="app", current_project="app", cross_project_writable=False)


def test_cross_project_write_allowed_when_flag_set():
    assert can_write(owner_project="app", current_project="other", cross_project_writable=True)


def test_cross_project_write_denied_without_flag():
    assert not can_write(
        owner_project="app", current_project="other", cross_project_writable=False
    )
