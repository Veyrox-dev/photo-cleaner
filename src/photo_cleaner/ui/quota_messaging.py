from __future__ import annotations

from typing import Callable


def build_quota_limit_message(requested_count: int, reason: str | None, t_func: Callable[[str], str]) -> str:
    """Build a clear, actionable quota limit message for the pipeline start flow."""
    resolved_reason = reason or t_func("quota_limit_default_reason")
    return t_func("quota_limit_message").format(
        requested=requested_count,
        reason=resolved_reason,
        action=t_func("quota_limit_action"),
    )
