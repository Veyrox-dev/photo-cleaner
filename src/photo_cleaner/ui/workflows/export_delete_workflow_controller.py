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

    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        """Return a compact human-readable byte string."""
        size = max(0, int(num_bytes or 0))
        units = ("B", "KB", "MB", "GB", "TB")
        value = float(size)
        unit = units[0]
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                break
            value /= 1024.0
        if unit == "B":
            return f"{int(value)} {unit}"
        return f"{value:.1f} {unit}"

    @staticmethod
    def _html_escape(value: str) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _summary_block(self, title: str, lines: Sequence[str]) -> str:
        entries = "".join(f"<div>{self._html_escape(line)}</div>" for line in lines)
        return (
            "<div style='margin:10px 0 0 0; padding:10px 12px; "
            "border:1px solid #d8dde6; border-radius:10px; background:#f6f8fb;'>"
            f"<div style='font-weight:700; margin-bottom:6px;'>{self._html_escape(title)}</div>"
            f"{entries}</div>"
        )

    def build_export_decision(
        self,
        output_path: Path | None,
        keep_count: int,
        delete_count: int,
        reclaimable_bytes: int,
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

        export_lines = [
            f"{keep_count} Bild(er) werden ins ZIP übernommen.",
            f"Zielordner: {output_path}",
        ]
        cleanup_lines = [
            f"{delete_count} Bild(er) werden aus der aktiven Sitzung entfernt.",
            f"Du sparst damit aktuell {self._format_bytes(reclaimable_bytes)}.",
            "Die Originaldateien werden dabei nicht physisch gelöscht.",
        ]

        return DialogDecision(
            can_continue=True,
            level="question",
            title="Export & Bereinigung abschließen",
            message=(
                "<div style='min-width:420px;'>"
                "<div style='font-size:16px; font-weight:700; margin-bottom:8px;'>"
                "Bereit zum Abschließen"
                "</div>"
                "<div style='margin-bottom:8px;'>"
                "Beim Fortfahren wird ein ZIP-Archiv erstellt und die aktuelle Bereinigung angewendet."
                "</div>"
                f"{self._summary_block('Export', export_lines)}"
                f"{self._summary_block('Bereinigung', cleanup_lines)}"
                "<div style='margin-top:12px; font-weight:600;'>Jetzt exportieren und bereinigen?</div>"
                "</div>"
            ),
        )

    def build_export_result_message(
        self,
        success_count: int,
        failure_count: int,
        errors: Sequence[str],
        archive_path: Path,
        cancelled: bool,
        delete_applied_count: int = 0,
        reclaimable_bytes: int = 0,
        skipped_locked_count: int = 0,
        delete_failed_message: str | None = None,
    ) -> DialogMessage:
        """Build final export result message for info/warning dialogs."""
        if cancelled:
            return DialogMessage(
                level="info",
                title="Export abgebrochen",
                message="Der Export wurde abgebrochen. Teilresultate können im ZIP liegen.",
            )

        cleanup_lines = [
            f"{delete_applied_count} Bild(er) aus aktiver Sitzung entfernt.",
            f"Du hast aktuell {self._format_bytes(reclaimable_bytes)} eingespart.",
            (
                f"Übersprungen (gesperrt): {skipped_locked_count}."
                if skipped_locked_count
                else "Keine gesperrten Dateien übersprungen."
            ),
        ]

        if failure_count == 0:
            blocks = [
                self._summary_block(
                    "Export",
                    [
                        f"{success_count} Bild(er) wurden als ZIP exportiert.",
                        f"Archiv: {archive_path}",
                    ],
                )
            ]
            if delete_applied_count or skipped_locked_count or reclaimable_bytes:
                blocks.append(self._summary_block("Bereinigungsergebnis", cleanup_lines))
                blocks.append(
                    self._summary_block(
                        "Hinweis",
                        ["Die Dateien wurden in der App bereinigt, aber nicht physisch gelöscht."],
                    )
                )
            if delete_failed_message:
                blocks.append(self._summary_block("Problem beim Entfernen", [delete_failed_message]))
            return DialogMessage(
                level="info",
                title="Export abgeschlossen",
                message=(
                    "<div style='min-width:420px;'>"
                    "<div style='font-size:16px; font-weight:700; margin-bottom:8px;'>"
                    "Export erfolgreich abgeschlossen"
                    "</div>"
                    f"{''.join(blocks)}"
                    "</div>"
                ),
            )

        error_lines = list(errors[:5])
        if len(errors) > 5:
            error_lines.append(f"... und {len(errors) - 5} weitere")

        blocks = [
            self._summary_block(
                "Status",
                [
                    f"Erfolgreich exportiert: {success_count}",
                    f"Fehler: {failure_count}",
                    f"ZIP: {archive_path}",
                ],
            ),
            self._summary_block("Fehlerdetails", error_lines),
        ]
        if delete_applied_count or skipped_locked_count or reclaimable_bytes:
            blocks.append(self._summary_block("Bereinigung", cleanup_lines))
        if delete_failed_message:
            blocks.append(self._summary_block("Problem beim Entfernen", [delete_failed_message]))

        return DialogMessage(
            level="warning",
            title="Export Teilweise Fehlgeschlagen",
            message=(
                "<div style='min-width:420px;'>"
                "<div style='font-size:16px; font-weight:700; margin-bottom:8px;'>"
                "Export teilweise abgeschlossen"
                "</div>"
                f"{''.join(blocks)}"
                "</div>"
            ),
        )

    def build_delete_decision(
        self,
        delete_count: int,
        reclaimable_bytes: int,
        t_func: Callable[[str], str],
    ) -> DialogDecision:
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
            title="Bereinigung bestätigen",
            message=(
                "<div style='min-width:420px;'>"
                "<div style='font-size:16px; font-weight:700; margin-bottom:8px;'>"
                "Bereinigung anwenden"
                "</div>"
                f"{self._summary_block('Auswahl', [f'{delete_count} Bild(er) werden aus der aktiven Sitzung entfernt.', f'Du sparst damit aktuell {self._format_bytes(reclaimable_bytes)}.'])}"
                f"{self._summary_block('Hinweis', ['Die Dateien werden nicht physisch gelöscht.', 'Die Bereinigung wirkt nur auf den aktiven Review-Stand.'])}"
                "<div style='margin-top:12px; font-weight:600;'>Jetzt bereinigen?</div>"
                "</div>"
            ),
        )

    def build_delete_result_message(
        self,
        result: dict,
        t_func: Callable[[str], str],
        reclaimable_bytes: int = 0,
    ) -> DialogMessage:
        """Build delete result message based on batch delete action result."""
        if not result.get("ok"):
            return DialogMessage(
                level="warning",
                title="Löschen fehlgeschlagen",
                message=result.get("message", "Unbekannter Fehler"),
            )

        deleted_ids = result.get("deleted_ids", [])
        skipped_locked = result.get("skipped_locked", [])

        lines = [
            f"{len(deleted_ids)} Bild(er) aus aktiver Sitzung entfernt.",
            f"Potenziell freigebbarer Speicher: {self._format_bytes(reclaimable_bytes)}.",
        ]
        if skipped_locked:
            lines.append(f"{len(skipped_locked)} Datei(en) wurden übersprungen (gesperrt).")

        return DialogMessage(
            level="info",
            title=t_func("delete_completed"),
            message=(
                "<div style='min-width:420px;'>"
                "<div style='font-size:16px; font-weight:700; margin-bottom:8px;'>"
                "Bereinigung abgeschlossen"
                "</div>"
                f"{self._summary_block('Ergebnis', lines)}"
                "</div>"
            ),
        )
