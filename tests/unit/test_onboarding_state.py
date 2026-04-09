from __future__ import annotations

from photo_cleaner.ui.onboarding_state import (
    ONBOARDING_COMPLETED_KEY,
    mark_onboarding_completed,
    reset_onboarding_completed,
    should_show_onboarding,
)


def test_should_show_onboarding_when_not_completed() -> None:
    settings: dict = {}

    assert should_show_onboarding(settings) is True


def test_should_not_show_onboarding_when_completed() -> None:
    settings = {ONBOARDING_COMPLETED_KEY: True}

    assert should_show_onboarding(settings) is False


def test_mark_onboarding_completed_sets_flag() -> None:
    settings: dict = {}

    updated = mark_onboarding_completed(settings)

    assert updated is settings
    assert settings[ONBOARDING_COMPLETED_KEY] is True


def test_reset_onboarding_completed_removes_flag() -> None:
    settings = {ONBOARDING_COMPLETED_KEY: True, "other": 123}

    updated = reset_onboarding_completed(settings)

    assert updated is settings
    assert ONBOARDING_COMPLETED_KEY not in settings
    assert settings["other"] == 123
