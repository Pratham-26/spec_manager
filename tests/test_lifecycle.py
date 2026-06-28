import pytest

from spec_manager.lifecycle import (
    STATUSES,
    InvalidTransition,
    can_transition,
    is_valid_status,
    transition,
)


def test_recognizes_all_lifecycle_states():
    assert set(STATUSES) == {
        "draft", "in_review", "approved", "planned", "implemented",
        "deprecated", "superseded",
    }


def test_forward_progression_is_allowed():
    assert can_transition("draft", "in_review")
    assert can_transition("in_review", "approved")
    assert can_transition("approved", "planned")
    assert can_transition("planned", "implemented")


def test_review_can_revert_to_draft():
    assert can_transition("in_review", "draft")


def test_any_nonterminal_state_can_be_deprecated():
    for s in ["draft", "in_review", "approved", "planned", "implemented"]:
        assert can_transition(s, "deprecated")


def test_any_nonterminal_state_can_be_superseded():
    for s in ["draft", "approved", "implemented"]:
        assert can_transition(s, "superseded")


def test_invalid_jumps_are_rejected():
    assert not can_transition("draft", "implemented")
    assert not can_transition("approved", "in_review")
    assert not can_transition("implemented", "approved")


def test_terminal_states_cannot_transition():
    assert not can_transition("deprecated", "draft")
    assert not can_transition("deprecated", "approved")
    assert not can_transition("superseded", "implemented")


def test_transition_returns_target_on_success():
    assert transition("draft", "in_review") == "in_review"


def test_transition_raises_on_invalid():
    with pytest.raises(InvalidTransition):
        transition("draft", "implemented")


def test_unknown_status_is_invalid():
    assert not is_valid_status("bogus")
    assert is_valid_status("draft")
