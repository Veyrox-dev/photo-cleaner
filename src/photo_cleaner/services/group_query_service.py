from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Callable

from photo_cleaner.ui.models.rows import GroupRow

logger = logging.getLogger(__name__)


class GroupQueryService:
    """Service layer for loading and preparing duplicate/single-image groups."""

    def query_groups(
        self,
        conn: sqlite3.Connection,
        hide_completed_groups: bool,
        *,
        build_group_diagnostics_fn: Callable[..., str],
        classify_group_confidence_fn: Callable[[int], str],
        build_score_explanation_fn: Callable[..., object],
        compute_file_confidence_bucket_fn: Callable[..., int],
    ) -> tuple[list[GroupRow], dict[str, GroupRow], int, int]:
        group_lookup: dict[str, GroupRow] = {}

        cur = conn.execute(
            """
            SELECT d.group_id,
                   MIN(f.path) AS sample_path,
                   COUNT(*) AS total,
                   SUM(CASE WHEN COALESCE(f.file_status, 'UNDECIDED') IN ('UNDECIDED','UNSURE') THEN 1 ELSE 0 END) AS open_cnt,
                   SUM(CASE WHEN COALESCE(f.file_status, 'UNDECIDED') IN ('KEEP','DELETE') THEN 1 ELSE 0 END) AS decided_cnt,
                   SUM(CASE WHEN COALESCE(f.file_status, 'UNDECIDED') = 'DELETE' THEN 1 ELSE 0 END) AS delete_cnt,
                   MAX(d.similarity_score) AS sim,
                   SUM(CASE WHEN f.quality_score IS NOT NULL THEN 1 ELSE 0 END) AS analyzed_cnt,
                   MIN(
                       CASE
                           WHEN f.quality_score IS NULL THEN 0
                           WHEN (f.sharpness_component IS NULL AND f.lighting_component IS NULL AND f.resolution_component IS NULL AND f.face_quality_component IS NULL)
                               THEN 10
                           WHEN (
                               f.quality_score >= 75
                               AND COALESCE(f.sharpness_component, 100) >= 60
                               AND COALESCE(f.lighting_component, 100) >= 60
                               AND COALESCE(f.resolution_component, 100) >= 60
                               AND COALESCE(f.face_quality_component, 100) >= 60
                           ) THEN 100
                           WHEN (
                               f.quality_score < 45
                               OR COALESCE(f.sharpness_component < 30, 0)
                               OR COALESCE(f.lighting_component < 30, 0)
                               OR COALESCE(f.resolution_component < 30, 0)
                               OR COALESCE(f.face_quality_component < 30, 0)
                               OR (
                                   (CASE WHEN f.sharpness_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.lighting_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.resolution_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.face_quality_component < 45 THEN 1 ELSE 0 END)
                               ) >= 2
                           ) THEN 25
                           ELSE 65
                       END
                   ) AS min_conf_bucket,
                   SUM(
                       CASE
                           WHEN f.quality_score IS NULL THEN 0
                           WHEN (
                               (f.sharpness_component IS NULL AND f.lighting_component IS NULL AND f.resolution_component IS NULL AND f.face_quality_component IS NULL)
                               OR f.quality_score < 45
                               OR (
                                   (CASE WHEN f.sharpness_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.lighting_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.resolution_component < 45 THEN 1 ELSE 0 END)
                                   + (CASE WHEN f.face_quality_component < 45 THEN 1 ELSE 0 END)
                               ) >= 2
                           ) THEN 1
                           ELSE 0
                       END
                   ) AS needs_review_cnt,
                   SUM(CASE WHEN f.sharpness_component < 45 THEN 1 ELSE 0 END) AS weak_sharpness_cnt,
                   SUM(CASE WHEN f.lighting_component < 45 THEN 1 ELSE 0 END) AS weak_lighting_cnt,
                   SUM(CASE WHEN f.resolution_component < 45 THEN 1 ELSE 0 END) AS weak_resolution_cnt,
                   SUM(CASE WHEN f.face_quality_component < 45 THEN 1 ELSE 0 END) AS weak_face_cnt,
                   SUM(CASE WHEN f.sharpness_component >= 75 THEN 1 ELSE 0 END) AS strong_sharpness_cnt,
                   SUM(CASE WHEN f.lighting_component >= 75 THEN 1 ELSE 0 END) AS strong_lighting_cnt,
                   SUM(CASE WHEN f.resolution_component >= 75 THEN 1 ELSE 0 END) AS strong_resolution_cnt,
                   SUM(CASE WHEN f.face_quality_component >= 75 THEN 1 ELSE 0 END) AS strong_face_cnt
            FROM duplicates d
            JOIN files f ON f.file_id = d.file_id
            WHERE f.is_deleted = 0
            GROUP BY d.group_id
            ORDER BY (open_cnt > 0) DESC, open_cnt DESC, MAX(COALESCE(f.is_recommended, 0)) DESC, MIN(COALESCE(f.capture_time, f.modified_time, 0)) ASC, d.group_id
            """
        )

        rows = cur.fetchall()
        result: list[GroupRow] = []

        for r in rows:
            analyzed_count = int(r[7] or 0)
            min_conf_bucket = int(r[8] or 0)
            needs_review_count = int(r[9] or 0)
            confidence_score = min_conf_bucket if analyzed_count > 0 else 0
            diagnostics_text = build_group_diagnostics_fn(
                weak_sharpness=int(r[10] or 0),
                weak_lighting=int(r[11] or 0),
                weak_resolution=int(r[12] or 0),
                weak_face=int(r[13] or 0),
                strong_sharpness=int(r[14] or 0),
                strong_lighting=int(r[15] or 0),
                strong_resolution=int(r[16] or 0),
                strong_face=int(r[17] or 0),
            )

            grp = GroupRow(
                group_id=str(r[0]),
                sample_path=Path(r[1]),
                total=r[2] or 0,
                open_count=r[3] or 0,
                decided_count=r[4] or 0,
                delete_count=r[5] or 0,
                similarity=float(r[6] or 0.0),
                needs_review_count=needs_review_count,
                confidence_score=confidence_score,
                confidence_level=classify_group_confidence_fn(confidence_score),
                diagnostics_text=diagnostics_text,
            )

            if hide_completed_groups and grp.open_count == 0:
                continue

            result.append(grp)
            group_lookup[grp.group_id] = grp

        cur = conn.execute(
            """
            SELECT f.file_id,
                   f.path,
                   f.file_status,
                   f.quality_score,
                   f.sharpness_component,
                   f.lighting_component,
                   f.resolution_component,
                   f.face_quality_component
            FROM files f
            LEFT JOIN duplicates d ON f.file_id = d.file_id
            WHERE f.is_deleted = 0
              AND d.file_id IS NULL
              AND COALESCE(f.file_status, 'UNDECIDED') IN ('UNDECIDED', 'UNSURE')
            ORDER BY f.path
            """
        )

        single_rows = cur.fetchall()

        for row in single_rows:
            file_id, path, status, quality_score, sharpness, lighting, resolution, face_quality = row
            file_path = Path(path)

            try:
                file_path.stat()
            except (FileNotFoundError, OSError) as e:
                logger.warning(
                    "Single-image group SINGLE_%s: Datei nicht verfügbar (%s): %s",
                    file_id,
                    file_path.name,
                    e,
                )
                try:
                    conn.execute("UPDATE files SET is_deleted = 1 WHERE file_id = ?", (file_id,))
                    conn.commit()
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as db_err:
                    logger.error("Fehler beim Markieren als gelöscht: %s", db_err, exc_info=True)
                continue

            explanation = build_score_explanation_fn(
                quality_score=float(quality_score) if quality_score is not None else None,
                sharpness_score=float(sharpness) if sharpness is not None else None,
                lighting_score=float(lighting) if lighting is not None else None,
                resolution_score=float(resolution) if resolution is not None else None,
                face_quality_score=float(face_quality) if face_quality is not None else None,
            )
            confidence_score = compute_file_confidence_bucket_fn(
                quality_score=float(quality_score) if quality_score is not None else None,
                sharpness_score=float(sharpness) if sharpness is not None else None,
                lighting_score=float(lighting) if lighting is not None else None,
                resolution_score=float(resolution) if resolution is not None else None,
                face_quality_score=float(face_quality) if face_quality is not None else None,
            )

            single_grp = GroupRow(
                group_id=f"SINGLE_{file_id}",
                sample_path=file_path,
                total=1,
                open_count=1,
                decided_count=0,
                delete_count=0,
                similarity=0.0,
                needs_review_count=1 if confidence_score in (10, 25) else 0,
                confidence_score=confidence_score,
                confidence_level=classify_group_confidence_fn(confidence_score),
                diagnostics_text=explanation.component_summary_text or "Diagnose: Einzelbild",
            )
            result.append(single_grp)
            group_lookup[single_grp.group_id] = single_grp

        return result, group_lookup, len(single_rows), len(rows)
