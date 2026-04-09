from __future__ import annotations

ONBOARDING_COMPLETED_KEY = "first_run_onboarding_completed"


def should_show_onboarding(settings: dict) -> bool:
    """Return True when onboarding should be shown for current user settings."""
    return not bool(settings.get(ONBOARDING_COMPLETED_KEY, False))


def mark_onboarding_completed(settings: dict) -> dict:
    """Persist onboarding completion in the provided settings mapping."""
    settings[ONBOARDING_COMPLETED_KEY] = True
    return settings


def reset_onboarding_completed(settings: dict) -> dict:
    """Clear onboarding completion state so onboarding can be shown again."""
    settings.pop(ONBOARDING_COMPLETED_KEY, None)
    return settings
