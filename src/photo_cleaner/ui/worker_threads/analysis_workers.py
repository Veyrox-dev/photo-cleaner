from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from photo_cleaner.db.schema import Database
from photo_cleaner.i18n import t
from photo_cleaner.repositories.file_repository import FileRepository

logger = logging.getLogger(__name__)

_QualityAnalyzer = None
_GroupScorer = None
_analyzer_lock = threading.Lock()
_scorer_lock = threading.Lock()


def _get_quality_analyzer():
    """Lazy load QualityAnalyzer to avoid expensive startup costs."""
    global _QualityAnalyzer
    with _analyzer_lock:
        if _QualityAnalyzer is None:
            from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer

            _QualityAnalyzer = QualityAnalyzer
    return _QualityAnalyzer


def _get_group_scorer():
    """Lazy load GroupScorer to avoid expensive startup costs."""
    global _GroupScorer
    with _scorer_lock:
        if _GroupScorer is None:
            from photo_cleaner.pipeline.scorer import GroupScorer

            _GroupScorer = GroupScorer
    return _GroupScorer


def _compute_analysis_workers(image_count: int) -> int:
    """Pick a conservative worker count for stage-4 quality analysis."""
    if image_count <= 1:
        return 1
    cpu_total = os.cpu_count() or 4
    cpu_budget = max(1, cpu_total - 1)
    if image_count <= 3:
        return min(cpu_budget, image_count)
    if image_count <= 8:
        return min(cpu_budget, 4, image_count)
    return min(cpu_budget, 8, image_count)


class RatingWorkerThread(QThread):
    """Worker thread for auto-rating operation."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, db_path: Path, top_n: int, mtcnn_status: dict | None = None):
        super().__init__()
        self.db_path = db_path
        self.top_n = top_n
        self.mtcnn_status = mtcnn_status or {"available": True, "error": None}
        self._should_cancel = False
        self._progress_emit_interval_sec = 0.08

    def run(self):
        from photo_cleaner.pipeline.parallel_quality_analyzer import ParallelQualityAnalyzer

        logger.info("[WORKER] RatingWorkerThread.run() STARTED")
        start_time = time.monotonic()
        info = {"rated": False, "warn": False}

        if self.mtcnn_status.get("available", False):
            logger.info("[WORKER] MTCNN available - will use face detection for rating")
        else:
            error_msg = self.mtcnn_status.get("error", "MTCNN not available")
            if error_msg:
                logger.warning("[WORKER] MTCNN not available (%s) - will use Haar Cascade fallback", error_msg)
                logger.warning("[WORKER] Rating will continue with lower accuracy")
            else:
                logger.info("[WORKER] MTCNN status unknown - continuing with runtime auto-detection")

        db = None
        conn = None
        try:
            logger.info("[WORKER] Connecting to database...")
            db = Database(self.db_path)
            conn = db.connect()
            files = FileRepository(conn)

            logger.info("[WORKER] Querying groups from database...")
            cur = conn.execute(
                """
                SELECT d.group_id, f.path
                FROM duplicates d
                JOIN files f ON f.file_id = d.file_id
                WHERE f.is_deleted = 0
                ORDER BY d.group_id, f.path
                """
            )
            groups: dict[str, list[Path]] = {}
            for row in cur.fetchall():
                groups.setdefault(row["group_id"], []).append(Path(row[1]))

            logger.info("[WORKER] Found %s groups to rate", len(groups))
            if not groups:
                logger.info("[WORKER] No duplicate groups found; skipping rating step")
                self.finished.emit(info)
                return

            total_images = sum(len(v) for v in groups.values())
            logger.info("[WORKER] Total images to analyze: %s", total_images)

            last_progress_emit_ts = 0.0
            last_progress_signature: tuple[int, str] | None = None

            def _emit_progress(pct: int, status: str, force: bool = False) -> None:
                nonlocal last_progress_emit_ts, last_progress_signature
                clamped_pct = max(0, min(100, int(pct)))
                signature = (clamped_pct, status)
                now = time.monotonic()
                if not force:
                    if signature == last_progress_signature:
                        return
                    if now - last_progress_emit_ts < self._progress_emit_interval_sec:
                        return
                self.progress.emit(clamped_pct, status)
                last_progress_emit_ts = now
                last_progress_signature = signature

            logger.info("[WORKER] Thread alive after %.2fs [DB query complete]", time.monotonic() - start_time)
            _emit_progress(87, f"Modelle werden geladen... 0/{total_images}", force=True)

            logger.info("[WORKER] Initializing QualityAnalyzer (use_face_mesh=True)...")
            init_start = time.monotonic()
            QualityAnalyzer = _get_quality_analyzer()
            analyzer = QualityAnalyzer(use_face_mesh=True)
            parallel_analyzer = ParallelQualityAnalyzer(analyzer)
            logger.info("[WORKER] QualityAnalyzer initialized in %.2fs", time.monotonic() - init_start)

            _emit_progress(88, f"QualityAnalyzer bereit, lade GroupScorer... 0/{total_images}", force=True)

            logger.info("[WORKER] Initializing GroupScorer (top_n=%s)...", self.top_n)
            scorer_start = time.monotonic()
            GroupScorer = _get_group_scorer()
            scorer = GroupScorer(top_n=self.top_n)
            logger.info("[WORKER] GroupScorer initialized in %.2fs", time.monotonic() - scorer_start)

            quality_results: dict[str, list] = {}
            done = 0
            total_scored_images = 0

            logger.info("[WORKER] Models ready after %.2fs total, starting warmup and analysis...", time.monotonic() - start_time)
            _emit_progress(90, f"Modelle aufwärmen... 0/{total_images}", force=True)

            analyzer.warmup()
            logger.info("[WORKER] Warmup complete, beginning batch analysis")
            _emit_progress(87, f"Bilder werden bewertet... {done}/{total_images}", force=True)

            for group_id, paths in groups.items():
                if self._should_cancel:
                    logger.info("Rating cancelled by user")
                    self.finished.emit(info)
                    return

                pct = 87 + int(7 * (done / max(1, total_images)))
                _emit_progress(min(94, pct), f"Bilder werden bewertet... {done}/{total_images}")

                group_base_done = done
                last_reported_local_done = 0
                worker_count = _compute_analysis_workers(len(paths))

                def _progress_cb(local_done: int, local_total: int) -> None:
                    nonlocal last_reported_local_done
                    if self._should_cancel:
                        return
                    current_done = group_base_done + local_done
                    pct_inner = 87 + int(7 * (current_done / max(1, total_images)))
                    _emit_progress(min(94, pct_inner), f"Bilder werden bewertet... {current_done}/{total_images}")

                    capped_local_done = max(0, min(local_done, len(paths)))
                    if capped_local_done <= last_reported_local_done:
                        return
                    for image_idx in range(last_reported_local_done + 1, capped_local_done + 1):
                        global_idx = group_base_done + image_idx
                        image_name = paths[image_idx - 1].name
                        _emit_progress(min(94, pct_inner), f"Bild bewertet {global_idx}/{total_images}: {image_name}", force=True)
                    last_reported_local_done = capped_local_done

                use_process_parallel = os.getenv("PHOTOCLEANER_USE_PROCESS_PARALLEL", "1").lower() in ("1", "true", "yes")
                if use_process_parallel and worker_count > 1:
                    results = parallel_analyzer.analyze_batch_parallel(
                        paths,
                        max_workers=worker_count,
                        batch_size=1,
                        progress_callback=_progress_cb,
                    )
                else:
                    results = analyzer.analyze_batch(
                        paths,
                        progress_callback=_progress_cb,
                        max_workers=worker_count,
                    )
                quality_results[group_id] = results
                done += len(paths)

                pct = 87 + int(7 * (done / max(1, total_images)))
                _emit_progress(min(94, pct), f"Bilder werden bewertet... {done}/{total_images}", force=(done >= total_images))

            total_scored_images = sum(len(group_results) for group_results in quality_results.values())

            if self._should_cancel:
                logger.info("Rating cancelled by user")
                self.finished.emit(info)
                return

            logger.info("Scoring all groups...")
            group_scores = scorer.score_multiple_groups(quality_results)
            logger.info("Applying scores to database (action_id=AUTO_RATING)...")
            scorer.apply_scores_to_db(group_scores, files, action_id="AUTO_RATING")
            logger.info("Scores applied successfully")

            logger.info("Applying auto-selection for each group...")
            scored_done = 0
            for group_id, results in quality_results.items():
                if self._should_cancel:
                    break

                best_path, second_path, all_scores = scorer.auto_select_best_image(group_id, results)
                try:
                    conn.execute(
                        """
                        UPDATE files
                        SET is_recommended = 0, keeper_source = 'undecided', quality_score = NULL,
                            sharpness_component = NULL, lighting_component = NULL,
                            resolution_component = NULL, face_quality_component = NULL
                        WHERE file_id IN (
                            SELECT file_id FROM duplicates WHERE group_id = ?
                        )
                        """,
                        (group_id,),
                    )

                    score_updates_with_components: list[tuple[float, float, float, float, float, str]] = []
                    score_updates_basic: list[tuple[float, str]] = []
                    for item in all_scores:
                        if len(item) == 4:
                            path, score, disqualified, components = item
                            score_updates_with_components.append(
                                (
                                    score,
                                    components.sharpness_score,
                                    components.lighting_score,
                                    components.resolution_score,
                                    components.face_quality_score,
                                    str(path),
                                )
                            )
                        else:
                            path, score, disqualified = item
                            score_updates_basic.append((score, str(path)))

                        scored_done += 1
                        score_value = float(score)
                        score_display = f"{score_value:.1f}" if score_value > 1.0 else f"{score_value * 100:.0f}%"
                        if best_path and path == best_path:
                            decision = "EMPFOHLEN"
                        elif second_path and path == second_path:
                            decision = "ZWEITWAHL"
                        elif len(item) == 4 and components.duplicate_class == "A":
                            decision = "KLASSE A (DUPLIKAT-LOESCHEN)"
                        elif disqualified:
                            decision = "AUSSORTIERT"
                        else:
                            decision = "BEWERTET"

                        score_pct = 94 + int(round((scored_done / max(1, total_scored_images)) * 5))
                        _emit_progress(
                            min(99, score_pct),
                            f"Ergebnis {scored_done}/{max(1, total_scored_images)}: {Path(path).name} -> {decision} ({score_display})",
                            force=True,
                        )

                    if score_updates_with_components:
                        conn.executemany(
                            """
                            UPDATE files
                            SET quality_score = ?,
                                sharpness_component = ?,
                                lighting_component = ?,
                                resolution_component = ?,
                                face_quality_component = ?
                            WHERE path = ?
                            """,
                            score_updates_with_components,
                        )
                    if score_updates_basic:
                        conn.executemany(
                            """
                            UPDATE files
                            SET quality_score = ?
                            WHERE path = ?
                            """,
                            score_updates_basic,
                        )

                    if best_path:
                        conn.execute(
                            """
                            UPDATE files
                            SET is_recommended = 1, keeper_source = 'auto'
                            WHERE path = ?
                            """,
                            (str(best_path),),
                        )
                        logger.info("%s als Empfehlung markiert", best_path.name)

                    if second_path:
                        conn.execute(
                            """
                            UPDATE files
                            SET keeper_source = 'auto_secondary'
                            WHERE path = ?
                            """,
                            (str(second_path),),
                        )
                        logger.info("%s als Zweitwahl markiert", second_path.name)

                    conn.commit()
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                    logger.error("Fehler beim Markieren der Empfehlungen für %s: %s", group_id, e, exc_info=True)
                    info["warn"] = True

            logger.info("[WORKER] RatingWorkerThread COMPLETED - rated=%s, warn=%s", info["rated"], info["warn"])
            info["rated"] = True
            self.finished.emit(info)

        except Exception as e:
            logger.error("[WORKER] RatingWorkerThread FAILED with unexpected error: %s: %s", type(e).__name__, e, exc_info=True)
            info["warn"] = True
            self.error.emit(f"{type(e).__name__}: {str(e)}")
            self.finished.emit(info)
        finally:
            logger.info("[WORKER] RatingWorkerThread cleanup")
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning("Error closing connection: %s", e)
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.warning("Error closing database: %s", e)

    def cancel(self):
        """Cancel the rating operation."""
        self._should_cancel = True


class MergeGroupRatingWorker(QThread):
    """Background worker for re-rating a newly merged group."""

    progress = Signal(int, int, str, str, int, int)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, db_path: Path, group_id: str, top_n: int):
        super().__init__()
        self.db_path = db_path
        self.group_id = group_id
        self.top_n = top_n
        self._cancelled = False
        self._progress_emit_interval_sec = 0.08

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        from photo_cleaner.pipeline.parallel_quality_analyzer import ParallelQualityAnalyzer

        db = None
        conn = None
        try:
            last_progress_emit_ts = 0.0
            last_progress_signature: tuple[int, int, str, str, int, int] | None = None

            def _emit_progress(
                pct: int,
                step: int,
                phase_label: str,
                detail_label: str,
                current: int,
                total: int,
                force: bool = False,
            ) -> None:
                nonlocal last_progress_emit_ts, last_progress_signature
                clamped_pct = max(0, min(100, int(pct)))
                signature = (clamped_pct, step, phase_label, detail_label, int(current), int(total))
                now = time.monotonic()
                if not force:
                    if signature == last_progress_signature:
                        return
                    if now - last_progress_emit_ts < self._progress_emit_interval_sec:
                        return
                self.progress.emit(clamped_pct, step, phase_label, detail_label, int(current), int(total))
                last_progress_emit_ts = now
                last_progress_signature = signature

            _emit_progress(5, 1, t("merge_progress_phase_prepare"), t("merge_progress_detail_prepare"), 0, 0, force=True)

            db = Database(self.db_path)
            conn = db.connect()
            files = FileRepository(conn)

            cur = conn.execute(
                """
                SELECT f.path
                FROM duplicates d
                JOIN files f ON f.file_id = d.file_id
                WHERE d.group_id = ? AND f.is_deleted = 0
                ORDER BY f.path
                """,
                (self.group_id,),
            )
            paths = [Path(row["path"]) for row in cur.fetchall()]
            if not paths:
                self.finished.emit(False)
                return

            total_images = len(paths)
            worker_count = _compute_analysis_workers(total_images)
            _emit_progress(
                15,
                1,
                t("merge_progress_phase_prepare"),
                t("merge_progress_detail_found_images").format(count=total_images),
                total_images,
                total_images,
                force=True,
            )

            if self._cancelled:
                self.finished.emit(False)
                return

            _emit_progress(30, 2, t("merge_progress_phase_models"), t("merge_progress_detail_models"), 0, 0, force=True)
            QualityAnalyzer = _get_quality_analyzer()
            GroupScorer = _get_group_scorer()
            analyzer = QualityAnalyzer(use_face_mesh=True)
            parallel_analyzer = ParallelQualityAnalyzer(analyzer)
            scorer = GroupScorer(top_n=self.top_n)

            _emit_progress(
                40,
                3,
                t("merge_progress_phase_compare"),
                t("merge_progress_detail_compare_count").format(current=0, total=total_images),
                0,
                total_images,
                force=True,
            )

            def _progress_cb(local_done: int, local_total: int) -> None:
                if self._cancelled:
                    return
                if local_total <= 0:
                    pct = 40
                else:
                    pct = 40 + int(round((local_done / local_total) * 30))
                total_local = max(local_total, total_images)
                _emit_progress(
                    min(70, max(40, pct)),
                    3,
                    t("merge_progress_phase_compare"),
                    t("merge_progress_detail_compare_count").format(current=local_done, total=total_local),
                    max(0, local_done),
                    max(1, total_local),
                )

            use_process_parallel = os.getenv("PHOTOCLEANER_USE_PROCESS_PARALLEL", "1").lower() in ("1", "true", "yes")
            if use_process_parallel and worker_count > 1:
                results = parallel_analyzer.analyze_batch_parallel(
                    paths,
                    max_workers=worker_count,
                    batch_size=1,
                    progress_callback=_progress_cb,
                )
            else:
                results = analyzer.analyze_batch(
                    paths,
                    progress_callback=_progress_cb,
                    max_workers=worker_count,
                )
            if self._cancelled:
                self.finished.emit(False)
                return

            _emit_progress(75, 4, t("merge_progress_phase_scoring"), t("merge_progress_detail_scoring_count").format(current=0, total=0), 0, 0, force=True)
            group_scores = scorer.score_multiple_groups({self.group_id: results})
            scorer.apply_scores_to_db(group_scores, files, action_id="AUTO_RATING_MERGE")

            best_path, second_path, all_scores = scorer.auto_select_best_image(self.group_id, results)
            total_scores = len(all_scores)

            conn.execute(
                """
                UPDATE files
                SET is_recommended = 0, keeper_source = 'undecided', quality_score = NULL,
                    sharpness_component = NULL, lighting_component = NULL,
                    resolution_component = NULL, face_quality_component = NULL
                WHERE file_id IN (
                    SELECT file_id FROM duplicates WHERE group_id = ?
                )
                """,
                (self.group_id,),
            )

            score_updates_with_components: list[tuple[float, float, float, float, float, str]] = []
            score_updates_basic: list[tuple[float, str]] = []
            for idx, item in enumerate(all_scores, start=1):
                if self._cancelled:
                    self.finished.emit(False)
                    return
                if len(item) == 4:
                    path, score, _, components = item
                    score_updates_with_components.append(
                        (
                            score,
                            components.sharpness_score,
                            components.lighting_score,
                            components.resolution_score,
                            components.face_quality_score,
                            str(path),
                        )
                    )
                else:
                    path, score, _ = item
                    score_updates_basic.append((score, str(path)))

                if total_scores > 0 and (idx == total_scores or idx == 1 or idx % 5 == 0):
                    pct = 75 + int(round((idx / total_scores) * 21))
                    _emit_progress(
                        min(96, max(75, pct)),
                        4,
                        t("merge_progress_phase_scoring"),
                        t("merge_progress_detail_scoring_count").format(current=idx, total=total_scores),
                        idx,
                        total_scores,
                    )

            if score_updates_with_components:
                conn.executemany(
                    """
                    UPDATE files
                    SET quality_score = ?,
                        sharpness_component = ?,
                        lighting_component = ?,
                        resolution_component = ?,
                        face_quality_component = ?
                    WHERE path = ?
                    """,
                    score_updates_with_components,
                )
            if score_updates_basic:
                conn.executemany(
                    """
                    UPDATE files
                    SET quality_score = ?
                    WHERE path = ?
                    """,
                    score_updates_basic,
                )

            if best_path:
                conn.execute(
                    """
                    UPDATE files
                    SET is_recommended = 1, keeper_source = 'auto'
                    WHERE path = ?
                    """,
                    (str(best_path),),
                )

            if second_path:
                conn.execute(
                    """
                    UPDATE files
                    SET keeper_source = 'auto_secondary'
                    WHERE path = ?
                    """,
                    (str(second_path),),
                )

            _emit_progress(98, 5, t("merge_progress_phase_finalize"), t("merge_progress_detail_finalize"), 0, 0, force=True)
            conn.commit()
            _emit_progress(100, 5, t("merge_progress_phase_done"), t("merge_progress_detail_done"), 0, 0, force=True)
            self.finished.emit(True)
        except Exception as e:
            logger.error("MergeGroupRatingWorker failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning("Error closing connection: %s", e)
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.warning("Error closing database: %s", e)


class DuplicateFinderThread(QThread):
    """Worker thread for duplicate group building."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, db_path: Path, phash_threshold: int = 5):
        super().__init__()
        self.db_path = db_path
        self.phash_threshold = phash_threshold

    def run(self) -> None:
        from photo_cleaner.duplicates.finder import DuplicateFinder

        db = None
        conn = None
        try:
            db = Database(self.db_path)
            conn = db.connect()
            finder = DuplicateFinder(db, phash_threshold=self.phash_threshold)
            group_rows = finder.build_groups()
            self.finished.emit(group_rows)
        except Exception as e:
            logger.error("Duplicate finder failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning("Error closing connection: %s", e)
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.warning("Error closing database: %s", e)
