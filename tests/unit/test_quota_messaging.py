from __future__ import annotations

from photo_cleaner.ui.quota_messaging import build_quota_limit_message


def _t(key: str) -> str:
    mapping = {
        "quota_limit_default_reason": "default-reason",
        "quota_limit_action": "open-license",
        "quota_limit_message": "req={requested}; reason={reason}; action={action}",
    }
    return mapping[key]


def test_build_quota_limit_message_with_reason() -> None:
    msg = build_quota_limit_message(42, "limit-hit", _t)

    assert "req=42" in msg
    assert "reason=limit-hit" in msg
    assert "action=open-license" in msg


def test_build_quota_limit_message_with_default_reason() -> None:
    msg = build_quota_limit_message(5, None, _t)

    assert "req=5" in msg
    assert "reason=default-reason" in msg
