from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class DialogDecision:
    can_continue: bool
    level: str  # info | warning | question
    title: str
    message: str


@dataclass(frozen=True)
class DialogMessage:
    level: str  # info | warning
    title: str
    message: str


class ExportDeleteWorkflowController:
    """Controller for export/delete dialog decision and summary messages."""

    def build_export_decision(
        self,
        output_path: Path | None,
        keep_count: int,
        t_func: Callable[[str], str],
    ) -> DialogDecision:
        """Build pre-check result and confirmation text for export flow."""
        if not output_path:
            return DialogDecision(
                can_continue=False,
                level="warning",
                title="Kein Ausgabeordner",
                message="Kein Ausgabeordner festgelegt. Export nicht möglich.",
            )

        if keep_count == 0:
            return DialogDecision(
                can_continue=False,
                level="info",
                title=t_func("no_selection_msg"),
                message="Keine Bilder als BEHALTEN markiert.",
            )

        return DialogDecision(
            can_continue=True,
            level="question",
            title="Finalisieren?",
            message=(
                f"{keep_count} Bild(er) als BEHALTEN markiert.\\n\\n"
                f"Exportieren nach:\\n{output_path}\\n\\nFortfahren?"
            ),
        )

    def build_export_result_message(
        self,
        success_count: int,
        failure_count: int,
        errors: Sequence[str],
        archive_path: Path,
        cancelled: bool,
    ) -> DialogMessage:
        """Build final export result message for info/warning dialogs."""
        if cancelled:
            return DialogMessage(
                level="info",
                title="Export abgebrochen",
                message="Der Export wurde abgebrochen. Teilresultate können im ZIP liegen.",
            )

        if failure_count == 0:
            return DialogMessage(
                level="info",
                title="Export Erfolgreich",
                message=f"{success_count} Bild(er) exportiert als ZIP:\\n{archive_path}",
            )

        error_text = "\\n".join(errors[:5])
        if len(errors) > 5:
            error_text += f"\\n... und {len(errors) - 5} weitere"

        return DialogMessage(
            level="warning",
            title="Export Teilweise Fehlgeschlagen",
            message=(
                f"✓ {success_count} erfolgreich\\n"
                f"✗ {failure_count} Fehler\\n\\n"
                f"{error_text}\\n\\nZIP: {archive_path}"
            ),
        )

    def build_delete_decision(self, delete_count: int, t_func: Callable[[str], str]) -> DialogDecision:
        """Build pre-check result and confirmation text for delete flow."""
        if delete_count == 0:
            return DialogDecision(
                can_continue=False,
                level="info",
                title=t_func("no_deletions"),
                message="Keine Bilder sind zum Löschen markiert.",
            )

        return DialogDecision(
            can_continue=True,
            level="question",
            title="Löschen bestätigen",
            message=f"{delete_count} Bild(er) sind als LÖSCHEN markiert.\\n\\nJetzt löschen?",
        )

    def build_delete_result_message(self, result: dict, t_func: Callable[[str], str]) -> DialogMessage:
        """Build delete result message based on batch delete action result."""
        if not result.get("ok"):
            return DialogMessage(
                level="warning",
                title="Löschen fehlgeschlagen",
                message=result.get("message", "Unbekannter Fehler"),
            )

        deleted_ids = result.get("deleted_ids", [])
        skipped_locked = result.get("skipped_locked", [])

        message = f"{len(deleted_ids)} Bild(er) gelöscht."
        if skipped_locked:
            message += f"\\n{len(skipped_locked)} Datei(en) wurden übersprungen (gesperrt)."

        return DialogMessage(
            level="info",
            title=t_func("delete_completed"),
            message=message,
        )
