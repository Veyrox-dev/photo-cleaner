from __future__ import annotations

from pathlib import Path

from photo_cleaner.ui.workflows.export_delete_workflow_controller import ExportDeleteWorkflowController


def test_build_export_decision_without_output_path_returns_warning() -> None:
    controller = ExportDeleteWorkflowController()

    decision = controller.build_export_decision(None, 3, 1, 1024, lambda key: key)

    assert decision.can_continue is False
    assert decision.level == "warning"
    assert decision.title == "Kein Ausgabeordner"


def test_build_export_decision_without_keep_returns_info() -> None:
    controller = ExportDeleteWorkflowController()

    decision = controller.build_export_decision(Path("C:/out"), 0, 1, 1024, lambda key: key)

    assert decision.can_continue is False
    assert decision.level == "info"
    assert decision.title == "no_selection_msg"


def test_build_export_decision_with_valid_input_returns_question() -> None:
    controller = ExportDeleteWorkflowController()

    decision = controller.build_export_decision(Path("C:/out"), 4, 3, 5 * 1024 * 1024, lambda key: key)

    assert decision.can_continue is True
    assert decision.level == "question"
    assert decision.title == "Export & Bereinigung abschließen"
    assert "4 Bild(er)" in decision.message
    assert "Du sparst damit aktuell 5.0 MB." in decision.message
    assert "nicht physisch gelöscht" in decision.message
    assert str(Path("C:/out")) in decision.message


def test_build_export_result_message_for_partial_failures_is_warning() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_export_result_message(
        success_count=2,
        failure_count=1,
        errors=["a", "b"],
        archive_path=Path("C:/out/export.zip"),
        cancelled=False,
    )

    assert message.level == "warning"
    assert message.title == "Export Teilweise Fehlgeschlagen"
    assert "Fehler: 1" in message.message


def test_build_export_result_message_cancelled_returns_info() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_export_result_message(
        success_count=1,
        failure_count=0,
        errors=[],
        archive_path=Path("C:/out/export.zip"),
        cancelled=True,
    )

    assert message.level == "info"
    assert message.title == "Export abgebrochen"
    assert "abgebrochen" in message.message


def test_build_export_result_message_includes_reclaimable_size_summary() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_export_result_message(
        success_count=5,
        failure_count=0,
        errors=[],
        archive_path=Path("C:/out/export.zip"),
        cancelled=False,
        delete_applied_count=3,
        reclaimable_bytes=5 * 1024 * 1024,
        skipped_locked_count=1,
    )

    assert message.level == "info"
    assert "3 Bild(er) aus aktiver Sitzung entfernt." in message.message
    assert "Du hast aktuell 5.0 MB eingespart." in message.message
    assert "Übersprungen (gesperrt): 1." in message.message


def test_build_export_result_message_limits_error_preview_to_five() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_export_result_message(
        success_count=3,
        failure_count=7,
        errors=["e1", "e2", "e3", "e4", "e5", "e6", "e7"],
        archive_path=Path("C:/out/export.zip"),
        cancelled=False,
    )

    assert message.level == "warning"
    assert "e1" in message.message
    assert "e5" in message.message
    assert "<div>e6</div>" not in message.message
    assert "... und 2 weitere" in message.message


def test_build_delete_decision_without_marked_paths_returns_info() -> None:
    controller = ExportDeleteWorkflowController()

    decision = controller.build_delete_decision(0, 0, lambda key: key)

    assert decision.can_continue is False
    assert decision.level == "info"
    assert decision.title == "no_deletions"


def test_build_delete_decision_with_marked_paths_returns_question() -> None:
    controller = ExportDeleteWorkflowController()

    decision = controller.build_delete_decision(5, 8 * 1024 * 1024, lambda key: key)

    assert decision.can_continue is True
    assert decision.level == "question"
    assert decision.title == "Bereinigung bestätigen"
    assert "5 Bild(er)" in decision.message
    assert "Du sparst damit aktuell 8.0 MB." in decision.message
    assert "nicht physisch gelöscht" in decision.message


def test_build_delete_result_message_ok_with_locked_files() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_delete_result_message(
        {"ok": True, "deleted_ids": [1, 2], "skipped_locked": [3]},
        lambda key: key,
        reclaimable_bytes=3 * 1024 * 1024,
    )

    assert message.level == "info"
    assert message.title == "delete_completed"
    assert "2 Bild(er) aus aktiver Sitzung entfernt" in message.message
    assert "Potenziell freigebbarer Speicher: 3.0 MB." in message.message
    assert "1 Datei(en) wurden übersprungen" in message.message


def test_build_delete_result_message_failure_is_warning() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_delete_result_message(
        {"ok": False, "message": "boom"},
        lambda key: key,
    )

    assert message.level == "warning"
    assert message.title == "Löschen fehlgeschlagen"
    assert message.message == "boom"


def test_build_delete_result_message_failure_uses_default_when_missing_message() -> None:
    controller = ExportDeleteWorkflowController()

    message = controller.build_delete_result_message(
        {"ok": False},
        lambda key: key,
    )

    assert message.level == "warning"
    assert message.title == "Löschen fehlgeschlagen"
    assert message.message == "Unbekannter Fehler"
