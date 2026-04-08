"""Modern PhotoCleaner UI with grid view, zoom, and EXIF display.

This is a complete redesign of the main UI with focus on:
- Clean, modern card-based design
- Grid thumbnail view with detail modal
- Zoom functionality (mousewheel, +/-, pan)
- Structured EXIF data display
- Smooth animations and transitions
- Better visual hierarchy

v0.5.3: Async indexing + smart caching integration
"""
from __future__ import annotations

import logging
import os
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from PySide6.QtCore import (
    Qt,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    QTimer,
    QThread,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPalette,
    QPixmap,
    QShortcut,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QMessageBox,
    QFileDialog,
    QScrollBar,
    QAbstractItemView,
    QSlider,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QInputDialog,
)

from photo_cleaner.db.schema import Database
from photo_cleaner.config import AppConfig
from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.repositories.history_repository import HistoryRepository
from photo_cleaner.services.mode_service import ModeService
from photo_cleaner.services.progress_service import ProgressService
from photo_cleaner.services.rule_simulator import RuleSimulator
from photo_cleaner.services.status_service import StatusService
# LAZY: Import QualityAnalyzer and GroupScorer only when needed (they import numpy)
# NOTE: get_thumbnail is used for detail views only; list/grid thumbnails are async.
from photo_cleaner.ui.thumbnail_cache import get_thumbnail
from photo_cleaner.ui_actions import UIActions
from photo_cleaner.session_manager import SessionManager
from photo_cleaner.ui.indexing_thread import IndexingThread  # v0.5.3
from photo_cleaner.ui.workflows.indexing_workflow_controller import IndexingWorkflowController
from photo_cleaner.ui.workflows.rating_workflow_controller import RatingWorkflowController
from photo_cleaner.ui.workflows.selection_workflow_controller import SelectionWorkflowController
from photo_cleaner.ui.workflows.export_delete_workflow_controller import ExportDeleteWorkflowController
from photo_cleaner.cache.image_cache_manager import ImageCacheManager  # v0.5.3
from photo_cleaner.ui.thumbnail_lazy import ThumbnailLoader, SmartThumbnailCache  # Thumbnail async loading

# Lazy load heavy analysis modules
_QualityAnalyzer = None
_GroupScorer = None

def _get_quality_analyzer():
    """Lazy load QualityAnalyzer to avoid numpy initialization."""
    global _QualityAnalyzer
    if _QualityAnalyzer is None:
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
        _QualityAnalyzer = QualityAnalyzer
    return _QualityAnalyzer

def _get_group_scorer():
    """Lazy load GroupScorer to avoid numpy initialization."""
    global _GroupScorer
    if _GroupScorer is None:
        from photo_cleaner.pipeline.scorer import GroupScorer
        _GroupScorer = GroupScorer
    return _GroupScorer
from photo_cleaner.i18n import t, set_language, load_language_from_settings, save_language_to_settings, get_available_languages
from photo_cleaner.theme import set_theme, load_theme_from_settings, save_theme_to_settings, apply_theme_to_palette, get_theme, get_theme_colors
from photo_cleaner.ui.color_constants import (
    get_status_colors,
    get_quality_colors,
    get_semantic_colors,
    get_text_hint_color,
    get_label_background_color,
    get_label_foreground_color,
    get_card_colors,
    get_high_contrast_colors,
    to_rgba,
)
from photo_cleaner.ui.score_explanation import build_score_explanation
from photo_cleaner.ui.group_confidence import (
    build_group_diagnostics,
    classify_group_confidence,
    compute_file_confidence_bucket,
)
from photo_cleaner.ui.theme_manager import ThemeManager


class RatingWorkerThread(QThread):
    """Worker thread for auto-rating operation (Bug #1 Fix).
    
    Prevents UI-Thread blocking during long-running quality analysis.
    Runs rating in background with signal-based progress updates.
    """
    
    # Signals
    progress = Signal(int, str)  # (percentage, status_text)
    finished = Signal(dict)  # rating_info dict {"rated": bool, "warn": bool}
    error = Signal(str)  # error message
    
    def __init__(self, db_path: Path, top_n: int, mtcnn_status: dict | None = None):
        super().__init__()
        self.db_path = db_path
        self.top_n = top_n
        self.mtcnn_status = mtcnn_status or {"available": False, "error": None}
        self._should_cancel = False
    
    def run(self):
        """Execute auto-rating in background thread."""
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
        from photo_cleaner.pipeline.scorer import GroupScorer
        from photo_cleaner.db.schema import Database
        from photo_cleaner.repositories.file_repository import FileRepository
        import time
        import sqlite3
        
        logger.info("[WORKER] RatingWorkerThread.run() STARTED")
        start_time = time.monotonic()
        info = {"rated": False, "warn": False}
        
        # LOG MTCNN status (informational only, not a blocker)
        if self.mtcnn_status.get("available", False):
            logger.info("[WORKER] ✓ MTCNN available - will use face detection for rating")
        else:
            error_msg = self.mtcnn_status.get("error", "MTCNN not available")
            logger.warning(f"[WORKER] ⚠ MTCNN not available ({error_msg}) - will use Haar Cascade fallback")
            logger.warning("[WORKER] Rating will continue with lower accuracy")
        
        db = None
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
            
            logger.info(f"[WORKER] Found {len(groups)} groups to rate")
            if not groups:
                logger.warning("[WORKER] No groups found - returning early")
                self.finished.emit(info)
                return
            
            total_images = sum(len(v) for v in groups.values())
            logger.info(f"[WORKER] Total images to analyze: {total_images}")
            
            # EMIT IMMEDIATE progress signal - tells main thread worker is active!
            elapsed = time.monotonic() - start_time
            logger.info(f"[WORKER] Thread alive after {elapsed:.2f}s [DB query complete] - emitting status")
            self.progress.emit(87, f"Modelle werden geladen... 0/{total_images}")
            
            # Initialize QualityAnalyzer with progress feedback
            logger.info(f"[WORKER] Initializing QualityAnalyzer (use_face_mesh=True)...")
            init_start = time.monotonic()
            QualityAnalyzer = _get_quality_analyzer()
            analyzer = QualityAnalyzer(use_face_mesh=True)
            init_time = time.monotonic() - init_start
            logger.info(f"[WORKER] QualityAnalyzer initialized in {init_time:.2f}s")
            
            # Emit signal after first model is ready
            self.progress.emit(88, f"QualityAnalyzer bereit, lade GroupScorer... 0/{total_images}")
            
            logger.info(f"[WORKER] Initializing GroupScorer (top_n={self.top_n})...")
            scorer_start = time.monotonic()
            GroupScorer = _get_group_scorer()
            scorer = GroupScorer(top_n=self.top_n)
            scorer_time = time.monotonic() - scorer_start
            logger.info(f"[WORKER] GroupScorer initialized in {scorer_time:.2f}s")
            
            quality_results: dict[str, list] = {}
            done = 0
            
            # NOW emit progress - models are ready
            total_init_time = time.monotonic() - start_time
            logger.info(f"[WORKER] Models ready after {total_init_time:.2f}s total, starting warmup and analysis...")
            self.progress.emit(90, f"Modelle aufwärmen... 0/{total_images}")
            
            analyzer.warmup()
            logger.info(f"[WORKER] Warmup complete, beginning batch analysis")
            self.progress.emit(87, f"Bilder werden bewertet... {done}/{total_images}")
            
            for group_id, paths in groups.items():
                if self._should_cancel:
                    logger.info("Rating cancelled by user")
                    self.finished.emit(info)
                    return
                
                logger.debug(f"Analyzing group {group_id} with {len(paths)} images...")
                
                # Update progress before analysis
                pct = 87 + int(7 * (done / max(1, total_images)))
                self.progress.emit(min(94, pct), f"Bilder werden bewertet... {done}/{total_images}")
                
                group_base_done = done
                def _progress_cb(local_done: int, local_total: int) -> None:
                    if self._should_cancel:
                        return
                    current_done = group_base_done + local_done
                    pct = 87 + int(7 * (current_done / max(1, total_images)))
                    self.progress.emit(min(94, pct), f"Bilder werden bewertet... {current_done}/{total_images}")
                
                results = analyzer.analyze_batch(paths, progress_callback=_progress_cb)
                quality_results[group_id] = results
                done += len(paths)
                
                # Update progress after analysis
                pct = 87 + int(7 * (done / max(1, total_images)))
                self.progress.emit(min(94, pct), f"Bilder werden bewertet... {done}/{total_images}")
            
            if self._should_cancel:
                logger.info("Rating cancelled by user")
                self.finished.emit(info)
                return
            
            logger.info("Scoring all groups...")
            group_scores = scorer.score_multiple_groups(quality_results)
            logger.info(f"Applying scores to database (action_id=AUTO_RATING)...")
            scorer.apply_scores_to_db(group_scores, files, action_id="AUTO_RATING")
            logger.info("Scores applied successfully")
            
            logger.info("Applying auto-selection for each group...")
            for group_id, results in quality_results.items():
                if self._should_cancel:
                    break
                
                best_path, second_path, all_scores = scorer.auto_select_best_image(group_id, results)
                try:
                    # Reset recommendations for the group
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
                    
                    # Store scores for all images
                    for item in all_scores:
                        if len(item) == 4:
                            path, score, disqualified, components = item
                            conn.execute(
                                """
                                UPDATE files
                                SET quality_score = ?,
                                    sharpness_component = ?,
                                    lighting_component = ?,
                                    resolution_component = ?,
                                    face_quality_component = ?
                                WHERE path = ?
                                """,
                                (
                                    score,
                                    components.sharpness_score,
                                    components.lighting_score,
                                    components.resolution_score,
                                    components.face_quality_score,
                                    str(path)
                                ),
                            )
                        else:
                            path, score, disqualified = item
                            conn.execute(
                                """
                                UPDATE files
                                SET quality_score = ?
                                WHERE path = ?
                                """,
                                (score, str(path)),
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
                        logger.info(f"⭐ {best_path.name} als Empfohlung markiert")
                    
                    if second_path:
                        conn.execute(
                            """
                            UPDATE files
                            SET keeper_source = 'auto_secondary'
                            WHERE path = ?
                            """,
                            (str(second_path),),
                        )
                        logger.info(f"🥈 {second_path.name} als Zweitwahl markiert")
                    
                    conn.commit()
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                    logger.error(f"Fehler beim Markieren der Empfehlungen für {group_id}: {e}", exc_info=True)
                    info["warn"] = True
            
            logger.info(f"[WORKER] RatingWorkerThread COMPLETED - rated={info['rated']}, warn={info['warn']}")
            info["rated"] = True
            self.finished.emit(info)
            
        except Exception as e:
            # Catch ALL exceptions: QualityAnalyzer crashes, import errors, Runtime errors, etc.
            logger.error(f"[WORKER] RatingWorkerThread FAILED with unexpected error: {type(e).__name__}: {e}", exc_info=True)
            info["warn"] = True
            self.error.emit(f"{type(e).__name__}: {str(e)}")
            self.finished.emit(info)
        finally:
            logger.info(f"[WORKER] RatingWorkerThread cleanup")
            if db:
                db.close()
    
    def cancel(self):
        """Cancel the rating operation."""
        self._should_cancel = True


class DuplicateFinderThread(QThread):
    """Worker thread for duplicate group building."""

    finished = Signal(object)  # group_rows list
    error = Signal(str)

    def __init__(self, db_path: Path, phash_threshold: int = 10):
        super().__init__()
        self.db_path = db_path
        self.phash_threshold = phash_threshold

    def run(self) -> None:
        from photo_cleaner.db.schema import Database
        from photo_cleaner.duplicates.finder import DuplicateFinder

        db = None
        try:
            db = Database(self.db_path)
            db.connect()
            finder = DuplicateFinder(db, phash_threshold=self.phash_threshold)
            group_rows = finder.build_groups()
            self.finished.emit(group_rows)
        except Exception as e:
            logger.error(f"Duplicate finder failed: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            if db:
                db.close()


class ExifWorkerThread(QThread):
    """P2 FIX #16: Worker thread for async EXIF extraction.
    
    Prevents UI-Thread blocking during EXIF extraction for large batches.
    Runs EXIF extraction in background with signal-based result updates.
    """
    
    # Signals
    finished = Signal(dict)  # exif_data dict {"field": "value"}
    error = Signal(str)  # error message
    
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Execute EXIF extraction in background thread."""
        try:
            logger.debug(f"ExifWorkerThread: Reading EXIF for {self.file_path.name}")
            exif_data = ExifReader.read_exif(self.file_path)
            logger.debug(f"ExifWorkerThread: EXIF read complete for {self.file_path.name}")
            self.finished.emit(exif_data)
        except Exception as e:
            logger.error(f"ExifWorkerThread: Failed to read EXIF for {self.file_path.name}: {e}", exc_info=True)
            self.error.emit(str(e))
 

class FolderSelectionDialog(QDialog):
    """Dialog zur Auswahl von Eingabe- und Ausgabeordnern + Top-N."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(t("select_folders_title"))
        self.setModal(True)
        self.resize(900, 600)
        
        self.input_folder: Optional[Path] = None
        self.output_folder: Optional[Path] = None
        self.top_n: int = 3

        self.setStyleSheet(f"QDialog {{ background-color: {get_theme_colors()['window']}; }}")
        
        self._build_ui()
    
    def _build_ui(self):
        """Erstelle Ordnerauswahl-UI mit Tabs."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Titel
        title = QLabel(f"<h2>{t('import_dialog_title')}</h2>")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 18px 20px 6px 20px;")
        layout.addWidget(title)
        
        desc = QLabel(t("import_dialog_subtitle"))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc_color = get_text_hint_color()
        desc.setStyleSheet(f"color: {desc_color}; padding: 0 28px 24px 28px; font-size: 13px;")
        layout.addWidget(desc)
        
        # Ordnerauswahl
        layout.addWidget(self._create_folder_tab(), stretch=1)
        
        layout.addSpacing(10)
        
        # Validierungsmeldung
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet(
            f"color: {get_semantic_colors()['error']}; font-weight: bold; padding: 6px 12px;"
        )
        self.validation_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.validation_label)

        # Buttons
        button_box = QDialogButtonBox()
        
        self.start_btn = QPushButton(t("start_analysis"))
        self.start_btn.setEnabled(False)
        success_color = get_semantic_colors()['success']
        self.start_btn.setStyleSheet(
            _build_button_style(success_color, padding="12px 28px", font_size=14, radius=10)
        )
        self.start_btn.clicked.connect(self.accept)
        button_box.addButton(self.start_btn, QDialogButtonBox.AcceptRole)
        
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setStyleSheet(
            _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'])
        )
        cancel_btn.clicked.connect(self.reject)
        button_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        
        layout.addWidget(button_box)

        # Load previously used folders (after buttons exist for validation)
        self._load_recent_folders()
    
    def _create_folder_tab(self) -> QWidget:
        """Erstelle Ordnerauswahl-Tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Icon size for group previews (used elsewhere)
        
        # Eingabeordner
        input_group = QWidget()
        input_group.setStyleSheet(_build_surface_style())
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(8)
        input_layout.setContentsMargins(16, 16, 16, 16)
        
        input_label = QLabel(t("select_input_folder_label"))
        input_layout.addWidget(input_label)
        
        input_hint = QLabel(f"<i>{t('import_input_card_hint')}</i>")
        hint_color = get_text_hint_color()
        input_hint.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
        input_layout.addWidget(input_hint)
        
        input_row = QHBoxLayout()
        self.input_path_label = QLabel(t("not_selected"))
        self.input_path_label.setStyleSheet(_build_path_label_style(is_empty=True))
        input_row.addWidget(self.input_path_label, stretch=1)
        
        input_btn = QPushButton(t("browse"))
        input_btn.setFixedWidth(120)
        input_btn.setStyleSheet(_build_button_style(get_semantic_colors()["info"], padding="10px 14px"))
        input_btn.clicked.connect(self._select_input_folder)
        input_row.addWidget(input_btn)
        
        input_layout.addLayout(input_row)
        layout.addWidget(input_group)
        
        # Ausgabeordner
        output_group = QWidget()
        output_group.setStyleSheet(_build_surface_style())
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)
        output_layout.setContentsMargins(16, 16, 16, 16)
        
        output_label = QLabel(f"{t('select_output_folder_label')} {t('output_folder_required')}")
        output_layout.addWidget(output_label)
        
        output_hint = QLabel(f"<i>{t('import_output_card_hint')}</i>")
        hint_color = get_text_hint_color()
        output_hint.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
        output_layout.addWidget(output_hint)
        
        output_row = QHBoxLayout()
        self.output_path_label = QLabel(t("not_selected"))
        self.output_path_label.setStyleSheet(_build_path_label_style(is_empty=True))
        output_row.addWidget(self.output_path_label, stretch=1)
        
        output_btn = QPushButton(t("browse"))
        output_btn.setFixedWidth(120)
        output_btn.setStyleSheet(_build_button_style(get_semantic_colors()["info"], padding="10px 14px"))
        output_btn.clicked.connect(self._select_output_folder)
        output_row.addWidget(output_btn)
        
        output_layout.addLayout(output_row)
        layout.addWidget(output_group)

        # Top-N Auswahl
        topn_group = QWidget()
        topn_group.setStyleSheet(_build_surface_style())
        topn_layout = QVBoxLayout(topn_group)
        topn_layout.setSpacing(8)
        topn_layout.setContentsMargins(16, 16, 16, 16)

        topn_label = QLabel(t("select_topn_label"))
        topn_layout.addWidget(topn_label)

        topn_hint = QLabel(f"<i>{t('import_topn_card_hint')}</i>")
        hint_color = get_text_hint_color()
        topn_hint.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
        topn_layout.addWidget(topn_hint)

        topn_row = QHBoxLayout()
        self.topn_spin = QSpinBox()
        self.topn_spin.setRange(1, 10)
        self.topn_spin.setValue(self.top_n)
        self.topn_spin.setFixedWidth(80)
        self.topn_spin.setStyleSheet(_build_input_style())
        self.topn_spin.valueChanged.connect(self._on_topn_changed)
        topn_row.addWidget(self.topn_spin)
        topn_row.addStretch()
        topn_layout.addLayout(topn_row)

        layout.addWidget(topn_group)
        
        layout.addStretch()
        return container
    
    def _create_quality_tab(self) -> QWidget:
        """Erstelle Quality Settings Tab."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Titel
        quality_title = QLabel(f"<b>{t('quality_settings_for_analysis')}</b>")
        quality_title.setStyleSheet("font-size: 14px;")
        layout.addWidget(quality_title)
        
        # Preset Auswahl
        preset_group = QWidget()
        preset_layout = QHBoxLayout(preset_group)
        preset_layout.setSpacing(10)
        
        preset_label = QLabel(f"{t('presets')}:")
        preset_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        presets = self.preset_manager.list_presets()
        self.preset_combo.addItems(presets)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo, stretch=1)
        
        layout.addWidget(preset_group)
        
        # Quality Panel (von main_window kopiert)
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
            }
            QScrollBar::handle:vertical {{
                background-color: {colors['disabled_bg']};
                border-radius: 6px;
            }}
        """)
        scroll_area.setWidgetResizable(True)
        
        quality_panel = self._create_quality_controls()
        scroll_area.setWidget(quality_panel)
        layout.addWidget(scroll_area, stretch=1)
        
        return container
    
    def _create_quality_controls(self) -> QWidget:
        """Erstelle Quality Control Widgets."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(15)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        
        # Blur Weight
        blur_group = QWidget()
        blur_layout = QHBoxLayout(blur_group)
        blur_layout.setSpacing(10)
        
        blur_label = QLabel(f"{t('blur')}-Gewicht:")
        blur_layout.addWidget(blur_label)
        
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(100)
        self.blur_slider.setValue(int(self.config_update_system.get_config('blur_weight') * 100))
        colors = get_theme_colors()
        slider_groove_border = colors['input_border']
        slider_groove_bg = get_label_background_color()
        success_color = get_semantic_colors()["success"]
        self.blur_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {slider_groove_border};
                height: 6px;
                background: {slider_groove_bg};
            }}
            QSlider::handle:horizontal {{
                background: {success_color};
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }}
        """)
        self.blur_value_label = QLabel(f"{self.blur_slider.value()}%")
        self.blur_slider.valueChanged.connect(
            lambda v: self._update_quality_value('blur_weight', v / 100, self.blur_value_label)
        )
        blur_layout.addWidget(self.blur_slider, stretch=1)
        blur_layout.addWidget(self.blur_value_label, alignment=Qt.AlignRight)
        panel_layout.addWidget(blur_group)
        
        # Contrast Weight
        contrast_group = QWidget()
        contrast_layout = QHBoxLayout(contrast_group)
        contrast_layout.setSpacing(10)
        
        contrast_label = QLabel(f"{t('contrast')}:")
        contrast_layout.addWidget(contrast_label)
        
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.setValue(int(self.config_update_system.get_config('contrast_weight') * 100))
        self.contrast_slider.setStyleSheet(self.blur_slider.styleSheet())
        self.contrast_value_label = QLabel(f"{self.contrast_slider.value()}%")
        self.contrast_slider.valueChanged.connect(
            lambda v: self._update_quality_value('contrast_weight', v / 100, self.contrast_value_label)
        )
        contrast_layout.addWidget(self.contrast_slider, stretch=1)
        contrast_layout.addWidget(self.contrast_value_label, alignment=Qt.AlignRight)
        panel_layout.addWidget(contrast_group)
        
        # Exposure Weight
        exp_group = QWidget()
        exp_layout = QHBoxLayout(exp_group)
        exp_layout.setSpacing(10)
        
        exp_label = QLabel(f"{t('exposure')}:")
        exp_layout.addWidget(exp_label)
        
        self.exp_slider = QSlider(Qt.Horizontal)
        self.exp_slider.setMinimum(0)
        self.exp_slider.setMaximum(100)
        self.exp_slider.setValue(int(self.config_update_system.get_config('exposure_weight') * 100))
        self.exp_slider.setStyleSheet(self.blur_slider.styleSheet())
        self.exp_value_label = QLabel(f"{self.exp_slider.value()}%")
        self.exp_slider.valueChanged.connect(
            lambda v: self._update_quality_value('exposure_weight', v / 100, self.exp_value_label)
        )
        exp_layout.addWidget(self.exp_slider, stretch=1)
        exp_layout.addWidget(self.exp_value_label, alignment=Qt.AlignRight)
        panel_layout.addWidget(exp_group)
        
        # Noise Weight
        noise_group = QWidget()
        noise_layout = QHBoxLayout(noise_group)
        noise_layout.setSpacing(10)
        
        noise_label = QLabel(f"{t('noise')}:")
        noise_layout.addWidget(noise_label)
        
        self.noise_slider = QSlider(Qt.Horizontal)
        self.noise_slider.setMinimum(0)
        self.noise_slider.setMaximum(100)
        self.noise_slider.setValue(int(self.config_update_system.get_config('noise_weight') * 100))
        self.noise_slider.setStyleSheet(self.blur_slider.styleSheet())
        self.noise_value_label = QLabel(f"{self.noise_slider.value()}%")
        self.noise_slider.valueChanged.connect(
            lambda v: self._update_quality_value('noise_weight', v / 100, self.noise_value_label)
        )
        noise_layout.addWidget(self.noise_slider, stretch=1)
        noise_layout.addWidget(self.noise_value_label, alignment=Qt.AlignRight)
        panel_layout.addWidget(noise_group)
        
        # Eye Detection Settings
        eye_group = QWidget()
        eye_layout = QVBoxLayout(eye_group)
        eye_layout.setSpacing(8)
        
        eye_label = QLabel(f"<b>{t('eye_detection')}</b>")
        eye_layout.addWidget(eye_label)
        
        self.closed_eyes_check = QCheckBox(t("closed_eyes_detection"))
        self.closed_eyes_check.setChecked(self.config_update_system.get_config('detect_closed_eyes', True))
        self.closed_eyes_check.stateChanged.connect(
            lambda: self._update_checkbox_value('detect_closed_eyes', self.closed_eyes_check.isChecked())
        )
        eye_layout.addWidget(self.closed_eyes_check)
        
        self.redeye_check = QCheckBox(t("redeye_detection"))
        self.redeye_check.setChecked(self.config_update_system.get_config('detect_redeye', True))
        self.redeye_check.stateChanged.connect(
            lambda: self._update_checkbox_value('detect_redeye', self.redeye_check.isChecked())
        )
        eye_layout.addWidget(self.redeye_check)
        
        panel_layout.addWidget(eye_group)
        
        # Detection Settings
        detect_group = QWidget()
        detect_layout = QVBoxLayout(detect_group)
        detect_layout.setSpacing(8)
        
        detect_label = QLabel(f"<b>{t('error_detection')}</b>")
        detect_layout.addWidget(detect_label)
        
        self.blurry_check = QCheckBox(t("blurry_detection"))
        self.blurry_check.setChecked(self.config_update_system.get_config('detect_blurry', True))
        self.blurry_check.stateChanged.connect(
            lambda: self._update_checkbox_value('detect_blurry', self.blurry_check.isChecked())
        )
        detect_layout.addWidget(self.blurry_check)
        
        self.underexposed_check = QCheckBox(t("underexposed_detection"))
        self.underexposed_check.setChecked(self.config_update_system.get_config('detect_underexposed', True))
        self.underexposed_check.stateChanged.connect(
            lambda: self._update_checkbox_value('detect_underexposed', self.underexposed_check.isChecked())
        )
        detect_layout.addWidget(self.underexposed_check)
        
        self.overexposed_check = QCheckBox(t("overexposed_detection"))
        self.overexposed_check.setChecked(self.config_update_system.get_config('detect_overexposed', False))
        self.overexposed_check.stateChanged.connect(
            lambda: self._update_checkbox_value('detect_overexposed', self.overexposed_check.isChecked())
        )
        detect_layout.addWidget(self.overexposed_check)
        
        panel_layout.addWidget(detect_group)
        
        panel_layout.addStretch()
        return panel
    
    def _on_preset_changed(self, preset_name: str):
        """Wenn Vorgabe geändert wird, lade Einstellungen."""
        from photo_cleaner.config_update_system import ChangeType
        
        preset_config = self.preset_manager.get_preset(preset_name)
        if preset_config:
            # Accept both QualityPreset objects and dicts
            if hasattr(preset_config, "to_dict"):
                data = preset_config.to_dict()
            elif isinstance(preset_config, dict):
                data = preset_config
            else:
                data = {}
            for key, value in data.items():
                if key != "name":  # Skip preset name
                    self.config_update_system.request_change(
                        key, value, ChangeType.PRESET_LOADED
                    )
            self.config_update_system.apply_immediately()
            self._update_ui_values()
    
    def _update_quality_value(self, key: str, value: float, label: QLabel):
        """Update quality configuration value."""
        from photo_cleaner.config_update_system import ChangeType
        
        self.config_update_system.request_change(key, value, ChangeType.SLIDER_CHANGE)
        label.setText(f"{int(value * 100)}%")
    
    def _update_checkbox_value(self, key: str, value: bool):
        """Update checkbox configuration value."""
        from photo_cleaner.config_update_system import ChangeType
        
        self.config_update_system.request_change(key, value, ChangeType.CHECKBOX_CHANGE)
    
    def _update_ui_values(self):
        """Update all UI values from config."""
        self.blur_slider.setValue(
            int(self.config_update_system.get_config('blur_weight') * 100)
        )
        self.contrast_slider.setValue(
            int(self.config_update_system.get_config('contrast_weight') * 100)
        )
        self.exp_slider.setValue(
            int(self.config_update_system.get_config('exposure_weight') * 100)
        )
        self.noise_slider.setValue(
            int(self.config_update_system.get_config('noise_weight') * 100)
        )
        self.closed_eyes_check.setChecked(
            self.config_update_system.get_config('detect_closed_eyes', True)
        )
        self.redeye_check.setChecked(
            self.config_update_system.get_config('detect_redeye', True)
        )
        self.blurry_check.setChecked(
            self.config_update_system.get_config('detect_blurry', True)
        )
        self.underexposed_check.setChecked(
            self.config_update_system.get_config('detect_underexposed', True)
        )
        self.overexposed_check.setChecked(
            self.config_update_system.get_config('detect_overexposed', False)
        )
    
    def _select_input_folder(self):
        """Eingabeordner auswählen."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("select_input_folder_title"),
            str(self.input_folder) if self.input_folder else ""
        )
        
        if folder:
            self.input_folder = Path(folder)
            self._update_input_label()
            self._save_recent_folders()
            self._validate()
    
    def _select_output_folder(self):
        """Ausgabeordner auswählen."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("select_output_folder_title"),
            str(self.output_folder) if self.output_folder else ""
        )
        
        if folder:
            self.output_folder = Path(folder)
            self._update_output_label()
            self._save_recent_folders()
            self._validate()

    def _update_input_label(self) -> None:
        if self.input_folder:
            self.input_path_label.setText(str(self.input_folder))
            self.input_path_label.setStyleSheet(_build_path_label_style(is_empty=False))

    def _update_output_label(self) -> None:
        if self.output_folder:
            self.output_path_label.setText(str(self.output_folder))
            self.output_path_label.setStyleSheet(_build_path_label_style(is_empty=False))

    def _load_recent_folders(self) -> None:
        try:
            settings = AppConfig.get_user_settings()
            recent = settings.get("recent_folders", {})
            input_path = recent.get("input")
            output_path = recent.get("output")

            if input_path and Path(input_path).exists():
                self.input_folder = Path(input_path)
                self._update_input_label()
            if output_path and Path(output_path).exists():
                self.output_folder = Path(output_path)
                self._update_output_label()

            self._validate()
        except (KeyError, ValueError, OSError) as e:
            logger.warning(f"Could not load recent folders: {e}")

    def _save_recent_folders(self) -> None:
        try:
            settings = AppConfig.get_user_settings()
            settings["recent_folders"] = {
                "input": str(self.input_folder) if self.input_folder else "",
                "output": str(self.output_folder) if self.output_folder else "",
            }
            AppConfig.set_user_settings(settings)
        except (KeyError, ValueError, OSError) as e:
            logger.warning(f"Could not save recent folders: {e}")

    def _on_topn_changed(self, value: int):
        """Top-N Auswahl speichern.
        
        BUG #10 FIX: Validate top_n value range.
        """
        # Ensure value is within reasonable bounds (1-1000)
        validated_value = max(1, min(int(value), 1000))
        if validated_value != value:
            logger.warning(f"Top-N value {value} out of range, clamped to {validated_value}")
        self.top_n = validated_value
    
    def _validate(self):
        """Ordnerauswahl validieren."""
        # Ausgabeordner ist erforderlich
        if not self.output_folder:
            self.validation_label.setText(t("validation_select_output"))
            if hasattr(self, "start_btn"):
                self.start_btn.setEnabled(False)
            return
        
        # Eingabeordner ist optional (kann existierende DB verwenden)
        if not self.input_folder:
            self.validation_label.setText(t("validation_optional_input"))
            self.validation_label.setStyleSheet(f"color: {get_semantic_colors()['warning']}; font-weight: bold;")
        else:
            self.validation_label.setText(t("validation_ready"))
            self.validation_label.setStyleSheet(f"color: {get_semantic_colors()['success']}; font-weight: bold;")
        
        if hasattr(self, "start_btn"):
            self.start_btn.setEnabled(True)


# Status colors are now provided by get_status_colors() from color_constants
# This ensures theme-aware colors that update on theme changes


@dataclass
class GroupRow:
    """Represents a duplicate group with metadata."""
    group_id: str
    sample_path: Path
    total: int
    open_count: int
    decided_count: int
    delete_count: int
    similarity: float
    needs_review_count: int = 0
    confidence_score: int = 0
    confidence_level: str = "none"
    diagnostics_text: str = ""


@dataclass
class FileRow:
    """Represents a file with its status and metadata."""
    path: Path
    status: FileStatus
    locked: bool
    is_recommended: bool
    quality_score: Optional[float] = None  # Overall quality score (0-100)
    sharpness_score: Optional[float] = None  # Sharpness component (0-100)
    lighting_score: Optional[float] = None  # Lighting/Exposure component (0-100)
    resolution_score: Optional[float] = None  # Resolution component (0-100)
    face_quality_score: Optional[float] = None  # Face quality component (0-100)


def _get_confidence_style(level: Optional[str]) -> tuple[str, str]:
    semantic_colors = get_semantic_colors()
    if level == "high":
        return semantic_colors["success"], "white"
    if level == "medium":
        return semantic_colors["warning"], "black"
    if level == "low":
        return semantic_colors["error"], "white"
    if level == "incomplete":
        return semantic_colors["info"], "white"
    colors = get_theme_colors()
    return colors["alternate_base"], colors["text"]


def _get_confidence_i18n_label(level: Optional[str]) -> str:
    """Map confidence level (internal: high/medium/low/incomplete/none) to i18n label."""
    if level == "high":
        return t("confidence_very_reliable")
    if level == "medium":
        return t("confidence_review_recommended")
    if level == "low":
        return t("confidence_review_needed")
    if level == "incomplete":
        return t("confidence_data_incomplete")
    return t("confidence_no_data")


def _get_component_bar_color(score: float) -> str:
    quality_colors = get_quality_colors()
    if score >= 75.0:
        return quality_colors["high"]
    if score >= 45.0:
        return quality_colors["medium"]
    return quality_colors["low"]


def _build_button_style(
    background_color: str,
    *,
    text_color: str = "white",
    hover_color: Optional[str] = None,
    disabled_bg: Optional[str] = None,
    disabled_text: Optional[str] = None,
    padding: str = "10px 14px",
    font_size: int = 13,
    radius: int = 8,
) -> str:
    colors = get_theme_colors()
    semantic_colors = get_semantic_colors()
    hover = hover_color or background_color
    disabled_background = disabled_bg or colors["disabled_bg"]
    disabled_foreground = disabled_text or colors["disabled_text"]
    focus_color = semantic_colors["info"]
    return f"""
        QPushButton {{
            background-color: {background_color};
            color: {text_color};
            padding: {padding};
            font-size: {font_size}px;
            font-weight: bold;
            border-radius: {radius}px;
            border: 1px solid transparent;
        }}
        QPushButton:hover:enabled {{
            background-color: {hover};
        }}
        QPushButton:focus:enabled {{
            border: 2px solid {focus_color};
        }}
        QPushButton:disabled {{
            background-color: {disabled_background};
            color: {disabled_foreground};
            border: 1px solid {disabled_background};
        }}
    """


def _build_surface_style() -> str:
    colors = get_theme_colors()
    return (
        f"background-color: {colors['window']}; "
        f"border: 1px solid {colors['border']}; "
        "border-radius: 12px;"
    )


def _build_input_style() -> str:
    colors = get_theme_colors()
    semantic_colors = get_semantic_colors()
    return f"""
        QLineEdit, QSpinBox {{
            background-color: {colors['input_bg']};
            color: {colors['text']};
            border: 1px solid {colors['input_border']};
            border-radius: 8px;
            padding: 8px 10px;
            min-height: 20px;
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border: 2px solid {semantic_colors['info']};
        }}
    """


def _build_path_label_style(is_empty: bool = False) -> str:
    colors = get_theme_colors()
    label_bg = get_label_background_color()
    label_fg = get_label_foreground_color() if is_empty else colors["text"]
    border = colors["input_border"]
    return (
        f"padding: 10px 12px; background-color: {label_bg}; color: {label_fg}; "
        f"border-radius: 8px; border: 1px solid {border};"
    )


def _resolve_default_db_path(db_path: Optional[Path]) -> Path:
    """Resolve DB path to a user-writable location by default.

    In frozen MSI installs, current working directory may be under Program Files,
    so a relative DB path would fail with permission errors.
    """
    if db_path is None:
        return AppConfig.get_db_dir() / "photo_cleaner.db"

    candidate = Path(db_path).expanduser()
    if candidate.is_absolute():
        return candidate

    return AppConfig.get_db_dir() / candidate.name


class ExifReader:
    """Liest und formatiert EXIF-Metadaten aus Bildern."""
    
    @staticmethod
    def read_exif(image_path: Path) -> dict[str, str]:
        """Lese EXIF-Daten aus Bilddatei.
        
        Gibt dict mit formatierten EXIF-Daten zurück, behandelt Fehler sicher.
        Häufige Felder: Kamera, Objektiv, ISO, Blende, Verschlusszeit, Brennweite, Aufnahmedatum, etc.
        """
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            
            exif_data = {}
            
            with Image.open(image_path) as img:
                # Get basic image info
                exif_data["Format"] = img.format or "Unknown"
                exif_data["Size"] = f"{img.width} × {img.height} px"
                exif_data["Mode"] = img.mode
                
                # Get EXIF data
                exif_raw = img.getexif()
                if not exif_raw:
                    return exif_data
                
                # Map common EXIF tags to readable names
                tag_map = {
                    "Make": "Camera Make",
                    "Model": "Camera Model",
                    "LensModel": "Lens",
                    "DateTime": "Date Taken",
                    "DateTimeOriginal": "Date Original",
                    "DateTimeDigitized": "Date Digitized",
                    "ExposureTime": "Shutter Speed",
                    "FNumber": "Aperture",
                    "ISOSpeedRatings": "ISO",
                    "FocalLength": "Focal Length",
                    "Flash": "Flash",
                    "WhiteBalance": "White Balance",
                    "ExposureProgram": "Exposure Mode",
                    "MeteringMode": "Metering Mode",
                    "Orientation": "Orientation",
                    "XResolution": "X Resolution",
                    "YResolution": "Y Resolution",
                    "Software": "Software",
                }
                
                for tag_id, value in exif_raw.items():
                    tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                    
                    # Format specific values
                    if tag_name == "ExposureTime" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            exif_data["Shutter Speed"] = f"{value[0]}/{value[1]} sec"
                    elif tag_name == "FNumber" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            f_value = value[0] / value[1]
                            exif_data["Aperture"] = f"f/{f_value:.1f}"
                    elif tag_name == "FocalLength" and isinstance(value, (tuple, list)):
                        if len(value) == 2 and value[1] != 0:
                            focal = value[0] / value[1]
                            exif_data["Focal Length"] = f"{focal:.1f} mm"
                    elif tag_name in tag_map:
                        display_name = tag_map[tag_name]
                        exif_data[display_name] = str(value)
                
                # GPS data
                gps_info = exif_raw.get_ifd(0x8825)
                if gps_info:
                    exif_data["GPS"] = "Available"
            
            return exif_data
            
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Could not read EXIF: {e}", exc_info=True)
            return {"Error": f"Could not read EXIF: {e}"}
    
    @staticmethod
    def format_exif_html(exif_data: dict[str, str]) -> str:
        """Formatiere EXIF-Daten als HTML zur Anzeige."""
        if not exif_data:
            return "<p><i>Keine EXIF-Daten verfügbar</i></p>"
        
        html = "<table style='width: 100%; border-collapse: collapse;'>"
        
        # Nach Kategorien gruppieren
        basic_fields = ["Format", "Size", "Mode"]
        camera_fields = ["Camera Make", "Camera Model", "Lens"]
        exposure_fields = ["Shutter Speed", "Aperture", "ISO", "Focal Length"]
        other_fields = [k for k in exif_data.keys() 
                       if k not in basic_fields + camera_fields + exposure_fields]
        
        def add_section(title: str, fields: list[str]):
            nonlocal html
            section_data = {k: v for k, v in exif_data.items() if k in fields}
            if section_data:
                label_color = get_label_foreground_color()
                info_color = get_semantic_colors()["info"]
                html += f"<tr><td colspan='2' style='padding-top: 12px; font-weight: bold; color: {info_color};'>{title}</td></tr>"
                for key, value in section_data.items():
                    html += f"<tr><td style='padding: 4px 12px; color: {label_color};'>{key}</td><td style='padding: 4px;'>{value}</td></tr>"
        
        add_section("Bild", basic_fields)
        add_section("Kamera", camera_fields)
        add_section("Belichtung", exposure_fields)
        add_section("Andere", other_fields)
        
        html += "</table>"
        return html


class ZoomableImageView(QGraphicsView):
    """QGraphicsView with zoom and pan functionality.
    
    Features:
    - Mousewheel zoom (Ctrl+Wheel for fine control)
    - Keyboard shortcuts (+/- for zoom, 0 to reset)
    - Pan with middle mouse or left drag
    - Double-click to fit image
    - Smooth zoom animations
    """
    
    # NEW: Signal for sync pan (Feature 1)
    pan_changed = Signal(int, int)  # Emits (h_scroll, v_scroll) position
    zoom_changed = Signal(float)  # Emits zoom level for sync zoom
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)
        
        self._zoom_level = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._zoom_step = 1.15
        
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._sync_enabled = False  # NEW: Track if sync is enabled
        self._sync_in_progress = False  # NEW: Prevent feedback loops
        
        # Setup keyboard shortcuts
        QShortcut(QKeySequence.ZoomIn, self, activated=self.zoom_in)
        QShortcut(QKeySequence.ZoomOut, self, activated=self.zoom_out)
        QShortcut(QKeySequence("0"), self, activated=self.reset_zoom)
        
        # Connect scrollbar signals for sync pan (NEW Feature 1)
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
    
    def set_image(self, pixmap: QPixmap):
        """Load a new image into the view."""
        self.scene().clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self._pixmap_item)
        self.reset_zoom()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mousewheel zoom."""
        # Get zoom factor based on wheel delta
        delta = event.angleDelta().y()
        if delta == 0:
            return
        
        # Fine control with Ctrl
        factor = self._zoom_step if delta > 0 else (1.0 / self._zoom_step)
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.0 + (factor - 1.0) * 0.5  # Halve zoom speed
        
        self._apply_zoom(factor)
        
        # NEW: Emit zoom signal if sync is enabled (for sync zoom with mousewheel)
        if self._sync_enabled:
            self.zoom_changed.emit(self._zoom_level)
    
    def mouseDoubleClickEvent(self, event):
        """Fit image on double-click."""
        if event.button() == Qt.LeftButton:
            self.fit_in_view()
        else:
            super().mouseDoubleClickEvent(event)
    
    def zoom_in(self):
        """Zoom in (keyboard shortcut)."""
        self._apply_zoom(self._zoom_step)
    
    def zoom_out(self):
        """Zoom out (keyboard shortcut)."""
        self._apply_zoom(1.0 / self._zoom_step)
    
    def reset_zoom(self):
        """Reset to fit view."""
        self.fit_in_view()
    
    def fit_in_view(self):
        """Fit the entire image in the view."""
        if not self._pixmap_item:
            return
        
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._zoom_level = self.transform().m11()
    
    def _apply_zoom(self, factor: float):
        """Apply zoom factor, respecting limits."""
        new_zoom = self._zoom_level * factor
        
        # Clamp to limits
        if new_zoom < self._min_zoom:
            factor = self._min_zoom / self._zoom_level
        elif new_zoom > self._max_zoom:
            factor = self._max_zoom / self._zoom_level
        
        if factor != 1.0:
            self.scale(factor, factor)
            self._zoom_level *= factor
    
    def _on_scroll_changed(self):
        """Emit pan_changed signal when scrollbars move (Feature 1)."""
        if self._sync_enabled and not self._sync_in_progress:
            h_value = self.horizontalScrollBar().value()
            v_value = self.verticalScrollBar().value()
            self.pan_changed.emit(h_value, v_value)
    
    def set_scroll_position(self, h_value: int, v_value: int):
        """Set scroll position externally (for sync pan, Feature 1)."""
        self._sync_in_progress = True
        
        # Use a timer to ensure smooth updates
        self.horizontalScrollBar().setValue(h_value)
        self.verticalScrollBar().setValue(v_value)
        
        # Reset flag after a short delay
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, lambda: setattr(self, '_sync_in_progress', False))
    
    def set_zoom_level(self, zoom_level: float):
        """Set zoom level externally (for sync zoom, Feature 1)."""
        if zoom_level < self._min_zoom:
            zoom_level = self._min_zoom
        elif zoom_level > self._max_zoom:
            zoom_level = self._max_zoom
        
        factor = zoom_level / self._zoom_level
        self._apply_zoom(factor)


class ImageDetailDialog(QDialog):
    """Modal dialog for full-screen image view with zoom and EXIF."""
    
    def __init__(self, file_row: FileRow, parent=None):
        super().__init__(parent)
        
        self.file_row = file_row
        
        self.setWindowTitle(f"Detail: {file_row.path.name}")
        self.resize(1400, 900)
        self.setModal(True)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build detail dialog UI."""
        layout = QHBoxLayout(self)
        
        # Left: Zoomable image view
        self.image_view = ZoomableImageView()
        layout.addWidget(self.image_view, stretch=3)
        
        # Right: Info panel
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_panel.setMaximumWidth(400)
        
        # File info
        info_layout.addWidget(QLabel(f"<h3>{self.file_row.path.name}</h3>"))
        
        status_label = QLabel(f"Status: <b>{self.file_row.status.value}</b>")
        status_colors = get_status_colors()
        status_color = status_colors.get(self.file_row.status.value, status_colors['UNDECIDED'])
        status_label.setStyleSheet(f"color: {status_color}; padding: 8px; font-size: 14px;")
        info_layout.addWidget(status_label)
        
        if self.file_row.locked:
            lock_label = QLabel("🔒 <b>LOCKED</b>")
            lock_label.setStyleSheet(f"color: {get_semantic_colors()['warning']}; padding: 4px;")
            info_layout.addWidget(lock_label)
        
        if self.file_row.is_recommended:
            rec_label = QLabel("⭐ <b>RECOMMENDED</b>")
            rec_label.setStyleSheet(f"color: {get_semantic_colors()['success']}; padding: 4px;")
            info_layout.addWidget(rec_label)
        
        info_layout.addWidget(QLabel(f"<small>{self.file_row.path}</small>"))
        
        # File stats
        try:
            stat = self.file_row.path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            info_layout.addWidget(QLabel(f"Size: {size_mb:.2f} MB"))
            
            from datetime import datetime
            mtime = datetime.fromtimestamp(stat.st_mtime)
            info_layout.addWidget(QLabel(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M')}"))
        except (OSError, IOError):
            logger.warning(f"Could not read file stats for {self.file_row.path}", exc_info=True)
            pass

        # Quality scores
        colors = get_theme_colors()
        quality_box = QGroupBox("Qualität")
        quality_layout = QVBoxLayout(quality_box)

        explanation = build_score_explanation(
            quality_score=self.file_row.quality_score,
            sharpness_score=self.file_row.sharpness_score,
            lighting_score=self.file_row.lighting_score,
            resolution_score=self.file_row.resolution_score,
            face_quality_score=self.file_row.face_quality_score,
        )

        if explanation.overall_text:
            overall_label = QLabel(explanation.overall_text)
            overall_label.setStyleSheet("font-weight: bold; font-size: 13px;")
            overall_label.setToolTip(explanation.tooltip_text)
            quality_layout.addWidget(overall_label)

        if explanation.confidence_label:
            bg_color, text_color = _get_confidence_style(explanation.confidence_level)
            confidence_label = QLabel(explanation.confidence_label)
            confidence_label.setToolTip(explanation.confidence_reason or explanation.tooltip_text)
            confidence_label.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color}; font-weight: bold; padding: 4px 8px; border-radius: 6px;"
            )
            quality_layout.addWidget(confidence_label)

        if explanation.component_summary_text:
            summary_label = QLabel(explanation.component_summary_text)
            summary_label.setWordWrap(True)
            summary_label.setToolTip(explanation.tooltip_text)
            quality_layout.addWidget(summary_label)

        for metric in explanation.component_details:
            metric_row = QWidget()
            metric_layout = QHBoxLayout(metric_row)
            metric_layout.setContentsMargins(0, 0, 0, 0)
            metric_layout.setSpacing(8)

            metric_label = QLabel(metric.label)
            metric_label.setMinimumWidth(80)
            metric_layout.addWidget(metric_label)

            metric_bar = QProgressBar()
            metric_bar.setRange(0, 100)
            metric_bar.setValue(int(round(metric.value)))
            metric_bar.setTextVisible(False)
            metric_bar.setStyleSheet(
                f"QProgressBar {{ border: 1px solid {colors['border']}; border-radius: 4px; background-color: {colors['alternate_base']}; }}"
                f"QProgressBar::chunk {{ background-color: {_get_component_bar_color(metric.value)}; border-radius: 4px; }}"
            )
            metric_layout.addWidget(metric_bar, stretch=1)

            metric_value = QLabel(f"{metric.value:.0f}%")
            metric_value.setMinimumWidth(42)
            metric_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            metric_layout.addWidget(metric_value)
            quality_layout.addWidget(metric_row)

        if explanation.strengths_text:
            strengths_label = QLabel(explanation.strengths_text)
            strengths_label.setWordWrap(True)
            quality_layout.addWidget(strengths_label)

        if explanation.concerns_text:
            concerns_label = QLabel(explanation.concerns_text)
            concerns_label.setWordWrap(True)
            concerns_label.setStyleSheet(f"color: {get_semantic_colors()['warning']};")
            quality_layout.addWidget(concerns_label)

        if explanation.needs_reanalysis:
            reanalysis_label = QLabel("Details fehlen: für diese Datei bitte Analyse erneut ausführen.")
            reanalysis_label.setWordWrap(True)
            reanalysis_label.setStyleSheet(f"color: {get_semantic_colors()['info']};")
            quality_layout.addWidget(reanalysis_label)

        if quality_layout.count() == 0:
            empty_label = QLabel("Keine Qualitätsdaten verfügbar")
            empty_label.setStyleSheet(f"color: {colors['text']}; font-style: italic;")
            quality_layout.addWidget(empty_label)

        quality_box.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {colors['border']}; border-radius: 6px; margin-top: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}"
        )
        info_layout.addWidget(quality_box)
        
        # EXIF data
        info_layout.addWidget(QLabel("<h4>EXIF Data</h4>"))
        
        exif_scroll = QScrollArea()
        exif_scroll.setWidgetResizable(True)
        exif_scroll.setFrameShape(QFrame.StyledPanel)
        
        exif_label = QLabel()
        exif_label.setWordWrap(True)
        exif_label.setTextFormat(Qt.RichText)
        
        # P2 FIX #16: Read EXIF in background worker thread to avoid blocking UI
        exif_scroll.setWidget(exif_label)
        info_layout.addWidget(exif_scroll)
        
        # Show loading message while EXIF is being read
        exif_label.setText("<i>EXIF-Daten werden geladen...</i>")
        
        # Start async EXIF extraction in worker thread
        self._exif_thread = ExifWorkerThread(self.file_row.path)
        self._exif_thread.finished.connect(lambda data: self._on_exif_ready(exif_label, data))
        self._exif_thread.error.connect(lambda err: self._on_exif_error(exif_label, err))
        self._exif_thread.start()
        
        # Zoom controls
        info_layout.addWidget(QLabel(t("h4zoom_controlsh4")))
        info_layout.addWidget(QLabel(t("mousewheel_zoom")))
        info_layout.addWidget(QLabel("Ctrl+Wheel: Fine zoom"))
        info_layout.addWidget(QLabel(t("_zoom_inout")))
        info_layout.addWidget(QLabel("0: Reset zoom"))
        info_layout.addWidget(QLabel("Double-click: Fit view"))
        info_layout.addWidget(QLabel("Drag: Pan image"))
        
        info_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        info_layout.addWidget(close_btn)
        
        layout.addWidget(info_panel, stretch=1)
        
        # Load image
        self._load_image()
    
    def _on_exif_ready(self, exif_label: QLabel, exif_data: dict):
        """P2 FIX #16: Callback when EXIF extraction completes in worker thread."""
        try:
            exif_html = ExifReader.format_exif_html(exif_data)
            exif_label.setText(exif_html)
            logger.debug(f"EXIF display updated for {self.file_row.path.name}")
        except Exception as e:
            logger.error(f"Failed to format EXIF data: {e}", exc_info=True)
            exif_label.setText(f"<i>Fehler beim Anzeigen von EXIF-Daten: {e}</i>")
    
    def _on_exif_error(self, exif_label: QLabel, error_msg: str):
        """P2 FIX #16: Callback when EXIF extraction fails in worker thread."""
        logger.error(f"EXIF extraction error: {error_msg}")
        exif_label.setText(f"<i>EXIF-Daten konnten nicht geladen werden: {error_msg}</i>")
    
    def _load_image(self):
        """Load and display the image."""
        try:
            # Load high-res version for detail view
            from PIL import Image
            with Image.open(self.file_row.path) as img:
                # Convert to RGB if needed
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                
                # Load into QPixmap (limit size to prevent memory issues)
                max_size = 4096
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.LANCZOS)
                
                # Save to temp and load as pixmap
                thumb_path = get_thumbnail(self.file_row.path, (img.width, img.height))
                pixmap = QPixmap(str(thumb_path))
                
                self.image_view.set_image(pixmap)
        except (OSError, IOError, ValueError, RuntimeError) as e:
            logger.error(f"Could not load image: {e}", exc_info=True)
            QMessageBox.warning(self, t("error"), t("load_image_failed").format(error=e))


class ThumbnailCard(QWidget):
    """Modern card widget for thumbnail display with hover effects."""
    
    clicked = Signal(int)  # Emits index when clicked
    
    def __init__(self, file_row: FileRow, index: int, parent=None):
        super().__init__(parent)
        
        self.file_row = file_row
        self.index = index
        self._hovered = False
        self._selected = False
        self._pixmap = None  # Track pixmap for explicit cleanup
        
        self.setFixedSize(180, 220)
        self.setCursor(Qt.PointingHandCursor)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        colors = get_theme_colors()
        
        # Thumbnail image
        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setFixedSize(160, 160)
        thumb_bg = colors["alternate_base"]
        thumb_border = colors["border"]
        self.thumbnail.setStyleSheet(f"""
            QLabel {{
                background-color: {thumb_bg};
                border-radius: 4px;
                border: 1px solid {thumb_border};
            }}
        """)

        # Placeholder - real thumbnail is loaded asynchronously by worker
        self.set_thumbnail_placeholder()
        
        layout.addWidget(self.thumbnail)
        
        # Status indicator
        status_colors = get_status_colors()
        status_color = status_colors.get(self.file_row.status.value, status_colors['UNDECIDED'])
        status_text = self.file_row.status.value
        
        if self.file_row.is_recommended:
            status_text = "⭐ " + status_text
        if self.file_row.locked:
            status_text = "🔒 " + status_text
        
        self.status_label = QLabel(status_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
                font-size: 11px;
            }}
        """)
        layout.addWidget(self.status_label)
        
        # File name (truncated)
        name = self.file_row.path.name
        if len(name) > 25:
            name = name[:22] + "..."
        
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"font-size: 11px; color: {colors['text']};")
        layout.addWidget(name_label)
        
        # Quality Score Badge (NEW Feature 4!)
        if self.file_row.quality_score is not None:
            score = self.file_row.quality_score
            explanation = build_score_explanation(
                quality_score=self.file_row.quality_score,
                sharpness_score=self.file_row.sharpness_score,
                lighting_score=self.file_row.lighting_score,
                resolution_score=self.file_row.resolution_score,
                face_quality_score=self.file_row.face_quality_score,
            )
            quality_colors = get_quality_colors()
            # Color coding: Blue shades (avoid confusion with status colors - green/orange/red)
            if score >= 70:
                score_color = quality_colors['high']  # Dark Blue (high quality)
                score_icon = "✓"
            elif score >= 40:
                score_color = quality_colors['medium']  # Medium Blue (medium quality)
                score_icon = "~"
            else:
                score_color = quality_colors['low']  # Light Blue (low quality)
                score_icon = "✗"

            if score >= 70:
                rating_text = t("quality_rating_very_good")
            elif score >= 40:
                rating_text = t("quality_rating_good")
            else:
                rating_text = t("quality_rating_poor")

            score_text = f"{score_icon} {rating_text}"
            score_label = QLabel(score_text)
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {score_color};
                    color: white;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 6px;
                    font-size: 10px;
                }}
            """)
            score_label.setToolTip(explanation.tooltip_text)
            layout.addWidget(score_label)
        
        # Card styling
        bg = colors["base"]
        bg_hover = colors["alternate_base"]
        border = colors["border"]
        border_info = get_semantic_colors()["info"]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border-radius: 12px;
                border: 2px solid {border};
            }}
            QWidget:hover {{
                background-color: {bg_hover};
                border-color: {border_info};
            }}
        """)
    
    def mousePressEvent(self, event):
        """Emit clicked signal."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
    
    def set_selected(self, selected: bool):
        """Mark card as selected."""
        self._selected = selected
        self._update_selection_style()
    
    def is_selected(self) -> bool:
        """Check if card is selected."""
        return self._selected
    
    def _update_selection_style(self):
        """Update card style based on selection state."""
        colors = get_theme_colors()
        card_colors = get_card_colors()
        if self._selected:
            sel_bg = card_colors['bg_selected']
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {sel_bg};
                    border-radius: 12px;
                    border: 3px solid {colors['highlight']};
                }}
            """)
        else:
            bg = card_colors['bg']
            bg_hover = card_colors['bg_hover']
            border = card_colors['border']
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg};
                    border-radius: 12px;
                    border: 2px solid {border};
                }}
                QWidget:hover {{
                    background-color: {bg_hover};
                    border-color: {colors['highlight']};
                }}
            """)
            if hasattr(self, '_selection_overlay'):
                self._selection_overlay.hide()
    
    def update_status(self, new_status: FileStatus):
        """Update the status display."""
        self.file_row.status = new_status
        status_colors = get_status_colors()
        status_color = status_colors.get(new_status.value, status_colors['UNDECIDED'])
        status_text = new_status.value
        
        if self.file_row.is_recommended:
            status_text = "⭐ " + status_text
        if self.file_row.locked:
            status_text = "🔒 " + status_text
        
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
                font-size: 11px;
            }}
        """)
    
    def cleanup(self):
        """Explicitly cleanup resources before deletion (prevents memory leak)."""
        # CRITICAL: Clear pixmap reference to release memory
        self._pixmap = None
        if self.thumbnail:
            self.thumbnail.clear()
            self.thumbnail.setPixmap(QPixmap())  # Set to empty pixmap

    def set_thumbnail_placeholder(self) -> None:
        """Set a neutral placeholder before async thumbnail arrives."""
        placeholder = QPixmap(160, 160)
        placeholder.fill(Qt.gray)
        self._pixmap = placeholder
        self.thumbnail.setPixmap(placeholder)

    def set_thumbnail_image(self, qimg: QImage) -> None:
        """Apply QImage thumbnail (UI thread only)."""
        if qimg.isNull():
            self.thumbnail.setText("❌")
            return
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap = scaled
        self.thumbnail.setPixmap(scaled)


class ImageDetailWindow(QMainWindow):
    """Eigenständiges Fenster für Detailansicht eines Bildes."""
    
    def __init__(self, file_row: FileRow, parent=None, all_files: list = None, current_index: int = 0):
        super().__init__(parent)
        
        self.file_row = file_row
        self.parent_window = parent  # Reference to ModernMainWindow
        self.all_files = all_files or []  # NEW: All files in group for navigation
        self.current_index = current_index  # NEW: Current position in group
        
        # Eigenständiges Fenster
        self.setWindowTitle(f"Detailansicht - {file_row.path.name}")
        self.resize(1200, 800)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # Zentrales Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._main_layout = QVBoxLayout(central_widget)
        
        self._build_ui()
    
    def _build_ui(self):
        """Erstelle Detailansicht-UI."""
        layout = self._main_layout
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Info Header
        status_colors = get_status_colors()
        status_color = status_colors.get(self.file_row.status.value, status_colors['UNDECIDED'])
        status_text = f"<span style='color: {status_color};'>{self.file_row.status.value}</span>"
        if self.file_row.is_recommended:
            status_text = "⭐ " + status_text
        if self.file_row.locked:
            status_text = "🔒 " + status_text
        
        header = QLabel(f"<h3>{self.file_row.path.name}</h3><p>Status: {status_text}</p>")
        layout.addWidget(header)
        
        # Quality Score Display (compact banner like side-by-side)
        colors = get_theme_colors()
        explanation = build_score_explanation(
            quality_score=self.file_row.quality_score,
            sharpness_score=self.file_row.sharpness_score,
            lighting_score=self.file_row.lighting_score,
            resolution_score=self.file_row.resolution_score,
            face_quality_score=self.file_row.face_quality_score,
        )

        if explanation.has_any_data:
            parts = [
                part
                for part in (
                    explanation.overall_text,
                    explanation.confidence_label,
                    explanation.component_summary_text,
                    explanation.concerns_text,
                )
                if part
            ]

            score_label = QLabel(" | ".join(parts) if parts else "Keine Qualitätsdaten verfügbar")
            score_label.setWordWrap(True)
            score_label.setToolTip(explanation.tooltip_text)
            score_label.setStyleSheet(
                f"font-size: 11px; color: {colors['text']}; padding: 6px; background-color: {colors['base']}; border: 1px solid {colors['border']}; border-radius: 6px;"
            )
            layout.addWidget(score_label)
        
        # Image view
        image_view = ZoomableImageView()
        layout.addWidget(image_view)
        
        # Load image
        try:
            from PIL import Image
            with Image.open(self.file_row.path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                
                max_size = 4096
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.LANCZOS)
                
                thumb_path = get_thumbnail(self.file_row.path, (img.width, img.height))
                pixmap = QPixmap(str(thumb_path))
                image_view.set_image(pixmap)
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Fehler beim Laden des Bildes {self.file_row.path.name}: {e}", exc_info=True)
            error_label = QLabel("Bild konnte nicht geladen werden")
            error_label.setStyleSheet(f"color: {get_semantic_colors()['error']}; padding: 10px; font-size: 14px;")
            layout.addWidget(error_label)
        
        # P2 FIX #16: EXIF Info - load in background to avoid blocking UI
        # Create placeholder label
        info_label = QLabel("<i>EXIF-Daten werden geladen...</i>")
        hint_color = get_text_hint_color()
        info_label.setStyleSheet(f"color: {hint_color}; font-size: 12px; padding: 8px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Start async EXIF extraction in worker thread
        self._exif_label = info_label
        self._exif_thread = ExifWorkerThread(self.file_row.path)
        self._exif_thread.finished.connect(lambda data: self._on_image_exif_ready(data))
        self._exif_thread.error.connect(lambda err: self._on_image_exif_error(err))
        self._exif_thread.start()
        
        # Control bar
        control_bar = QHBoxLayout()
        
        # Navigation buttons (NEW Feature 2!)
        if self.all_files and len(self.all_files) > 1:
            prev_btn = QPushButton("◄ " + t("previous_image"))
            prev_btn.setEnabled(self.current_index > 0)
            prev_btn.clicked.connect(self._navigate_previous)
            control_bar.addWidget(prev_btn)
            
            nav_info = QLabel(f"{self.current_index + 1} / {len(self.all_files)}")
            hint_color = get_text_hint_color()
            nav_info.setStyleSheet(f"color: {hint_color}; font-size: 14px; padding: 0 12px;")
            control_bar.addWidget(nav_info)
            
            next_btn = QPushButton(t("next_image") + " ►")
            next_btn.setEnabled(self.current_index < len(self.all_files) - 1)
            next_btn.clicked.connect(self._navigate_next)
            control_bar.addWidget(next_btn)
        
        control_bar.addStretch()
        
        close_btn = QPushButton(t("close_button"))
        close_btn.clicked.connect(self.close)
        control_bar.addWidget(close_btn)
        
        layout.addLayout(control_bar)
    
    def _on_image_exif_ready(self, exif_data: dict):
        """P2 FIX #16: Callback when EXIF extraction completes for ImageDetailWindow."""
        try:
            info_parts = []
            
            if "Size" in exif_data:
                info_parts.append(f"Auflösung: {exif_data['Size']}")
            if "Camera Model" in exif_data:
                info_parts.append(f"Kamera: {exif_data['Camera Model']}")
            if "ISO" in exif_data:
                info_parts.append(f"ISO: {exif_data['ISO']}")
            if "Shutter Speed" in exif_data:
                info_parts.append(f"Verschlusszeit: {exif_data['Shutter Speed']}")
            if "Aperture" in exif_data:
                info_parts.append(f"Blende: {exif_data['Aperture']}")
            
            try:
                stat = self.file_row.path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                info_parts.append(f"Dateigröße: {size_mb:.2f} MB")
            except (OSError, IOError):
                logger.warning(f"Could not get file size for {self.file_row.path}", exc_info=True)
            
            if info_parts:
                text = " | ".join(info_parts)
            else:
                text = "<i>Keine EXIF-Daten verfügbar</i>"
            
            hint_color = get_text_hint_color()
            self._exif_label.setText(text)
            self._exif_label.setStyleSheet(f"color: {hint_color}; font-size: 12px; padding: 8px;")
            logger.debug(f"EXIF display updated for {self.file_row.path.name}")
        except Exception as e:
            logger.error(f"Failed to format EXIF data: {e}", exc_info=True)
            self._exif_label.setText(f"<i>Fehler beim Anzeigen von EXIF-Daten</i>")
    
    def _on_image_exif_error(self, error_msg: str):
        """P2 FIX #16: Callback when EXIF extraction fails for ImageDetailWindow."""
        logger.error(f"EXIF extraction error: {error_msg}")
        self._exif_label.setText("<i>EXIF-Daten konnten nicht geladen werden</i>")
    
    def _navigate_previous(self):
        """Navigate to previous image in group (Feature 2)."""
        if self.current_index > 0:
            self.current_index -= 1
            self._reload_image()
    
    def _navigate_next(self):
        """Navigate to next image in group (Feature 2)."""
        if self.current_index < len(self.all_files) - 1:
            self.current_index += 1
            self._reload_image()
    
    def _reload_image(self):
        """Reload window with new file from navigation."""
        self.file_row = self.all_files[self.current_index]
        self.setWindowTitle(f"Detailansicht - {self.file_row.path.name}")
        
        # Rebuild UI with new file
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._main_layout = QVBoxLayout(central_widget)
        self._build_ui()


class SideBySideComparisonWindow(QMainWindow):
    """Eigenständiges Fenster für Seite-an-Seite-Vergleich zweier Bilder."""
    
    def __init__(self, file_row_1: FileRow, file_row_2: FileRow, parent=None):
        super().__init__(parent)
        
        self.file_row_1 = file_row_1
        self.file_row_2 = file_row_2
        
        # P1 FIX (Feb 23, 2026): Keep references to EXIF worker threads
        # Without this, thread reference is lost and callbacks never fire
        self._exif_threads = []
        
        # Eigenständiges Fenster (nicht modal)
        self.setWindowTitle(t("seiteanseitevergleich"))
        self.resize(1600, 900)
        self.setAttribute(Qt.WA_DeleteOnClose)  # Automatisch aufräumen
        
        # Zentrales Widget für Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._main_layout = QVBoxLayout(central_widget)
        
        self._build_ui()
    
    def _build_ui(self):
        """Erstelle Vergleichs-UI."""
        layout = self._main_layout
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        colors = get_theme_colors()
        
        # Minimal title
        title = QLabel(f"<b style='font-size: 12px;'>{t('compare')}</b>")
        title.setMaximumHeight(20)
        title.setStyleSheet(f"color: {colors['text']};")
        layout.addWidget(title)
        
        # Main comparison area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Linkes Bild
        left_panel = self._build_image_panel(self.file_row_1, "Linkes Bild")
        main_splitter.addWidget(left_panel)
        
        # Rechtes Bild
        right_panel = self._build_image_panel(self.file_row_2, "Rechtes Bild")
        main_splitter.addWidget(right_panel)
        
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(main_splitter)
        
        # Compact synchronisierte Zoom-Steuerung
        control_bar = QHBoxLayout()
        control_bar.setSpacing(4)
        control_bar.setContentsMargins(0, 0, 0, 0)
        
        self.sync_pan_checkbox = QPushButton("🔗 Sync: AUS")
        self.sync_pan_checkbox.setCheckable(True)
        self.sync_pan_checkbox.setChecked(False)  # Default OFF
        self.sync_pan_checkbox.setMaximumWidth(120)
        self.sync_pan_checkbox.setMaximumHeight(28)
        bg_success = get_semantic_colors()["success"]
        self.sync_pan_checkbox.setStyleSheet(f"""
            QPushButton:checked {{
                background-color: {bg_success};
                color: white;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {colors['button']};
                color: {colors['button_text']};
                border: 1px solid {colors['border']};
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 10px;
            }}
        """)
        self.sync_pan_checkbox.clicked.connect(self._toggle_sync_pan)
        control_bar.addWidget(self.sync_pan_checkbox)
        
        # NEW: Reset Pan/Zoom button
        reset_pan_btn = QPushButton("↺ Reset")
        reset_pan_btn.setMaximumWidth(80)
        reset_pan_btn.setMaximumHeight(28)
        reset_pan_btn.setStyleSheet(
            f"font-size: 10px; padding: 4px 8px; background-color: {colors['button']}; color: {colors['button_text']}; border: 1px solid {colors['border']}; border-radius: 4px;"
        )
        reset_pan_btn.clicked.connect(self._reset_all_positions)
        control_bar.addWidget(reset_pan_btn)
        
        control_bar.addStretch()
        
        close_btn = QPushButton(t("close_button"))
        close_btn.setMaximumWidth(80)
        close_btn.setMaximumHeight(28)
        close_btn.setStyleSheet(
            f"font-size: 10px; padding: 4px 8px; background-color: {colors['button']}; color: {colors['button_text']}; border: 1px solid {colors['border']}; border-radius: 4px;"
        )
        close_btn.clicked.connect(self.close)
        control_bar.addWidget(close_btn)
        
        layout.addLayout(control_bar)
    
    def _build_image_panel(self, file_row: FileRow, title: str) -> QWidget:
        """Build panel for one image."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 2, 4, 2)
        colors = get_theme_colors()
        
        # Compact header with filename
        header = QLabel(f"<b style='font-size: 10px;'>{file_row.path.name}</b>")
        header.setWordWrap(False)
        header.setMaximumHeight(16)
        layout.addWidget(header)
        
        # Quality score breakdown (if available) - show overall and components
        explanation = build_score_explanation(
            quality_score=file_row.quality_score,
            sharpness_score=file_row.sharpness_score,
            lighting_score=file_row.lighting_score,
            resolution_score=file_row.resolution_score,
            face_quality_score=file_row.face_quality_score,
        )

        score_info = [
            part
            for part in (
                explanation.overall_text,
                explanation.confidence_label,
                explanation.component_summary_text,
            )
            if part
        ]

        if score_info:
            score_label = QLabel(" | ".join(score_info))
            score_label.setWordWrap(True)
            score_label.setMaximumHeight(32)
            score_label.setToolTip(explanation.tooltip_text)
            score_label.setStyleSheet(
                f"font-size: 9px; color: {colors['text']}; padding: 2px; background-color: {colors['base']}; border: 1px solid {colors['border']}; border-radius: 3px;"
            )
            layout.addWidget(score_label)
        elif explanation.needs_reanalysis:
            score_label = QLabel(
                f"Gesamtscore: {file_row.quality_score:.1f}% (Details: Neu analysieren erforderlich)"
            )
            score_label.setWordWrap(True)
            score_label.setMaximumHeight(24)
            score_label.setToolTip(explanation.tooltip_text)
            score_label.setStyleSheet(
                f"font-size: 9px; color: {colors['text']}; padding: 2px; background-color: {colors['base']}; border: 1px solid {colors['border']}; border-radius: 3px;"
            )
            layout.addWidget(score_label)
        
        # Image view
        image_view = ZoomableImageView()
        layout.addWidget(image_view)
        
        # Load image
        try:
            from PIL import Image
            with Image.open(file_row.path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                
                max_size = 4096
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.LANCZOS)
                
                thumb_path = get_thumbnail(file_row.path, (img.width, img.height))
                pixmap = QPixmap(str(thumb_path))
                image_view.set_image(pixmap)
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Fehler beim Laden des Bildes {file_row.path.name}: {e}", exc_info=True)
            error_label = QLabel("Bild konnte nicht geladen werden")
            error_label.setStyleSheet(f"color: {get_semantic_colors()['error']}; padding: 10px;")
            layout.addWidget(error_label)
        
        # Store view reference
        if not hasattr(self, 'left_view'):
            self.left_view = image_view
        else:
            self.right_view = image_view
        
        # P2 FIX #16: EXIF info (compact) - load in background to avoid blocking UI
        info_label = QLabel("<i>EXIF geladen...</i>")
        hint_color = get_text_hint_color()
        info_label.setStyleSheet(f"color: {hint_color}; font-size: 11px; padding: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # P1 FIX (Feb 23, 2026): Keep thread reference in list to prevent garbage collection
        # Bug: self._exif_thread was overwritten for right panel, losing left panel reference
        # Solution: Store all threads in list to maintain references
        exif_thread = ExifWorkerThread(file_row.path)
        exif_thread.finished.connect(lambda data, lbl=info_label, row=file_row: self._on_comparison_exif_ready(lbl, row, data))
        exif_thread.error.connect(lambda err, lbl=info_label: self._on_comparison_exif_error(lbl, err))
        exif_thread.start()
        self._exif_threads.append(exif_thread)  # Keep reference to prevent GC!
        
        return panel
    
    def _toggle_sync_pan(self):
        """Synchronisiertes Zoom+Pan umschalten (Feature 1)."""
        is_enabled = self.sync_pan_checkbox.isChecked()
        
        if is_enabled:
            self.sync_pan_checkbox.setText("🔗 Sync: AN")
            bg_success = get_semantic_colors()["success"]
            self.sync_pan_checkbox.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_success};
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 6px;
                }}
            """)
            
            # Enable sync in both views
            if hasattr(self, 'left_view') and hasattr(self, 'right_view'):
                self.left_view._sync_enabled = True
                self.right_view._sync_enabled = True
                
                # Connect pan signals
                self.left_view.pan_changed.connect(self._on_left_pan_changed)
                self.right_view.pan_changed.connect(self._on_right_pan_changed)
                
                # Connect zoom signals
                self.left_view.zoom_changed.connect(self._on_left_zoom_changed)
                self.right_view.zoom_changed.connect(self._on_right_zoom_changed)
        else:
            self.sync_pan_checkbox.setText("🔗 Sync: AUS")
            self.sync_pan_checkbox.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    border-radius: 6px;
                }
            """)
            
            # Disable sync in both views
            if hasattr(self, 'left_view') and hasattr(self, 'right_view'):
                self.left_view._sync_enabled = False
                self.right_view._sync_enabled = False
                
                # Disconnect signals
                try:
                    self.left_view.pan_changed.disconnect(self._on_left_pan_changed)
                    self.right_view.pan_changed.disconnect(self._on_right_pan_changed)
                    self.left_view.zoom_changed.disconnect(self._on_left_zoom_changed)
                    self.right_view.zoom_changed.disconnect(self._on_right_zoom_changed)
                except RuntimeError:
                    pass  # Already disconnected
    
    def _on_left_pan_changed(self, h: int, v: int):
        """Left pan changed - sync to right."""
        if hasattr(self, 'right_view'):
            self.right_view.set_scroll_position(h, v)
    
    def _on_right_pan_changed(self, h: int, v: int):
        """Right pan changed - sync to left."""
        if hasattr(self, 'left_view'):
            self.left_view.set_scroll_position(h, v)
    
    def _on_left_zoom_changed(self, zoom: float):
        """Left zoom changed - sync to right."""
        if hasattr(self, 'right_view'):
            self.right_view.set_zoom_level(zoom)
    
    def _on_right_zoom_changed(self, zoom: float):
        """Right zoom changed - sync to left."""
        if hasattr(self, 'left_view'):
            self.left_view.set_zoom_level(zoom)
    
    def _reset_all_positions(self):
        """Reset both images to original position and zoom (NEW!)."""
        if hasattr(self, 'left_view') and hasattr(self, 'right_view'):
            self.left_view.reset_zoom()
            self.right_view.reset_zoom()
            self.left_view.set_scroll_position(0, 0)
            self.right_view.set_scroll_position(0, 0)
    
    def _on_comparison_exif_ready(self, info_label: QLabel, file_row: FileRow, exif_data: dict):
        """P2 FIX #16: Callback when EXIF extraction completes for comparison window."""
        try:
            info_text = []
            
            if "Size" in exif_data:
                info_text.append(f"Resolution: {exif_data['Size']}")
            if "Camera Model" in exif_data:
                info_text.append(f"Camera: {exif_data['Camera Model']}")
            if "ISO" in exif_data:
                info_text.append(f"ISO: {exif_data['ISO']}")
            if "Shutter Speed" in exif_data:
                info_text.append(f"Shutter: {exif_data['Shutter Speed']}")
            if "Aperture" in exif_data:
                info_text.append(f"Aperture: {exif_data['Aperture']}")
            
            try:
                stat = file_row.path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                info_text.append(f"File Size: {size_mb:.2f} MB")
            except (OSError, IOError):
                logger.warning(f"Could not get file size for {file_row.path}", exc_info=True)
            
            text = " | ".join(info_text) if info_text else "No EXIF data available"
            info_label.setText(text)
            logger.debug(f"EXIF display updated for {file_row.path.name}")
        except Exception as e:
            logger.error(f"Failed to format EXIF data: {e}", exc_info=True)
            info_label.setText("Error reading EXIF data")
    
    def _on_comparison_exif_error(self, info_label: QLabel, error_msg: str):
        """P2 FIX #16: Callback when EXIF extraction fails for comparison window."""
        logger.error(f"EXIF extraction error: {error_msg}")
        info_label.setText("EXIF could not be loaded")

    
class VirtualScrollContainer(QWidget):
    """Virtual scrolling container for large image grids.
    
    Only renders visible items to improve performance.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.items: List[ThumbnailCard] = []
        self.visible_items: dict[int, ThumbnailCard] = {}
        self.item_height = 240  # Card height + spacing (was 280)
        self.items_per_row = 5  # More items per row (was 4)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build virtual scroll UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
    
    def set_items(self, items: List[ThumbnailCard]):
        """Set items for virtual scrolling."""
        self.items = items
        
        # Calculate total height
        total_rows = (len(items) + self.items_per_row - 1) // self.items_per_row
        total_height = total_rows * self.item_height
        
        self.container.setMinimumHeight(total_height)
        
        # Initial render
        self._render_visible_items()
    
    def _on_scroll(self):
        """Handle scroll event."""
        self._render_visible_items()
    
    def _render_visible_items(self):
        """Render only visible items."""
        if not self.items:
            return
        
        # Get visible range
        scroll_pos = self.scroll.verticalScrollBar().value()
        viewport_height = self.scroll.viewport().height()
        
        start_row = max(0, scroll_pos // self.item_height - 1)
        end_row = min(
            (len(self.items) + self.items_per_row - 1) // self.items_per_row,
            (scroll_pos + viewport_height) // self.item_height + 2
        )
        
        start_idx = start_row * self.items_per_row
        end_idx = min(len(self.items), end_row * self.items_per_row)
        
        # Remove items outside visible range
        for idx in list(self.visible_items.keys()):
            if idx < start_idx or idx >= end_idx:
                card = self.visible_items.pop(idx)
                self.grid_layout.removeWidget(card)
                card.hide()
        
        # Add items in visible range
        for idx in range(start_idx, end_idx):
            if idx not in self.visible_items and idx < len(self.items):
                card = self.items[idx]
                row = idx // self.items_per_row
                col = idx % self.items_per_row
                self.grid_layout.addWidget(card, row, col)
                card.show()
                self.visible_items[idx] = card
    
    def get_selected_indices(self) -> List[int]:
        """Get indices of all selected items."""
        return [i for i, card in enumerate(self.items) if card.is_selected()]


class ModernMainWindow(QMainWindow):
    """Modernes PhotoCleaner Hauptfenster mit Rasteransicht und verbesserter UX."""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
        input_path: Optional[Path] = None,
        mtcnn_status: dict | None = None,
    ):
        super().__init__()
        
        # Store MTCNN status for use in worker threads
        self.mtcnn_status = mtcnn_status or {"available": False, "error": None}
        
        # Kein statischer Titel - wird dynamisch gesetzt (z.B. "Detail: xyz.jpg")
        self.setWindowTitle("PhotoCleaner")
        self.resize(1600, 1000)
        self._pending_scan = bool(input_path)  # Auto-run only when provided via CLI
        
        # Default folders (user can change via main menu)
        self.input_folder: Optional[Path] = Path(input_path).resolve() if input_path else None
        default_output = output_path or (AppConfig.get_user_data_dir() / "exports")
        self.output_path: Optional[Path] = Path(default_output).resolve()
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.top_n = 3
        
        # Ensure main window becomes visible immediately (main menu accessible without import)
        try:
            self.show()
            QApplication.processEvents()
        except (RuntimeError, AttributeError):
            logger.warning("Failed to show main window", exc_info=True)
            pass
        
        self.db_path = _resolve_default_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(self.db_path)
        try:
            self.conn: sqlite3.Connection = self.db.connect()
        except sqlite3.OperationalError as e:
            fallback_path = AppConfig.get_db_dir() / "photo_cleaner.db"
            logger.warning(
                "Primary DB open failed (%s). Falling back to user DB path: %s",
                e,
                fallback_path,
            )
            if fallback_path == self.db_path:
                raise
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = fallback_path
            self.db = Database(self.db_path)
            self.conn = self.db.connect()
        
        # Initialize services
        self.files = FileRepository(self.conn)
        self.history = HistoryRepository(self.conn)
        self.mode_svc = ModeService(self.conn)
        self.progress_svc = ProgressService(self.files)
        self.mode_svc.set_mode(AppMode.CLEANUP_MODE)

        # Default to the highest eye detection stage; QualityAnalyzer will fallback safely.
        os.environ.setdefault("PHOTOCLEANER_EYE_DETECTION_STAGE", "3")
        
        self.rule_sim = RuleSimulator(
            self.files,
            image_meta_loader=lambda _p: {},
            mode_getter=self.mode_svc.get_mode,
            is_exact_duplicate=lambda _p: True,
        )
        
        self.status_svc = StatusService(
            self.files,
            self.history,
            self.mode_svc.get_mode,
            is_exact_duplicate=lambda _p: True,
        )
        
        # v0.5.3: Initialize async indexing & smart caching
        self.indexing_thread: Optional[IndexingThread] = None
        self._duplicate_thread: Optional[DuplicateFinderThread] = None
        self._rating_thread: Optional[RatingWorkerThread] = None
        self._indexing_progress_dialog: Optional[QProgressDialog] = None
        self._post_indexing_progress_dialog: Optional[QProgressDialog] = None
        self._post_indexing_cancelled = False
        self._post_indexing_group_count = 0
        self._post_indexing_duplicate_images = 0
        self._rating_error_message: Optional[str] = None
        self._indexing_results: Optional[dict] = None
        self._progress_update_ts = 0.0
        self._pipeline_start_ts = 0.0
        self._pipeline_last_known_total = 0
        self._indexing_workflow = IndexingWorkflowController(self, self._center_progress_dialog_text)
        self._rating_workflow = RatingWorkflowController(self, RatingWorkerThread, QApplication.processEvents)
        self._selection_workflow = SelectionWorkflowController()
        self._export_delete_workflow = ExportDeleteWorkflowController()
        self.cache_manager = ImageCacheManager(self.conn)
        
        # PHASE 4 FIX 1: Initialize CameraCalibrator for ML learning
        from photo_cleaner.pipeline.camera_calibrator import CameraCalibrator
        self.camera_calibrator = CameraCalibrator(self.conn)
        
        self.actions = UIActions(
            self.files,
            self.history,
            self.mode_svc,
            self.progress_svc,
            self.rule_sim,
            self.status_svc,
            camera_calibrator=self.camera_calibrator,
            cache_manager=self.cache_manager,
        )
        
        # Data
        self.groups: List[GroupRow] = []
        self.group_lookup: dict[str, GroupRow] = {}
        self.files_in_group: List[FileRow] = []
        self.current_group: Optional[str] = None
        self.current_index: int = -1
        self.thumbnail_cards: List[ThumbnailCard] = []
        self.page_size: int = 60  # P6.4 pagination cap to keep UI <100ms
        self.current_page: int = 0
        self.import_btn = None
        self.analyze_btn = None
        self.license_btn = None
        self.mini_thumb_list = None
        self.pagination_label = None
        self.prev_page_btn = None
        self.next_page_btn = None

        # Async thumbnail loading state
        self._group_thumb_total = 0
        self._group_thumb_done = 0
        self._grid_thumb_total = 0
        self._grid_thumb_done = 0
        self._thumb_loading_active = False
        self._pending_rating_summary: Optional[dict] = None
        self._grid_thumb_cache: Optional[SmartThumbnailCache] = None
        self._grid_thumb_loader: Optional[ThumbnailLoader] = None
        self._grid_thumb_index_map: dict[int, ThumbnailCard] = {}
        
        # Batch selection state - PER GROUP (not global!)
        # Maps group_id -> (selected_indices: set, last_selected_index: int)
        self._group_selection_state: dict[str, tuple[set[int], int]] = {}
        self.use_virtual_scrolling = True  # Enable for groups > 50 images
        
        # Session management
        self.session_manager = SessionManager()
        self._auto_save_timer = None
        self._auto_save_interval = 5000  # 5 seconds
        
        # Feature: License badge & duplicate count (for statusbar)
        self.license_badge_label = None
        self.duplicate_count_label = None
        
        # Theme
        self.current_theme = "Dunkel"
        self._user_settings = {}

        # Load language and theme from settings BEFORE building UI
        try:
            from photo_cleaner.i18n import load_language_from_settings
            from photo_cleaner.theme import load_theme_from_settings, apply_theme_to_palette, generate_stylesheet
            
            settings_path = AppConfig.get_user_data_dir() / "settings.json"
            load_language_from_settings(settings_path)
            load_theme_from_settings(settings_path)
            
            # Apply theme palette to app AND window
            palette = apply_theme_to_palette()
            app = QApplication.instance()
            if app:
                app.setPalette(palette)
                # Apply complete stylesheet for consistent theming
                stylesheet = generate_stylesheet()
                app.setStyleSheet(stylesheet)
            self.setPalette(palette)
        except (RuntimeError, AttributeError, ValueError) as e:
            logger.warning(f"Could not load i18n/theme settings: {e}", exc_info=True)

        self._build_ui()
        self._setup_grid_thumbnail_loader()
        self._build_menu()  # License menu
        self._wire_shortcuts()
        # Note: Theme palette is already applied during startup from settings
        # Don't override it with _apply_dark_palette() - it's redundant and breaks Light theme
        
        # Subscribe to theme changes for live updates
        theme_manager = ThemeManager.instance()
        theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # Load previous session if it exists
        self._load_session()
        
        self.refresh_groups()
        self._update_progress()
        
        # Setup auto-save timer
        self._setup_auto_save()
        
        # Start automatic scan only after DB/services/UI are ready
        if self._pending_scan:
            self._scan_input_folder()
    
    def keyPressEvent(self, event):
        """FEATURE: Keyboard Shortcuts - K/U/D for quick selection.
        
        K = Keep (mark selected files as KEEP)
        U = Unsure (mark as UNSURE)
        D = Delete (mark as DELETE)
        """
        if event.isAutoRepeat():
            event.ignore()
            return
        
        key = event.key()
        
        # Only handle shortcuts if we have current files
        if not self.files_in_group or not self.current_group:
            super().keyPressEvent(event)
            return
        
        try:
            # Get current selection
            selected_indices = self._get_selected_indices()
            if not selected_indices:
                super().keyPressEvent(event)
                return
            
            # K = Keep
            if key == Qt.Key_K:
                self._apply_status_to_selection(FileStatus.KEEP)
                event.accept()
                return
            
            # U = Unsure
            elif key == Qt.Key_U:
                self._apply_status_to_selection(FileStatus.UNSURE)
                event.accept()
                return
            
            # D = Delete
            elif key == Qt.Key_D:
                self._apply_status_to_selection(FileStatus.DELETE)
                event.accept()
                return
        
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Keyboard shortcut error: {e}", exc_info=True)
        
        # Pass other keys to parent
        super().keyPressEvent(event)
    
    def _scan_input_folder(self):
        """Eingabeordner scannen mit async indexing (v0.5.3)."""
        self._pending_scan = False  # ensure one-shot
        if not self.input_folder:
            return

        # Benutzerfreundliche Bestätigung
        reply = QMessageBox.question(
            self,
            "Ordner analysieren?",
            f"{t('images_loaded').replace('{count}', str(len(self.files)))} {self.input_folder}\n\n{t('analysis_wait')}\n\n{t('ok')}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # v0.5.3: Use async indexing
        self._start_async_indexing()
    
    def _start_async_indexing(self):
        """Start async indexing in background thread (v0.5.3)."""
        logger.info("Starting async indexing...")
        self._pipeline_start_ts = time.monotonic()
        self._pipeline_last_known_total = 0

        # BUG #3 FIX remains: controller builds a separate DB-backed indexer for thread safety
        indexer = self._indexing_workflow.build_indexer(self.db_path)

        progress = self._indexing_workflow.create_indexing_progress_dialog()
        self._indexing_progress_dialog = progress
        self._update_progress_dialog(
            progress,
            value=0,
            label="Schritt 1/3: Bilder einlesen und hashen...",
            force=True,
        )

        self.indexing_thread = self._indexing_workflow.create_indexing_thread(
            self.input_folder,
            indexer,
            on_progress=lambda curr, total, msg: self._on_indexing_progress(curr, total, msg, progress),
            on_finished=lambda results: self._on_indexing_finished(results, progress),
            on_error=lambda err: self._on_indexing_error(err, progress),
        )
        
        # Connect cancel button
        progress.canceled.connect(self._cancel_indexing)
        
        # Start thread
        self.indexing_thread.start()
        logger.info("Async indexing thread started")
    
    def _cancel_indexing(self) -> None:
        """Handle user-initiated indexing cancel without blocking the UI."""
        logger.info("Indexing cancelled by user")
        if self.indexing_thread:
            self.indexing_thread.stop(wait=False)
        if self._indexing_progress_dialog and self._indexing_progress_dialog.isVisible():
            self._indexing_progress_dialog.setLabelText("Abbruch wird ausgefuehrt...")

    def _update_progress_dialog(self, dialog: QProgressDialog, *, value: int | None = None, label: str | None = None, force: bool = False) -> None:
        if dialog is None or not dialog.isVisible():
            return
        if not force:
            now = time.monotonic()
            if now - self._progress_update_ts < 0.1:
                return
            self._progress_update_ts = now
        if value is not None:
            dialog.setValue(value)
        if label is not None:
            dialog.setLabelText(label)
        self._center_progress_dialog_text(dialog)

    def _center_progress_dialog_text(self, dialog: QProgressDialog) -> None:
        try:
            bar = dialog.findChild(QProgressBar)
            if bar:
                bar.setAlignment(Qt.AlignCenter)
        except (AttributeError, RuntimeError, ValueError):
            return

    def _format_eta(self, elapsed_sec: float, done: int, total: int) -> str:
        if total <= 0 or done <= 0 or done >= total:
            return ""
        remaining = max(0.0, elapsed_sec * ((total - done) / done))
        if remaining < 1.0:
            return ""
        if remaining < 60.0:
            return f"ETA: {int(remaining)}s"
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return f"ETA: {minutes}m {seconds}s"

    def _extract_progress_counts(self, status_text: str) -> tuple[int, int]:
        match = re.search(r"(\d+)\s*/\s*(\d+)", status_text or "")
        if not match:
            return (0, 0)
        return (int(match.group(1)), int(match.group(2)))

    def _on_indexing_progress(self, current: int, total: int, status: str, progress_dialog):
        """Handle progress update from indexing thread."""
        if progress_dialog is None or not progress_dialog.isVisible():
            return
        if total > 0:
            self._pipeline_last_known_total = total
            stage_pct = min(70, int(round((current / total) * 70)))
            elapsed = max(0.0, time.monotonic() - self._pipeline_start_ts)
            eta = self._format_eta(elapsed, current, total)
            label = f"Schritt 1/3: Bilder einlesen und hashen... ({current}/{total})"
            if eta:
                label += f"\n{eta}"
            self._update_progress_dialog(progress_dialog, value=stage_pct, label=label)
    
    def _on_indexing_finished(self, results: dict, progress_dialog):
        """Handle successful indexing completion."""
        import time
        handler_start = time.monotonic()
        logger.info("[UI] _on_indexing_finished() STARTED")
        
        if progress_dialog:
            try:
                progress_dialog.canceled.disconnect(self._cancel_indexing)
            except (RuntimeError, TypeError):
                pass
            progress_dialog.canceled.connect(self._cancel_post_indexing)
            self._update_progress_dialog(
                progress_dialog,
                value=70,
                label="Schritt 2/3: Duplikatgruppen werden erstellt...",
                force=True,
            )
        self._indexing_progress_dialog = progress_dialog

        logger.info(f"[UI] Indexing finished: {results}")
        self._indexing_results = results

        # Refresh UI for indexed files (duplicates/rating follow asynchronously)
        logger.info("[UI] About to call refresh_groups() - this should be FAST now (no thumbnail loading)")
        refresh_start = time.monotonic()
        self.refresh_groups()
        refresh_time = time.monotonic() - refresh_start
        logger.info(f"[UI] refresh_groups() returned after {refresh_time:.3f}s")
        
        self._update_progress()

        logger.info("[UI] About to start post-indexing analysis...")
        self._start_post_indexing_analysis(results)
        
        handler_time = time.monotonic() - handler_start
        logger.info(f"[UI] _on_indexing_finished() FINISHED in {handler_time:.3f}s")
    
    def _on_indexing_error(self, error_msg: str, progress_dialog):
        """Handle indexing error."""
        try:
            progress_dialog.canceled.disconnect(self._cancel_indexing)
        except (AttributeError, RuntimeError, TypeError):
            pass
        progress_dialog.close()
        self._indexing_progress_dialog = None
        logger.error(f"Indexing error: {error_msg}")
        QMessageBox.critical(self, t("error"), t("scan_failed").format(error=error_msg))

    def _start_post_indexing_analysis(self, results: dict) -> None:
        """Build duplicate groups and rate images without blocking the UI."""
        start_time = time.monotonic()
        logger.info("[UI] _start_post_indexing_analysis() STARTED")
        
        # ✅ CRITICAL FIX: Pause ThumbnailLoaders during post-indexing to prevent race conditions
        # The loaders will resume ONLY in _finish_post_indexing() after rating is complete
        if self._group_thumb_loader:
            logger.info("[UI] Pausing _group_thumb_loader during analysis...")
            self._group_thumb_loader.pause()
        if self._grid_thumb_loader:
            logger.info("[UI] Pausing _grid_thumb_loader during analysis...")
            self._grid_thumb_loader.pause()
        
        self._post_indexing_cancelled = False
        self._rating_error_message = None
        self._post_indexing_group_count = 0
        self._post_indexing_duplicate_images = 0

        logger.info("[UI] Reusing unified progress dialog for post-indexing...")
        progress = self._indexing_progress_dialog
        if progress is None:
            progress = self._indexing_workflow.create_post_indexing_progress_dialog(
                on_cancel=self._cancel_post_indexing,
            )
        progress.setMinimum(0)
        progress.setMaximum(100)
        self._update_progress_dialog(
            progress,
            value=70,
            label="Schritt 2/3: Duplikatgruppen werden erstellt...",
            force=True,
        )
        self._post_indexing_progress_dialog = progress

        logger.info("[UI] Starting DuplicateFinderThread...")
        self._duplicate_thread = DuplicateFinderThread(self.db_path, phash_threshold=10)
        self._duplicate_thread.finished.connect(self._on_duplicate_finder_finished)
        self._duplicate_thread.error.connect(self._on_duplicate_finder_error)
        self._duplicate_thread.start()
        
        setup_time = time.monotonic() - start_time
        logger.info(f"[UI] _start_post_indexing_analysis() setup completed in {setup_time:.3f}s, DuplicateFinder running...")

    def _cancel_post_indexing(self) -> None:
        """Handle cancel during duplicate/rating stages without blocking."""
        self._post_indexing_cancelled = True
        if self._rating_thread:
            self._rating_thread.cancel()
        if self._post_indexing_progress_dialog and self._post_indexing_progress_dialog.isVisible():
            self._post_indexing_progress_dialog.setLabelText("Abbruch wird ausgefuehrt...")

    def _on_duplicate_finder_finished(self, group_rows) -> None:
        import time
        handler_start = time.monotonic()
        logger.info(f"[DUPFINDER] _on_duplicate_finder_finished() STARTED with {len(group_rows) if group_rows else 0} groups")
        
        if self._post_indexing_cancelled:
            logger.info("[DUPFINDER] Cancelled, returning early")
            return

        group_rows = group_rows or []
        self._post_indexing_group_count = len(group_rows)
        self._post_indexing_duplicate_images = sum(row[1] for row in group_rows) if group_rows else 0
        logger.info(f"[DUPFINDER] Found {self._post_indexing_group_count} groups, {self._post_indexing_duplicate_images} duplicate images")

        if self._post_indexing_group_count == 0:
            logger.info("[DUPFINDER] No groups found, finishing without rating")
            self._finish_post_indexing({"rated": False, "warn": False})
            return

        # ✅ CRITICAL FIX: Render groups IMMEDIATELY after duplicate finding
        logger.info("[DUPFINDER] Rendering groups to UI...")
        render_start = time.monotonic()
        self.refresh_groups()  # Shows the duplicate groups to user
        render_time = time.monotonic() - render_start
        logger.info(f"[DUPFINDER] Groups rendered in {render_time:.3f}s - user can now see duplicate groups!")

        progress = self._post_indexing_progress_dialog
        if progress:
            progress.setMinimum(0)
            progress.setMaximum(100)
            self._update_progress_dialog(
                progress,
                value=75,
                label="Schritt 3/3: Bildbewertung startet...",
                force=True,
            )

        logger.info("[DUPFINDER] Creating RatingWorkerThread...")
        thread_create_start = time.monotonic()
        self._rating_thread = self._rating_workflow.create_and_wire_rating_thread(
            self.db_path,
            self.top_n,
            self.mtcnn_status,
            on_progress=self._on_rating_progress,
            on_finished=self._on_rating_finished,
            on_error=self._on_rating_error,
        )
        thread_create_time = time.monotonic() - thread_create_start
        logger.info(f"[DUPFINDER] RatingWorkerThread created in {thread_create_time:.3f}s")
        
        logger.info("[DUPFINDER] Starting RatingWorkerThread...")
        thread_start_time = time.monotonic()
        self._rating_workflow.start_rating_thread(self._rating_thread, progress)
        thread_start_elapsed = time.monotonic() - thread_start_time
        logger.info(f"[DUPFINDER] RatingWorkerThread.start() returned after {thread_start_elapsed:.3f}s")

        logger.info("[DUPFINDER] Rating workflow started (dialog visibility + Qt event processing delegated)")
        
        handler_time = time.monotonic() - handler_start
        logger.info(f"[DUPFINDER] _on_duplicate_finder_finished() FINISHED in {handler_time:.3f}s (thread should be running)")
        logger.info("[DUPFINDER] Waiting for [WORKER] logs from RatingWorkerThread.run()...")

    def _on_duplicate_finder_error(self, error_msg: str) -> None:
        if self._post_indexing_progress_dialog:
            self._post_indexing_progress_dialog.close()
            self._post_indexing_progress_dialog = None
        logger.error(f"Duplicate finder error: {error_msg}")
        QMessageBox.critical(self, t("error"), t("duplicate_search_failed").format(error=error_msg))

    def _on_rating_progress(self, pct: int, status: str) -> None:
        progress = self._post_indexing_progress_dialog
        if progress:
            clamped = max(0, min(100, int(pct)))
            mapped = 75 + int(round((clamped / 100) * 20))
            done, total = self._extract_progress_counts(status)
            eta = ""
            if done > 0 and total > 0:
                elapsed = max(0.0, time.monotonic() - self._pipeline_start_ts)
                eta = self._format_eta(elapsed, done, total)
            label = "Schritt 3/3: Bilder werden bewertet"
            if done > 0 and total > 0:
                label += f" ({done}/{total})"
            if eta:
                label += f"\n{eta}"
            self._update_progress_dialog(progress, value=mapped, label=label)

    def _on_rating_error(self, error_msg: str) -> None:
        logger.error(f"Rating error: {error_msg}")
        self._rating_error_message = error_msg

    def _on_rating_finished(self, rating_info: dict) -> None:
        self._finish_post_indexing(rating_info)

    def _finish_post_indexing(self, rating_info: dict) -> None:
        import time
        finish_start = time.monotonic()
        logger.info("[UI] _finish_post_indexing() STARTED")
        
        if self._post_indexing_cancelled:
            logger.info("[UI] Post-indexing was cancelled, skipping finish")
            return
        
        # ✅ CRITICAL FIX: Now that rating is complete, resume ThumbnailLoaders for sequential flow
        logger.info("[UI] Rating complete! Resuming ThumbnailLoaders for sequential flow...")
        if self._group_thumb_loader:
            self._group_thumb_loader.resume()
            logger.info("[UI] _group_thumb_loader resumed")
        if self._grid_thumb_loader:
            self._grid_thumb_loader.resume()
            logger.info("[UI] _grid_thumb_loader resumed")
        
        if self._post_indexing_progress_dialog:
            self._update_progress_dialog(
                self._post_indexing_progress_dialog,
                value=95,
                label="Schritt 3/3: Abschluss und Anzeige wird vorbereitet...",
                force=True,
            )

        logger.info("[UI] About to refresh_groups() after rating completion...")
        refresh_start = time.monotonic()
        self.refresh_groups()
        refresh_time = time.monotonic() - refresh_start
        logger.info(f"[UI] refresh_groups() completed in {refresh_time:.3f}s")
        
        self._update_progress()
        self._pending_rating_summary = rating_info
        self._update_thumbnail_progress()
        if not self._post_indexing_progress_dialog:
            summary = self._pending_rating_summary
            self._pending_rating_summary = None
            if summary is not None:
                self._show_analysis_summary(summary)
            finish_time = time.monotonic() - finish_start
            logger.info(f"[UI] _finish_post_indexing() FINISHED in {finish_time:.3f}s")
            return
        if not self._thumb_loading_active:
            summary = self._pending_rating_summary
            self._pending_rating_summary = None
            if summary is not None:
                self._show_analysis_summary(summary)
        
        finish_time = time.monotonic() - finish_start
        logger.info(f"[UI] _finish_post_indexing() FINISHED in {finish_time:.3f}s")

    def _show_analysis_summary(self, rating_info: dict) -> None:
        results = self._indexing_results or {}
        total_files = int(results.get("total_files", 0) or 0)
        new_files = int(results.get("new_files", 0) or 0)
        hashed_files = int(results.get("hashed_files", 0) or 0)
        cached_files = int(results.get("cached_files", 0) or 0)
        handled_files = hashed_files + cached_files
        not_processed = max(0, new_files - handled_files)

        msg = (
            "Analyse abgeschlossen.\n\n"
            f"Gesamtbilder: {total_files}\n"
            f"Neu verarbeitet: {new_files}\n"
            f"Erfolgreich verarbeitet: {handled_files}\n"
            f"Nicht verarbeitet: {not_processed}\n"
            f"Gefundene Gruppen: {self._post_indexing_group_count}"
        )

        if self._rating_error_message:
            msg += f"\n\nFehler:\n{self._rating_error_message}"
            msg += "\n\nWenn das Problem wiederholt auftritt, bitte Fehler melden."
        elif rating_info.get("warn"):
            msg += "\n\nHinweis: Einige Bilder konnten nicht vollstaendig bewertet werden."

        QMessageBox.information(self, "Analyse fertig", msg)
    
    def _run_automatic_pipeline(self):
        """Führe vollautomatische Pipeline aus: Scannen → Indexieren → Duplikate finden → Qualität analysieren."""
        from photo_cleaner.core.indexer import PhotoIndexer
        from photo_cleaner.duplicates.finder import DuplicateFinder
        from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
        from photo_cleaner.pipeline.scorer import GroupScorer
        import time
        
        progress = QProgressDialog(
            "Ordner wird analysiert...",
            "Abbrechen",
            0, 100,
            self
        )
        progress.setWindowTitle(t("image_analysis"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setMinimumWidth(460)
        progress.setMinimumHeight(140)
        progress.setStyleSheet(
            "QLabel { padding: 6px 8px; }"
            "QProgressBar { min-height: 18px; }"
        )
        QApplication.processEvents()
        
        start_time = time.time()
        
        try:
            from photo_cleaner.io.file_scanner import FileScanner
            from photo_cleaner.license import get_license_manager

            progress.setLabelText("Lizenz wird geprueft...")
            progress.setValue(5)
            QApplication.processEvents()

            total_files = FileScanner(self.input_folder).count_files()
            license_mgr = get_license_manager()
            allowed, reason = license_mgr.check_and_consume_free_images(total_files)
            if not allowed:
                progress.close()
                QMessageBox.warning(
                    self,
                    "Free-Limit erreicht",
                    reason or "Free-Limit erreicht. Bitte Upgrade auf PRO.",
                )
                return

            progress.setLabelText(f"Bilder werden gescannt...\nOrdner: {self.input_folder.name}")
            progress.setValue(10)
            QApplication.processEvents()
            
            if progress.wasCanceled():
                return
            
            # BUG #3 FIX: Create separate DB instance for indexer (thread-safe)
            from photo_cleaner.db.schema import Database
            indexer_db = Database(self.db_path)
            indexer_db.connect()  # Initialize connection
            indexer = PhotoIndexer(indexer_db, max_workers=None)
            progress.setLabelText("Bilder werden analysiert...\nBitte warten, dies kann einige Minuten dauern.")
            progress.setValue(20)
            QApplication.processEvents()
            
            index_start = time.time()
            index_stats = indexer.index_folder(self.input_folder, skip_existing=False)
            index_duration = time.time() - index_start
            
            progress.setValue(60)
            QApplication.processEvents()
            
            if progress.wasCanceled():
                return
            
            progress.setLabelText(t("searching_duplicates"))
            progress.setValue(65)
            QApplication.processEvents()
            finder = DuplicateFinder(self.db, phash_threshold=10)
            duplicate_groups = finder.build_groups()
            
            progress.setValue(80)
            QApplication.processEvents()
            
            if progress.wasCanceled():
                return
            
            # Geschätzte Restzeit für Bewertung
            processed = index_stats.get("processed", 0)
            if processed > 0:
                avg_time_per_image = index_duration / processed
                estimated_rating_time = int(avg_time_per_image * processed * 0.3)  # Rating ist schneller
                if estimated_rating_time > 5:
                    progress.setLabelText(f"Bilder werden bewertet...\nVerbleibende Zeit: ca. {estimated_rating_time} Sekunden")
                else:
                    progress.setLabelText("Bilder werden bewertet...")
            else:
                progress.setLabelText("Bilder werden bewertet...")
            
            progress.setValue(85)
            
            # BUG #1 FIX: Run rating in background thread to prevent UI freeze
            rating_thread = RatingWorkerThread(self.db_path, self.top_n, self.mtcnn_status)
            rating_completed = False
            rating_info = {"rated": False, "warn": False}
            
            def on_rating_progress(pct: int, status: str):
                if not progress.wasCanceled():
                    progress.setValue(pct)
                    progress.setLabelText(status)
            
            def on_rating_finished(info: dict):
                nonlocal rating_completed, rating_info
                rating_completed = True
                rating_info = info
            
            def on_rating_error(error_msg: str):
                nonlocal rating_completed, rating_info
                rating_completed = True
                rating_info = {"rated": False, "warn": True}
                logger.error(f"Rating error: {error_msg}")
            
            rating_thread.progress.connect(on_rating_progress)
            rating_thread.finished.connect(on_rating_finished)
            rating_thread.error.connect(on_rating_error)
            
            # Cancel check connection
            def check_cancel():
                if progress.wasCanceled():
                    rating_thread.cancel()
            
            rating_thread.start()
            
            # Wait for thread completion with event processing
            from PySide6.QtCore import QTimer
            cancel_timer = QTimer()
            cancel_timer.timeout.connect(check_cancel)
            cancel_timer.start(100)  # Check every 100ms
            
            rating_thread.wait()  # Block until thread completes
            cancel_timer.stop()
            
            if progress.wasCanceled():
                return
            
            progress.setLabelText("Analyse wird abgeschlossen...")
            progress.setValue(95)
            
            self.refresh_groups()
            
            progress.setValue(100)
            QApplication.processEvents()
            
            total_duration = int(time.time() - start_time)
            skipped = index_stats.get("skipped", 0)
            failed = index_stats.get("failed", 0)
            num_groups = len(duplicate_groups)
            
            result_msg = f"✓ Analyse abgeschlossen!\n\n"
            result_msg += f"Verarbeitete Bilder: {processed}\n"
            if skipped > 0:
                result_msg += f"Bereits bekannte Bilder: {skipped}\n"
            if failed > 0:
                result_msg += f"Nicht verarbeitbar: {failed}\n"
            result_msg += f"\nGefundene Gruppen ähnlicher Bilder: {num_groups}"
            result_msg += f"\nGesamtdauer: {total_duration} Sekunden"
            if rating_info.get("rated"):
                result_msg += "\n\n✓ Bewertung abgeschlossen: Bilder wurden automatisch eingeschätzt."
            if rating_info.get("warn"):
                result_msg += "\n⚠ Hinweis: Einige Bilder konnten nicht bewertet werden."
            
            QMessageBox.information(
                self,
                "Analyse erfolgreich",
                result_msg
            )
            
        except (OSError, IOError, ValueError, PermissionError, sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
            error_msg = f"Bei der Analyse ist ein Fehler aufgetreten:\n\n"
            error_msg += f"Fehlerdetails: {str(e)}\n\n"
            error_msg += f"Bitte stellen Sie sicher, dass:\n"
            error_msg += f"• Der Ordner gültige Bilddateien enthält\n"
            error_msg += f"• Sie Leserechte für den Ordner haben\n"
            error_msg += f"• Genügend Speicherplatz vorhanden ist"
            
            QMessageBox.critical(
                self,
                "Fehler bei der Analyse",
                error_msg
            )
        finally:
            progress.close()
    
    def _auto_rate_images(self, progress: Optional[QProgressDialog] = None) -> dict[str, bool]:
        """Auto-Bewertung aller Gruppen ausführen und Ergebnisse speichern."""
        logger.info("=== _auto_rate_images() STARTED ===")
        info = {"rated": False, "warn": False}
        try:
            logger.info("Querying groups from database...")
            cur = self.conn.execute(
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
                groups.setdefault(row["group_id"], []).append(Path(row["path"]))
            
            logger.info(f"Found {len(groups)} groups to rate")
            if not groups:
                logger.warning("No groups found - returning early")
                return info
            
            if progress:
                progress.setLabelText("Bilder werden bewertet...")
                QApplication.processEvents()
            
            logger.info(f"Creating QualityAnalyzer (use_face_mesh=True)...")
            QualityAnalyzer = _get_quality_analyzer()
            analyzer = QualityAnalyzer(use_face_mesh=True)
            logger.info(f"Creating GroupScorer (top_n={self.top_n})...")
            GroupScorer = _get_group_scorer()
            scorer = GroupScorer(top_n=self.top_n)
            quality_results: dict[str, list] = {}
            total_images = sum(len(v) for v in groups.values())
            logger.info(f"Total images to analyze: {total_images}")
            done = 0

            if progress:
                progress.setLabelText("Lade Modelle...")
                progress.setValue(86)
                QApplication.processEvents()
            analyzer.warmup()
            if progress:
                progress.setLabelText(f"Bilder werden bewertet... {done}/{total_images}")
                QApplication.processEvents()
            
            for group_id, paths in groups.items():
                logger.debug(f"Analyzing group {group_id} with {len(paths)} images...")
                
                # Update progress BEFORE analysis to keep UI responsive
                if progress:
                    pct = 85 + int(10 * (done / max(1, total_images)))
                    progress.setValue(min(94, pct))
                    progress.setLabelText(f"Bilder werden bewertet... {done}/{total_images}")
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        logger.info("Rating cancelled by user")
                        return info
                
                group_base_done = done
                def _progress_cb(local_done: int, local_total: int) -> None:
                    current_done = group_base_done + local_done
                    if progress:
                        pct = 85 + int(10 * (current_done / max(1, total_images)))
                        progress.setValue(min(94, pct))
                        progress.setLabelText(f"Bilder werden bewertet... {current_done}/{total_images}")
                        QApplication.processEvents()

                results = analyzer.analyze_batch(paths, progress_callback=_progress_cb)
                quality_results[group_id] = results
                done += len(paths)
                
                # Update progress AFTER analysis
                if progress:
                    pct = 85 + int(10 * (done / max(1, total_images)))
                    progress.setValue(min(94, pct))
                    QApplication.processEvents()
            
            logger.info("Scoring all groups...")
            group_scores = scorer.score_multiple_groups(quality_results)
            logger.info(f"Applying scores to database (action_id=AUTO_RATING)...")
            scorer.apply_scores_to_db(group_scores, self.files, action_id="AUTO_RATING")
            logger.info("Scores applied successfully")
            
            logger.info("Applying auto-selection for each group...")
            for group_id, results in quality_results.items():
                best_path, second_path, all_scores = scorer.auto_select_best_image(group_id, results)
                try:
                    # Reset recommendations for the group
                    self.conn.execute(
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
                    
                    # Store scores for all images (for UI sorting)
                    for item in all_scores:
                        # Handle both old format (3-tuple) and new format (4-tuple with components)
                        if len(item) == 4:
                            path, score, disqualified, components = item
                            self.conn.execute(
                                """
                                UPDATE files
                                SET quality_score = ?,
                                    sharpness_component = ?,
                                    lighting_component = ?,
                                    resolution_component = ?,
                                    face_quality_component = ?
                                WHERE path = ?
                                """,
                                (
                                    score,
                                    components.sharpness_score,
                                    components.lighting_score,
                                    components.resolution_score,
                                    components.face_quality_score,
                                    str(path)
                                ),
                            )
                        else:
                            # Fallback for old format
                            path, score, disqualified = item
                            self.conn.execute(
                                """
                                UPDATE files
                                SET quality_score = ?
                                WHERE path = ?
                                """,
                                (score, str(path)),
                            )
                    
                    if best_path:
                        self.conn.execute(
                            """
                            UPDATE files
                            SET is_recommended = 1, keeper_source = 'auto'
                            WHERE path = ?
                            """,
                            (str(best_path),),
                        )
                        logger.info(f"⭐ {best_path.name} als Empfohlung markiert")
                    
                    if second_path:
                        self.conn.execute(
                            """
                            UPDATE files
                            SET keeper_source = 'auto_secondary'
                            WHERE path = ?
                            """,
                            (str(second_path),),
                        )
                        logger.info(f"🥈 {second_path.name} als Zweitwahl markiert")
                    
                    self.conn.commit()
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                    logger.error(f"Fehler beim Markieren der Empfehlungen für {group_id}: {e}", exc_info=True)
                    info["warn"] = True
            
            logger.info(f"=== _auto_rate_images() COMPLETED === rated={info['rated']}, warn={info['warn']}")
            info["rated"] = True
            return info
        except (sqlite3.DatabaseError, sqlite3.OperationalError, ValueError, TypeError) as e:
            logger.error(f"=== _auto_rate_images() FAILED === {e}", exc_info=True)
            info["warn"] = True
            return info

    def _auto_rate_single_group(self, group_id: str, progress: Optional[QProgressDialog] = None) -> bool:
        """Auto-Bewertung nur für eine einzelne Gruppe ausführen."""
        try:
            cur = self.conn.execute(
                """
                SELECT f.path
                FROM duplicates d
                JOIN files f ON f.file_id = d.file_id
                WHERE d.group_id = ? AND f.is_deleted = 0
                ORDER BY f.path
                """,
                (group_id,),
            )
            paths = [Path(row["path"]) for row in cur.fetchall()]
            if not paths:
                return False

            if progress:
                progress.setLabelText("Gruppe wird neu bewertet...")
                progress.setValue(10)
                QApplication.processEvents()
                if progress.wasCanceled():
                    return False

            QualityAnalyzer = _get_quality_analyzer()
            analyzer = QualityAnalyzer(use_face_mesh=True)
            GroupScorer = _get_group_scorer()
            scorer = GroupScorer(top_n=self.top_n)
            results = analyzer.analyze_batch(paths)

            if progress:
                progress.setValue(70)
                QApplication.processEvents()
                if progress.wasCanceled():
                    return False

            group_scores = scorer.score_multiple_groups({group_id: results})
            scorer.apply_scores_to_db(group_scores, self.files, action_id="AUTO_RATING_MERGE")

            best_path, second_path, all_scores = scorer.auto_select_best_image(group_id, results)

            self.conn.execute(
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

            for item in all_scores:
                if len(item) == 4:
                    path, score, _, components = item
                    self.conn.execute(
                        """
                        UPDATE files
                        SET quality_score = ?,
                            sharpness_component = ?,
                            lighting_component = ?,
                            resolution_component = ?,
                            face_quality_component = ?
                        WHERE path = ?
                        """,
                        (
                            score,
                            components.sharpness_score,
                            components.lighting_score,
                            components.resolution_score,
                            components.face_quality_score,
                            str(path),
                        ),
                    )
                else:
                    path, score, _ = item
                    self.conn.execute(
                        """
                        UPDATE files
                        SET quality_score = ?
                        WHERE path = ?
                        """,
                        (score, str(path)),
                    )

            if best_path:
                self.conn.execute(
                    """
                    UPDATE files
                    SET is_recommended = 1, keeper_source = 'auto'
                    WHERE path = ?
                    """,
                    (str(best_path),),
                )

            if second_path:
                self.conn.execute(
                    """
                    UPDATE files
                    SET keeper_source = 'auto_secondary'
                    WHERE path = ?
                    """,
                    (str(second_path),),
                )

            self.conn.commit()

            if progress:
                progress.setValue(100)
                QApplication.processEvents()

            return True
        except (sqlite3.DatabaseError, sqlite3.OperationalError, ValueError) as e:
            logger.error(f"Fehler beim Neu-Bewerten der Gruppe {group_id}: {e}", exc_info=True)
            return False
    
    def _build_ui(self):
        """Build main UI - simplified without Hauptmenü frame."""
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # Main content splitter (no top bar, no main menu frame)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Group list
        splitter.addWidget(self._build_group_panel())
        
        # Center: Grid view
        splitter.addWidget(self._build_grid_panel())
        
        # Right: Quick actions panel
        splitter.addWidget(self._build_actions_panel())
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 2)
        
        layout.addWidget(splitter)
        
        # Bottom: Status bar
        layout.addWidget(self._build_status_bar())
        
        self.setCentralWidget(wrapper)
    
    def _build_menu(self):
        """Baut Menüleiste mit Language & Theme Switcher."""
        # Clear existing menu
        menubar = self.menuBar()
        menubar.clear()
        menubar.setMinimumHeight(32)
        menubar.setStyleSheet(
            "QMenuBar { padding: 2px 4px; }"
            "QMenuBar::item { padding: 6px 10px; margin: 0px 2px; }"
        )
        
        # Import button
        self.import_action = menubar.addAction(t("import"))
        self.import_action.triggered.connect(self._open_import_dialog)
        self.import_action.setToolTip(t("import_tooltip"))
        
        # Settings button
        self.settings_action = menubar.addAction(t("settings"))
        self.settings_action.triggered.connect(self._open_settings)
        self.settings_action.setToolTip(t("settings_tooltip"))
        
        # Add separator
        menubar.addSeparator()
        
        # Language dialog
        self.language_action = menubar.addAction(t("language"))
        self.language_action.triggered.connect(self._show_language_dialog)
        
        # Theme switcher
        theme_menu = menubar.addMenu(t("theme"))
        theme_menu.addAction(t("theme_dark")).triggered.connect(lambda: self._change_theme("dark"))
        theme_menu.addAction(t("theme_light")).triggered.connect(lambda: self._change_theme("light"))
        
        # License button
        self.license_action = menubar.addAction(t("license"))
        self.license_action.triggered.connect(self._show_license_dialog)
        self.license_action.setToolTip(t("license_tooltip"))
        
        # Help button
        self.help_action = menubar.addAction(t("help"))
        self.help_action.triggered.connect(self._show_help)
        self.help_action.setToolTip(t("help_tooltip"))
        
        # Quit via Ctrl+Q (no File menu)
        quit_shortcut = QShortcut(QKeySequence.Quit, self)
        quit_shortcut.activated.connect(self.close)
    
    def _show_license_dialog(self):
        """Öffnet Lizenz-Verwaltungs-Dialog."""
        try:
            from photo_cleaner.license import get_license_manager
            from photo_cleaner.ui.license_dialog import LicenseDialog
            
            license_mgr = get_license_manager()
            dialog = LicenseDialog(license_mgr, self)
            if dialog.exec():
                self._update_menu_state()
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.error(f"Failed to open license dialog: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Fehler",
                f"Lizenz-Dialog konnte nicht geöffnet werden:\n{e}"
            )

    def _show_language_dialog(self) -> None:
        """Open language selection dialog."""
        try:
            from photo_cleaner.ui.language_dialog import LanguageDialog

            dialog = LanguageDialog(self)
            if dialog.exec():
                self._build_menu()
                self._update_ui_language()
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.error(f"Failed to open language dialog: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Fehler",
                f"Sprach-Dialog konnte nicht geoeffnet werden:\n{e}",
            )
    
    def _show_about(self):
        """Zeigt Über-Dialog."""
        QMessageBox.about(
            self,
            "Über PhotoCleaner",
            "PhotoCleaner 0.5.5\n\n"
            "Intelligente Fotoverwaltung und -bereinigung.\n\n"
            "© 2024-2026 PhotoCleaner Team"
        )
    
    def _open_import_dialog(self) -> None:
        """Open folder dialog and start analysis directly."""
        dialog = FolderSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.input_folder = dialog.input_folder
            self.output_path = dialog.output_folder
            self.top_n = dialog.top_n
            logger.info("Import dialog completed: input=%s output=%s", self.input_folder, self.output_path)
            self._update_menu_state()
            # Starte Analyse DIREKT - kein extra Button-Klick nötig
            self._start_async_indexing()

    def _on_analyze_clicked(self) -> None:
        """Removed - Analysis starts automatically after import (no manual button anymore)."""
        pass

    def _update_menu_state(self):
        """Update menu button states based on data availability (Analyze button removed)."""
        # No analyze button to update anymore - analysis is automatic
        pass
    
    def _change_language(self, code: str) -> None:
        """Change application language and persist to settings."""
        try:
            from photo_cleaner.i18n import set_language, save_language_to_settings, get_available_languages as get_langs
            from photo_cleaner.config import AppConfig
            
            set_language(code)
            save_language_to_settings(AppConfig.get_user_data_dir() / "settings.json", code)
            
            # Rebuild menu with new translations
            self._build_menu()
            
            # Update all UI text elements with new language
            self._update_ui_language()
            
            # Show confirmation with language name
            langs = get_langs()
            lang_name = langs.get(code, code)
            self._show_status_message(f"Language changed to {lang_name}")
            logger.info(f"Language changed to {code}")
        except (KeyError, ValueError, TypeError, OSError) as e:
            logger.error(f"Error changing language: {e}", exc_info=True)
            QMessageBox.warning(self, t("error"), t("language_change_failed").format(error=e))
    
    def _update_ui_language(self):
        """Update all UI text elements after language change."""
        try:
            # Update group panel title
            if hasattr(self, 'group_list') and self.group_list.parentWidget():
                group_panel_layout = self.group_list.parentWidget().layout()
                if group_panel_layout and group_panel_layout.count() > 0:
                    title_widget = group_panel_layout.itemAt(0).widget()
                    if isinstance(title_widget, QLabel):
                        title_widget.setText(f"<h3>{t('duplicate_groups')}</h3>")
            
            # Update search placeholder
            if hasattr(self, 'search_box'):
                self.search_box.setPlaceholderText(t("search_placeholder"))
            
            # Update grid title if visible
            if hasattr(self, 'grid_title'):
                self.grid_title.setText(t("select_group_message"))
            
            # Update actions panel title
            if hasattr(self, 'keep_btn') and self.keep_btn.parentWidget():
                actions_panel = self.keep_btn.parentWidget()
                actions_layout = actions_panel.layout()
                if actions_layout and actions_layout.count() > 0:
                    # First item is the title
                    title_widget = actions_layout.itemAt(0).widget()
                    if isinstance(title_widget, QLabel):
                        title_widget.setText(f"<h3>{t('quick_actions')}</h3>")
                    # Second item is selection count label
                    if actions_layout.count() > 1:
                        selection_widget = actions_layout.itemAt(1).widget()
                        if isinstance(selection_widget, QLabel) and hasattr(self, 'selection_count_label'):
                            if self.selection_count_label == selection_widget:
                                self.selection_count_label.setText(f"<b>{t('no_selection')}</b>")
                    # Third item is "Multi-select" label
                    if actions_layout.count() > 2:
                        batch_widget = actions_layout.itemAt(2).widget()
                        if isinstance(batch_widget, QLabel):
                            batch_widget.setText(f"<b>{t('select_multiple')}</b>")
            
            # Update button texts in actions panel
            if hasattr(self, 'keep_btn'):
                self.keep_btn.setText(t("keep"))
            if hasattr(self, 'del_btn'):
                self.del_btn.setText(t("delete"))
            if hasattr(self, 'unsure_btn'):
                self.unsure_btn.setText(t("unsure"))
            if hasattr(self, 'needs_review_only_cb'):
                self.needs_review_only_cb.setText(t("needs_review_only"))
                self.needs_review_only_cb.setToolTip(t("needs_review_only_tooltip"))
            if hasattr(self, 'lock_btn'):
                self.lock_btn.setText(t("lock_unlock_button"))
            if hasattr(self, 'compare_btn'):
                self.compare_btn.setText(t("compare_two"))
            if hasattr(self, 'split_group_btn'):
                self.split_group_btn.setText(t("split_group"))
            if hasattr(self, 'undo_btn'):
                self.undo_btn.setText(t("undo_button"))
            
            # Update actions_on_selection label
            if hasattr(self, 'keep_btn') and self.keep_btn.parentWidget():
                actions_panel = self.keep_btn.parentWidget()
                actions_layout = actions_panel.layout()
                if actions_layout:
                    # Find "Actions on selection" label (it's before keep_btn)
                    for i in range(actions_layout.count()):
                        widget = actions_layout.itemAt(i).widget()
                        if isinstance(widget, QLabel):
                            text = widget.text()
                            if 'Aktionen' in text or 'Actions' in text:
                                widget.setText(t("actions_on_selection"))
                                break
            
            # Update status bar elements
            if hasattr(self, 'finalize_btn'):
                self.finalize_btn.setText(t("finalize_export"))
            
            # Update pagination label if needed (format stays same, just verify)
            if hasattr(self, 'pagination_label'):
                # Pagination format is dynamic, no translation needed
                pass
            
            # Refresh current group display if one is selected
            if self.current_group:
                # Reload the group to refresh all labels
                self.refresh_groups()
                # Re-select current group
                for i in range(self.group_list.count()):
                    item = self.group_list.item(i)
                    if item and item.data(Qt.UserRole) == self.current_group:
                        self.group_list.setCurrentItem(item)
                        break
            else:
                # Update empty state message
                if hasattr(self, 'grid_title'):
                    self.grid_title.setText(t("select_group_message"))
                    
            logger.info("UI language updated successfully")
        except (KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Error updating UI language: {e}", exc_info=True)
            import traceback
            logger.debug(traceback.format_exc())
    
    def _change_theme(self, theme: str) -> None:
        """Change application theme with immediate visual update (no restart needed).
        
        Updates:
        - Global theme state
        - Settings persistence
        - Application palette
        - All widget stylesheets
        - All child widgets recursively
        """
        try:
            from photo_cleaner.ui.theme_manager import ThemeManager
            
            # Use singleton ThemeManager for live switching
            manager = ThemeManager.instance()
            manager.change_theme(theme, main_window=self)  # type: ignore
            
            self._show_status_message(f"Theme switched to {theme.capitalize()}")
            logger.info(f"Theme changed to {theme}")
        except (RuntimeError, AttributeError, ValueError) as e:
            logger.error(f"Error changing theme: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, t("error"), t("theme_change_failed").format(error=e))
    
    def _on_theme_changed(self, theme: str) -> None:
        """Callback when theme changes - refresh all dynamic colors.
        
        This is called by ThemeManager when theme changes, ensuring all
        dynamically colored widgets (buttons, labels, cards) update immediately.
        """
        try:
            logger.info(f"Theme changed callback triggered: {theme}")
            
            # Refresh all thumbnail cards with new colors
            for card in self.thumbnail_cards:
                card._update_selection_style()
                # Update status label colors
                if hasattr(card, 'status_label'):
                    status_colors = get_status_colors()
                    status_color = status_colors.get(card.file_row.status.value, status_colors['UNDECIDED'])
                    card.status_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: {status_color};
                            color: white;
                            font-weight: bold;
                            padding: 4px;
                            border-radius: 4px;
                            font-size: 11px;
                        }}
                    """)
            
            # Refresh action buttons
            if hasattr(self, 'keep_btn'):
                status_colors = get_status_colors()
                self.keep_btn.setStyleSheet(_build_button_style(status_colors['KEEP'], padding="12px 14px", font_size=14))
            if hasattr(self, 'del_btn'):
                status_colors = get_status_colors()
                self.del_btn.setStyleSheet(_build_button_style(status_colors['DELETE'], padding="12px 14px", font_size=14))
            if hasattr(self, 'unsure_btn'):
                status_colors = get_status_colors()
                self.unsure_btn.setStyleSheet(_build_button_style(status_colors['UNSURE'], padding="12px 14px", font_size=14))
            if hasattr(self, 'merge_groups_btn'):
                self.merge_groups_btn.setStyleSheet(
                    _build_button_style(
                        get_semantic_colors()["info"],
                        hover_color=get_quality_colors()["high"],
                        padding="9px 12px",
                    )
                )
            if hasattr(self, 'compare_btn'):
                self.compare_btn.setStyleSheet(_build_button_style(get_semantic_colors()["warning"], padding="12px 14px"))
            if hasattr(self, 'split_group_btn'):
                self.split_group_btn.setStyleSheet(_build_button_style(get_semantic_colors()["info"], padding="10px 12px", font_size=12))
            if hasattr(self, 'lock_btn'):
                self.lock_btn.setStyleSheet(
                    _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'])
                )
            if hasattr(self, 'undo_btn'):
                self.undo_btn.setStyleSheet(
                    _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'])
                )
            if hasattr(self, 'finalize_btn'):
                self.finalize_btn.setStyleSheet(
                    _build_button_style(get_semantic_colors()['success'], padding="4px 12px", font_size=11, radius=6)
                )
            
            # Refresh status label (progress indicator)
            if hasattr(self, 'status_label'):
                self._update_progress()  # This will apply correct semantic colors

            # Refresh selection count label
            if hasattr(self, 'selection_count_label'):
                self._update_selection_count_style()
            
            # Refresh progress bar
            if hasattr(self, 'progress'):
                self._update_progress_bar_style()

            if hasattr(self, 'status_bar_panel'):
                colors = get_theme_colors()
                self.status_bar_panel.setStyleSheet(
                    f"background-color: {colors['window']}; border: 1px solid {colors['border']};"
                )

            if hasattr(self, 'actions_panel'):
                self._update_actions_panel_style()
            
            # Force repaint of entire window
            self.update()
            self.repaint()
            
            logger.info("Theme change complete - all widgets refreshed")
            
        except (RuntimeError, AttributeError, KeyError, ValueError) as e:
            logger.error(f"Error in theme change callback: {e}", exc_info=True)
    
    def _update_selection_count_style(self) -> None:
        """Update selection count label colors for current theme."""
        try:
            colors = get_theme_colors()
            if hasattr(self, 'selection_count_label'):
                self.selection_count_label.setStyleSheet(
                    f"padding: 8px; background-color: {colors['alternate_base']}; color: {colors['text']}; border-radius: 4px;"
                )
                logger.debug("Selection count style updated")
        except (KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Error updating selection count style: {e}", exc_info=True)

    def _update_actions_panel_style(self) -> None:
        try:
            colors = get_theme_colors()
            if hasattr(self, 'actions_panel'):
                self.actions_panel.setStyleSheet(
                    f"background-color: {colors['window']}; border: 1px solid {colors['border']}; border-radius: 8px;"
                )
        except (KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Error updating actions panel style: {e}", exc_info=True)
    
    def _update_progress_bar_style(self) -> None:
        """Update progress bar colors for current theme."""
        try:
            colors = get_theme_colors()
            success_color = get_semantic_colors()['success']
            if hasattr(self, 'progress'):
                self.progress.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid {colors['border']};
                        border-radius: 3px;
                        background-color: {colors['base']};
                        text-align: center;
                        padding: 0px;
                        font-size: 11px;
                        font-weight: bold;
                        color: {colors['text']};
                        qproperty-textVisible: true;
                        qproperty-alignment: AlignCenter;
                    }}
                    QProgressBar::chunk {{
                        background-color: {success_color};
                        border-radius: 2px;
                    }}
                """)
                logger.debug(f"Progress bar styled: chunk={success_color}")
        except (KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Error updating progress bar style: {e}", exc_info=True)

    
    def _open_settings(self) -> None:
        """Show comprehensive settings dialog."""
        try:
            from photo_cleaner.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(self, actions=self.actions)
            if dialog.exec():
                self._show_status_message("Einstellungen gespeichert")
                # Refresh UI with new settings
                self.refresh_groups()
        except ImportError:
            # Fallback: Show quality panel if settings dialog not available
            if hasattr(self, "quality_toggle_btn"):
                self.quality_toggle_btn.setChecked(True)
                self.quality_content.show()
                self._show_status_message("Qualitäts-Einstellungen geöffnet")
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.debug("Settings open failed: %s", e)
            QMessageBox.warning(self, t("error"), t("settings_open_failed").format(error=e))

    def _has_any_images(self) -> bool:
        try:
            cur = self.conn.execute("SELECT COUNT(*) FROM files WHERE is_deleted = 0")
            return (cur.fetchone() or [0])[0] > 0
        except (sqlite3.DatabaseError, sqlite3.OperationalError):
            logger.warning("Could not check for images", exc_info=True)
            return False

    def _refresh_mini_thumbnails(self) -> None:
        if not self.mini_thumb_list:
            return
        self.mini_thumb_list.clear()
        rows = []
        try:
            cur = self.conn.execute(
                "SELECT path FROM files WHERE is_deleted = 0 ORDER BY indexed_at DESC LIMIT 24"
            )
            rows = cur.fetchall()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.debug("Mini-thumbnail load failed: %s", e)
        if not rows and self.input_folder and self.input_folder.exists():
            try:
                fallback_paths = []
                for p in self.input_folder.rglob("*"):
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".heic", ".heif"}:
                        fallback_paths.append(p)
                        if len(fallback_paths) >= 24:
                            break
                rows = [(str(p),) for p in fallback_paths]
                if rows:
                    self.mini_status_label.setText(t("preview_from_input"))
            except (OSError, IOError) as e:
                logger.debug("Fallback mini-thumb scan failed: %s", e)
        if not rows:
            self.mini_status_label.setText(t("no_images_imported"))
            return
        self.mini_status_label.setText(t("images_loaded").format(count=len(rows)))
        for row in rows:
            p = Path(row[0])
            item = QListWidgetItem()
            item.setToolTip(p.name)
            item.setData(Qt.UserRole, str(p))
            try:
                thumb_path = get_thumbnail(p, (80, 80))
                pm = QPixmap(str(thumb_path)).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(pm))
            except (OSError, IOError):
                logger.warning(f"Could not load thumbnail for {p}", exc_info=True)
                item.setText(p.name)
            self.mini_thumb_list.addItem(item)


    def _show_help(self):
        """Show help dialog."""
        QMessageBox.information(
            self,
            t("help_dialog_title"),
            t("help_dialog_content")
        )

    def _on_eye_mode_changed(self, text: str):
        """Handle change of Eye Detection Mode UI and persist setting."""
        mapping = {
            "Schnell (Stufe 1)": 1,
            "Ausgewogen (Stufe 2)": 2,
            "Maximal (Stufe 3)": 3,
        }
        stage = mapping.get(text, 1)
        self._apply_eye_detection_mode(stage)
        # Persist setting
        self._user_settings["eye_detection_stage"] = stage
        self._save_user_settings()
        # Update availability banner
        self._update_eye_mode_status_banner()

    def _apply_eye_detection_mode(self, stage: int):
        """Apply eye detection stage by setting environment variable and informing user."""
        os.environ["PHOTOCLEANER_EYE_DETECTION_STAGE"] = str(stage)
        # Optional: show brief status
        stage_name = {1: "Fast (Haar)", 2: "Balanced (Haar + dlib)", 3: "Maximum (Haar + dlib + MediaPipe)"}.get(stage, "Fast")
        try:
            if hasattr(self, "status_label") and self.status_label is not None:
                self._show_status_message(f"Eye Detection Mode: {stage_name}")
            else:
                logger.info(f"Eye Detection Mode: {stage_name}")
        except (AttributeError, RuntimeError):
            logger.info(f"Eye Detection Mode: {stage_name}")

    def _settings_path(self) -> Path:
        """Return path to user settings JSON file."""
        return AppConfig.get_user_data_dir() / "settings.json"

    def _on_eye_detection_config_changed(self, config_dict: dict) -> None:
        """Handle live config changes from ConfigManager.
        
        When user saves preferences dialog:
        1. Environment variables are updated
        2. This signal is emitted
        3. UI combo is synced
        4. New analyzers will use updated env vars
        """
        logger.debug(f"Eye detection config changed: {config_dict}")
        # Update UI combo to reflect new mode
        mode = config_dict.get("mode", 1)
        idx = {1: 0, 2: 1, 3: 2}.get(mode, 0)
        # Temporarily disconnect signal to avoid re-triggering
        try:
            self.eye_mode_combo.currentTextChanged.disconnect(self._on_eye_mode_changed)
            self.eye_mode_combo.setCurrentIndex(idx)
            self.eye_mode_combo.currentTextChanged.connect(self._on_eye_mode_changed)
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"Failed to sync combo: {e}", exc_info=True)
        
        # Update status banner
        self._update_eye_mode_status_banner()
        
        # Show confirmation to user
        self._show_status_message("Eye Detection preferences updated. New images will use the new settings.")

    def _show_eye_detection_preferences(self) -> None:
        """Open the Eye Detection Preferences Dialog."""
        QMessageBox.information(
            self,
            "Augenerkennung",
            "Augenerkennung wird automatisch konfiguriert und benötigt keine Benutzeroptionen.",
        )

    def _load_user_settings(self) -> dict:
        """Load user settings JSON (safe)."""
        try:
            path = self._settings_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to load settings: {e}")
        return {}

    def _save_user_settings(self) -> None:
        """Persist user settings JSON (safe)."""
        try:
            path = self._settings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._user_settings, f, ensure_ascii=False, indent=2)
        except (OSError, IOError, ValueError) as e:
            logger.debug(f"Failed to save settings: {e}", exc_info=True)

    # ==================== Eye Detection Availability ====================
    def _get_dlib_predictor_path(self) -> Optional[Path]:
        """Resolve dlib predictor path from settings/env or default locations."""
        # 1) User setting
        p = self._user_settings.get("dlib_predictor_path")
        if p:
            path = Path(p)
            if path.exists():
                return path
        # 2) Environment variable
        p = os.environ.get("PHOTOCLEANER_DLIB_PREDICTOR_PATH")
        if p:
            path = Path(p)
            if path.exists():
                return path
        # 3) Default under user data dir
        default = AppConfig.get_user_data_dir() / "models" / "shape_predictor_68_face_landmarks.dat"
        if default.exists():
            return default
        return None

    def check_eye_detection_availability(self) -> dict:
        """
        Check availability of Eye Detection Stages and return status map.
        
        Now uses DependencyManager for accurate detection.
        
        Returns:
            Dict keyed by stage number (1, 2, 3) with:
            - available: bool
            - message: str (user-friendly German message)
            - fix: str (optional, "install" if fixable)
        """
        from photo_cleaner.dependency_manager import get_dependency_manager
        
        manager = get_dependency_manager()
        available_stages = manager.get_available_stages()
        
        status = {}
        
        # Stage 1: Haar Cascades (always available with OpenCV)
        if 1 in available_stages:
            status[1] = {"available": True, "message": "Bereit"}
        else:
            status[1] = {"available": False, "message": "OpenCV nicht installiert", "fix": "install"}
        
        # Stage 2: dlib + predictor
        if 2 in available_stages:
            # dlib is installed, check predictor
            pred_path = self._get_dlib_predictor_path()
            if pred_path and Path(pred_path).exists():
                status[2] = {"available": True, "message": "Bereit"}
            else:
                status[2] = {"available": False, "message": "dlib Predictor fehlt", "fix": "download"}
        else:
            # dlib not installed
            if manager.dependencies["dlib"].requires_build_tools and not manager.system_info.has_build_tools:
                status[2] = {"available": False, "message": "dlib nicht installiert (Build Tools fehlen)", "fix": "install"}
            else:
                status[2] = {"available": False, "message": "dlib nicht installiert", "fix": "install"}
        
        # Stage 3: MediaPipe
        if 3 in available_stages:
            status[3] = {"available": True, "message": "Bereit"}
        else:
            status[3] = {"available": False, "message": "MediaPipe nicht installiert", "fix": "install"}
        
        return status

    def _update_eye_mode_status_banner(self) -> None:
        """Update inline status banner and fix button visibility based on selected stage."""
        if not hasattr(self, "eye_mode_combo"):
            return
        mapping = {"Schnell (Stufe 1)": 1, "Ausgewogen (Stufe 2)": 2, "Maximal (Stufe 3)": 3}
        stage = mapping.get(self.eye_mode_combo.currentText(), 1)
        status = self.check_eye_detection_availability().get(stage, {"available": True, "message": "Bereit"})

        if status.get("available"):
            self.eye_mode_status_label.setText("✓ Bereit")
            success_color = get_semantic_colors()["success"]
            self.eye_mode_status_label.setStyleSheet(f"padding: 4px 8px; border-radius: 6px; font-size: 12px; background-color: {success_color}; color: white;")
            self.eye_mode_fix_btn.hide()
        else:
            msg = status.get("message", "Nicht verfügbar")
            self.eye_mode_status_label.setText(f"⚠ {msg}")
            error_color = get_semantic_colors()["error"]
            self.eye_mode_status_label.setStyleSheet(f"padding: 4px 8px; border-radius: 6px; font-size: 12px; background-color: {error_color}; color: white;")
            # Show fix button for actionable fixes
            fix = status.get("fix")
            if fix in ("download", "install"):
                self.eye_mode_fix_btn.show()
            else:
                self.eye_mode_fix_btn.hide()

    def _eye_mode_fix_action(self) -> None:
        """
        Handle fix actions for the current stage.
        
        Opens the Installation Dialog to install missing dependencies (MediaPipe, dlib).
        """
        from photo_cleaner.ui.installation_dialog import InstallationDialog
        
        dialog = InstallationDialog(self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Installation erfolgt, aktualisiere Status
            self._update_eye_mode_status_banner()
            
            # Zeige Erfolgs-Nachricht mit Hinweis zum Neuladen
            QMessageBox.information(
                self,
                "Installation erfolgreich",
                "Die erweiterten Funktionen wurden installiert.\n\n"
                "Die Änderungen werden bei der nächsten Analyse aktiv."
            )

    def _choose_dlib_predictor_path(self) -> None:
        """Open file dialog to choose dlib predictor and persist path."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Wähle dlib Predictor Datei",
                str(AppConfig.get_user_data_dir()),
                "dlib Predictor (*.dat);;Alle Dateien (*.*)"
            )
            if file_path:
                path = Path(file_path)
                self._user_settings["dlib_predictor_path"] = str(path)
                os.environ["PHOTOCLEANER_DLIB_PREDICTOR_PATH"] = str(path)
                self._save_user_settings()
                QMessageBox.information(self, t("predictor_set_title"), t("predictor_set_message").format(path=path))
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Failed to set dlib predictor: {e}", exc_info=True)
            QMessageBox.warning(self, t("error"), t("predictor_set_failed").format(error=e))
    
    def _build_quality_settings_panel(self) -> QWidget:
        """Erstelle ausklappbares Qualitäts-Einstellungen Panel."""
        from photo_cleaner.config_update_system import get_config_update_system, ChangeType
        from photo_cleaner.preset_manager import get_preset_manager
        from datetime import datetime
        
        panel = QWidget()
        panel.setMaximumHeight(300)  # Limit height
        main_layout = QVBoxLayout(panel)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header / Toggle button
        header_layout = QHBoxLayout()
        self.quality_toggle_btn = QPushButton(f"🔽 {t('quality_settings').upper()}")
        self.quality_toggle_btn.setCheckable(True)
        self.quality_toggle_btn.setChecked(False)
        bg = get_label_background_color()
        fg = "white" if get_theme() == "dark" else "black"
        colors = get_theme_colors()
        border = colors['border']
        card_colors = get_card_colors()
        hover_bg = card_colors["bg_hover"]
        bg_info = get_semantic_colors()["info"]
        quality_high = get_quality_colors()["high"]
        self.quality_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background-color: {bg_info};
                border: 1px solid {quality_high};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """)
        header_layout.addWidget(self.quality_toggle_btn)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Collapsible content area
        self.quality_content = QWidget()
        self.quality_content.hide()  # Start hidden
        content_layout = QVBoxLayout(self.quality_content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(12, 8, 12, 8)
        
        # Get system instances
        self.config_system = get_config_update_system()
        self.preset_manager = get_preset_manager()
        
        # === Eye Detection Subsection ===
        eye_section = self._create_settings_section("👁 Augenerkennung")
        eye_layout = eye_section.layout()
        
        # Eye Detection Threshold slider
        eye_layout.addLayout(self._create_slider_control(
            label="Erkennungs-Schwellenwert:",
            key="eye_detection_threshold",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.25
        ))
        
        # Face Confidence slider
        eye_layout.addLayout(self._create_slider_control(
            label="Gesichts-Konfidenz:",
            key="face_confidence_threshold",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.7
        ))
        
        # Min Eye Size spinner
        min_eye_layout = QHBoxLayout()
        min_eye_label = QLabel(t("min_eye_size"))
        self.min_eye_spin = QSpinBox()
        self.min_eye_spin.setRange(5, 500)
        self.min_eye_spin.setValue(10)
        self.min_eye_spin.setMinimumWidth(100)
        self.min_eye_spin.valueChanged.connect(
            lambda v: self.config_system.request_change("min_eye_size", v, ChangeType.SLIDER_CHANGE)
        )
        min_eye_layout.addWidget(min_eye_label)
        min_eye_layout.addWidget(self.min_eye_spin)
        min_eye_layout.addStretch()
        eye_layout.addLayout(min_eye_layout)
        
        content_layout.addWidget(eye_section)
        
        # === Image Quality Subsection ===
        quality_section = self._create_settings_section("🎨 Bildqualität")
        quality_layout = quality_section.layout()
        
        quality_layout.addLayout(self._create_slider_control(
            label="Unschärfe-Gewichtung:",
            key="blur_weight",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.4
        ))
        
        quality_layout.addLayout(self._create_slider_control(
            label="Belichtungs-Gewichtung:",
            key="exposure_weight",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.3
        ))
        
        quality_layout.addLayout(self._create_slider_control(
            label="Kontrast-Gewichtung:",
            key="contrast_weight",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.2
        ))
        
        quality_layout.addLayout(self._create_slider_control(
            label="Rausch-Gewichtung:",
            key="noise_weight",
            min_val=0.0, max_val=1.0, step=0.05,
            default=0.1
        ))
        
        content_layout.addWidget(quality_section)
        
        # === Detection Options Subsection ===
        detection_section = self._create_settings_section("🔍 Erkennungsoptionen")
        detection_layout = detection_section.layout()
        
        self.detect_closed_eyes_cb = self._create_checkbox_control(
            label="Geschlossene Augen erkennen",
            key="detect_closed_eyes",
            default=True
        )
        detection_layout.addLayout(self.detect_closed_eyes_cb)
        
        self.detect_blurry_cb = self._create_checkbox_control(
            label="Unscharfe Bilder erkennen",
            key="detect_blurry",
            default=True
        )
        detection_layout.addLayout(self.detect_blurry_cb)
        
        self.detect_underexposed_cb = self._create_checkbox_control(
            label="Unterbelichtete Bilder erkennen",
            key="detect_underexposed",
            default=True
        )
        detection_layout.addLayout(self.detect_underexposed_cb)
        
        self.detect_overexposed_cb = self._create_checkbox_control(
            label="Überbelichtete Bilder erkennen",
            key="detect_overexposed",
            default=True
        )
        detection_layout.addLayout(self.detect_overexposed_cb)
        
        self.detect_redeye_cb = self._create_checkbox_control(
            label="Rote-Augen-Effekt erkennen",
            key="detect_redeye",
            default=True
        )
        detection_layout.addLayout(self.detect_redeye_cb)
        
        content_layout.addWidget(detection_section)
        
        # === Preset System Subsection ===
        preset_section = self._create_settings_section("💾 Voreinstellungen")
        preset_layout = preset_section.layout()
        
        preset_combo_layout = QHBoxLayout()
        preset_combo_layout.addWidget(QLabel("Voreinstellung:"))
        self.preset_combo = QComboBox()
        
        # Load preset names
        presets = self.preset_manager.list_presets()
        self.preset_combo.addItems(presets)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self.preset_combo.setMinimumWidth(150)
        preset_combo_layout.addWidget(self.preset_combo)
        preset_combo_layout.addStretch()
        preset_layout.addLayout(preset_combo_layout)
        
        # Preset buttons
        preset_btn_layout = QHBoxLayout()
        
        self.save_preset_btn = QPushButton("💾 Speichern")
        self.save_preset_btn.setFixedWidth(120)
        self.save_preset_btn.clicked.connect(self._save_current_preset)
        preset_btn_layout.addWidget(self.save_preset_btn)
        
        self.delete_preset_btn = QPushButton(t("delete_button"))
        self.delete_preset_btn.setFixedWidth(120)
        self.delete_preset_btn.clicked.connect(self._delete_current_preset)
        preset_btn_layout.addWidget(self.delete_preset_btn)
        
        self.reset_presets_btn = QPushButton(t("reset_icon"))
        self.reset_presets_btn.setFixedWidth(120)
        self.reset_presets_btn.clicked.connect(self._reset_presets)
        preset_btn_layout.addWidget(self.reset_presets_btn)
        
        preset_btn_layout.addStretch()
        preset_layout.addLayout(preset_btn_layout)
        
        content_layout.addWidget(preset_section)
        
        # Status label
        self.quality_status_label = QLabel("")
        link_color = get_semantic_colors()["link"]
        self.quality_status_label.setStyleSheet(f"""
            color: {link_color};
            font-size: 11px;
            padding: 4px 8px;
        """)
        content_layout.addWidget(self.quality_status_label)
        
        content_layout.addStretch()
        
        main_layout.addWidget(self.quality_content)
        
        # Connect toggle button
        self.quality_toggle_btn.toggled.connect(self._toggle_quality_panel)
        
        # Connect config system callbacks
        self.config_system.register_on_change_applied(self._on_config_applied)
        self.config_system.register_on_validation_error(self._on_config_validation_error)
        
        return panel
    
    def _create_settings_section(self, title: str) -> QGroupBox:
        """Erstelle eine Einstellungs-Sektion."""
        group = QGroupBox(title)
        colors = get_theme_colors()
        text_color = colors['text']
        border_color = colors['border']
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        return group
    
    def _create_slider_control(self, label: str, key: str, min_val: float, 
                               max_val: float, step: float, default: float,
                               change_type=None) -> QHBoxLayout:
        """Erstelle einen Slider-Control für Werte zwischen 0-1."""
        from photo_cleaner.config_update_system import ChangeType as CT
        
        layout = QHBoxLayout()
        
        # Label
        label_widget = QLabel(label)
        label_widget.setMinimumWidth(150)
        layout.addWidget(label_widget)
        
        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(min_val * 100), int(max_val * 100))
        slider.setValue(int(default * 100))
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(10)
        slider.setMinimumWidth(200)
        
        # Value label
        value_label = QLabel(f"{default:.2f}")
        value_label.setMinimumWidth(40)
        value_label.setAlignment(Qt.AlignRight)
        
        ctype = change_type if change_type else CT.SLIDER_CHANGE
        
        def on_slider_change(value):
            normalized = value / 100.0
            value_label.setText(f"{normalized:.2f}")
            self.config_system.request_change(key, normalized, ctype)
        
        slider.valueChanged.connect(on_slider_change)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        layout.addStretch()
        
        # Store slider for later updates
        setattr(self, f"slider_{key}", slider)
        setattr(self, f"label_{key}", value_label)
        
        return layout
    
    def _create_checkbox_control(self, label: str, key: str, default: bool,
                                 change_type=None) -> QHBoxLayout:
        """Erstelle einen Checkbox-Control."""
        from photo_cleaner.config_update_system import ChangeType as CT
        
        layout = QHBoxLayout()
        
        checkbox = QCheckBox(label)
        checkbox.setChecked(default)
        checkbox.setMinimumWidth(200)
        
        ctype = change_type if change_type else CT.CHECKBOX_CHANGE
        
        def on_checkbox_change(checked):
            self.config_system.request_change(key, checked, ctype)
        
        checkbox.stateChanged.connect(on_checkbox_change)
        layout.addWidget(checkbox)
        layout.addStretch()
        
        # Store checkbox for later updates
        setattr(self, f"cb_{key}", checkbox)
        
        return layout
    
    def _toggle_quality_panel(self, checked: bool):
        """Schalte Quality Settings Panel um."""
        if checked:
            self.quality_content.show()
            self.quality_toggle_btn.setText(f"🔼 {t('quality_settings').upper()}")
        else:
            self.quality_content.hide()
            self.quality_toggle_btn.setText(f"🔽 {t('quality_settings').upper()}")
    
    def _on_preset_selected(self, preset_name: str):
        """Lade ausgewähltes Preset."""
        if not preset_name:
            return
        
        preset = self.preset_manager.get_preset(preset_name)
        if preset:
            self.config_system.load_preset(preset)
            self._update_ui_from_config()
            self.quality_status_label.setText(f"✓ Voreinstellung '{preset_name}' geladen")
    
    def _save_current_preset(self):
        """Speichere aktuelle Einstellungen als Preset."""
        from datetime import datetime
        from photo_cleaner.preset_manager import QualityPreset
        
        new_name, ok = QInputDialog.getText(
            self,
            "Voreinstellung speichern",
            "Name für neue Voreinstellung:",
            QLineEdit.Normal,
            "Mein Preset"
        )
        
        if not ok or not new_name:
            return
        
        # Get current config
        current_config = self.config_system.get_config()
        
        # Create preset from current config
        from photo_cleaner.preset_manager import QualityPreset
        preset = QualityPreset(
            name=new_name,
            description=f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            eye_detection_mode=current_config.get("eye_detection_mode", 2),
            eye_detection_threshold=current_config.get("eye_detection_threshold", 0.25),
            face_confidence_threshold=current_config.get("face_confidence_threshold", 0.7),
            min_eye_size=current_config.get("min_eye_size", 10),
            blur_weight=current_config.get("blur_weight", 0.4),
            exposure_weight=current_config.get("exposure_weight", 0.3),
            contrast_weight=current_config.get("contrast_weight", 0.2),
            noise_weight=current_config.get("noise_weight", 0.1),
            detect_closed_eyes=current_config.get("detect_closed_eyes", True),
            detect_blurry=current_config.get("detect_blurry", True),
            detect_underexposed=current_config.get("detect_underexposed", True),
            detect_overexposed=current_config.get("detect_overexposed", True),
            detect_redeye=current_config.get("detect_redeye", True),
        )
        
        success, error = self.preset_manager.create_preset(new_name, preset)
        
        if success:
            # Refresh preset combo
            self.preset_combo.blockSignals(True)
            presets = self.preset_manager.list_presets()
            self.preset_combo.clear()
            self.preset_combo.addItems(presets)
            self.preset_combo.setCurrentText(new_name)
            self.preset_combo.blockSignals(False)
            
            self.quality_status_label.setText(f"✓ Voreinstellung '{new_name}' gespeichert")
        else:
            QMessageBox.warning(self, t("error"), t("preset_save_failed").format(error=error))
    
    def _delete_current_preset(self):
        """Lösche aktuelles Preset."""
        preset_name = self.preset_combo.currentText()
        
        if preset_name in self.preset_manager.BUILTIN_PRESETS:
            QMessageBox.information(self, t("not_possible"), 
                                   f"Kann vordefiniertes Preset '{preset_name}' nicht löschen.")
            return
        
        reply = QMessageBox.question(
            self,
            "Bestätigung",
            f"Soll die Voreinstellung '{preset_name}' wirklich gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, error = self.preset_manager.delete_preset(preset_name)
            if success:
                # Refresh preset combo
                self.preset_combo.blockSignals(True)
                presets = self.preset_manager.list_presets()
                self.preset_combo.clear()
                self.preset_combo.addItems(presets)
                self.preset_combo.setCurrentIndex(0)
                self.preset_combo.blockSignals(False)
                
                self.quality_status_label.setText(f"✓ Voreinstellung gelöscht")
            else:
                QMessageBox.warning(self, t("error"), t("preset_delete_failed").format(error=error))
    
    def _reset_presets(self):
        """Setze alle Presets auf Standard zurück."""
        reply = QMessageBox.question(
            self,
            "Bestätigung",
            "Sollen alle benutzerdefinierten Voreinstellungen wirklich gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.preset_manager.reset_to_defaults()
            
            # Refresh preset combo
            self.preset_combo.blockSignals(True)
            presets = self.preset_manager.list_presets()
            self.preset_combo.clear()
            self.preset_combo.addItems(presets)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)
            
            self.quality_status_label.setText("✓ Voreinstellungen zurückgesetzt")
    
    def _on_config_applied(self, changes):
        """Callback wenn Konfigurationsänderungen angewendet wurden."""
        self._update_ui_from_config()
        self.quality_status_label.setText("✓ Einstellungen aktualisiert")
    
    def _on_config_validation_error(self, key, error_msg):
        """Callback bei Validierungsfehler."""
        self.quality_status_label.setText(f"✗ Fehler in '{key}': {error_msg}")
    
    def _update_ui_from_config(self):
        """Aktualisiere UI-Controls von aktueller Konfiguration."""
        config = self.config_system.get_config()
        
        # Update sliders
        sliders_to_update = [
            ("eye_detection_threshold", "slider_eye_detection_threshold"),
            ("face_confidence_threshold", "slider_face_confidence_threshold"),
            ("blur_weight", "slider_blur_weight"),
            ("exposure_weight", "slider_exposure_weight"),
            ("contrast_weight", "slider_contrast_weight"),
            ("noise_weight", "slider_noise_weight"),
        ]
        
        for config_key, slider_attr in sliders_to_update:
            if hasattr(self, slider_attr):
                slider = getattr(self, slider_attr)
                value = config.get(config_key)
                if value is not None:
                    slider.blockSignals(True)
                    slider.setValue(int(value * 100))
                    slider.blockSignals(False)
        
        # Update min_eye_size
        if self.min_eye_spin:
            self.min_eye_spin.blockSignals(True)
            self.min_eye_spin.setValue(config.get("min_eye_size", 10))
            self.min_eye_spin.blockSignals(False)
        
        # Update checkboxes
        checkboxes_to_update = [
            ("detect_closed_eyes", "cb_detect_closed_eyes"),
            ("detect_blurry", "cb_detect_blurry"),
            ("detect_underexposed", "cb_detect_underexposed"),
            ("detect_overexposed", "cb_detect_overexposed"),
            ("detect_redeye", "cb_detect_redeye"),
        ]
        
        for config_key, cb_attr in checkboxes_to_update:
            if hasattr(self, cb_attr):
                cb = getattr(self, cb_attr)
                value = config.get(config_key)
                if value is not None:
                    cb.blockSignals(True)
                    cb.setChecked(value)
                    cb.blockSignals(False)
    
    def _build_group_panel(self) -> QWidget:
        """Erstelle Gruppenauswahlpanel."""
        panel = QWidget()
        panel.setMaximumWidth(350)
        panel.setStyleSheet(_build_surface_style())
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        
        title = QLabel(f"<h3>{t('duplicate_groups')}</h3>")
        layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(t("search_placeholder"))
        self.search_box.setStyleSheet(_build_input_style())
        self.search_box.textChanged.connect(self._apply_group_filter)
        layout.addWidget(self.search_box)

        self.needs_review_only_cb = QCheckBox(t("needs_review_only"))
        self.needs_review_only_cb.setToolTip(t("needs_review_only_tooltip"))
        self.needs_review_only_cb.stateChanged.connect(self._apply_group_filter)
        layout.addWidget(self.needs_review_only_cb)

        self.needs_review_counter_label = QLabel(t("needs_review_counter").format(visible=0, total=0))
        self.needs_review_counter_label.setStyleSheet(
            f"padding: 6px 8px; font-size: 11px; background-color: {get_theme_colors()['alternate_base']}; border-radius: 8px;"
        )
        layout.addWidget(self.needs_review_counter_label)
        
        self.group_list = QListWidget()
        self.group_list.itemSelectionChanged.connect(self._on_group_selected)
        self.group_list.setAlternatingRowColors(True)
        self.group_list.setIconSize(QSize(48, 48))
        # NEW Feature 3: Multi-select for group merging
        self.group_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # FIX (Feb 22, 2026): Async thumbnail loading with proper threading
        self._group_thumb_cache = SmartThumbnailCache(max_size_mb=100)
        self._group_thumb_loader = ThumbnailLoader(self._group_thumb_cache, thumb_size=(48, 48))
        self._group_thumb_loader.thumbnail_loaded.connect(self._on_group_thumb_loaded)
        # ✅ CRITICAL FIX: Start paused (only resume in _finish_post_indexing after rating complete)
        self._group_thumb_loader.start()
        logger.info("[UI] ThumbnailLoader started for group list (paused, will resume after rating)")
        # Use palette-driven colors to avoid dark boxes on light themes
        colors = get_theme_colors()
        self.group_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {colors['border']};
                border-radius: 10px;
                background-color: {colors['base']};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 10px;
                margin: 3px 0;
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                border: 2px solid {get_semantic_colors()['info']};
            }}
        """)
        layout.addWidget(self.group_list)
        
        # NEW Feature 3: Merge Groups Button
        merge_btn_layout = QHBoxLayout()
        self.merge_groups_btn = QPushButton(t("merge_groups"))
        self.merge_groups_btn.setEnabled(False)  # Enabled only when 2+ groups selected
        self.merge_groups_btn.clicked.connect(self._merge_selected_groups)
        self.merge_groups_btn.setStyleSheet(
            _build_button_style(
                get_semantic_colors()["info"],
                hover_color=get_quality_colors()["high"],
                padding="9px 12px",
            )
        )
        merge_btn_layout.addWidget(self.merge_groups_btn)
        layout.addLayout(merge_btn_layout)
        
        return panel

    def _setup_grid_thumbnail_loader(self) -> None:
        """Initialize async thumbnail loader for grid cards."""
        if self._grid_thumb_loader:
            return
        self._grid_thumb_cache = SmartThumbnailCache(max_size_mb=200)
        self._grid_thumb_loader = ThumbnailLoader(self._grid_thumb_cache, thumb_size=(160, 160))
        self._grid_thumb_loader.thumbnail_loaded.connect(self._on_grid_thumb_loaded)
        # ✅ CRITICAL FIX: Start paused (only resume in _finish_post_indexing after rating complete)
        self._grid_thumb_loader.start()
        logger.info("[UI] ThumbnailLoader started for grid cards (paused, will resume after rating)")
    
    def _build_grid_panel(self) -> QWidget:
        """Erstelle Hauptansicht mit Bild-Vorschau und Grid."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Titel
        self.grid_title = QLabel(t("select_group_message"))
        self.grid_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.grid_title)

        # Pagination controls (P6.4 quick-fix)
        pagination_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("←")
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.next_page_btn = QPushButton("→")
        self.next_page_btn.clicked.connect(self._next_page)
        self.pagination_label = QLabel("1/1")
        self.prev_page_btn.setEnabled(False)
        self.next_page_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.pagination_label)
        pagination_layout.addWidget(self.next_page_btn)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Scroll area für Grid
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setFrameShape(QFrame.NoFrame)
        colors = get_theme_colors()
        grid_bg = colors['window']
        grid_border = colors['border']
        self.grid_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {grid_bg};
                border: 2px solid {grid_border};
                border-radius: 8px;
            }}
        """)
        
        # Grid container
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        
        self.grid_scroll.setWidget(self.grid_container)
        layout.addWidget(self.grid_scroll)
        
        return panel
    
    def _build_actions_panel(self) -> QWidget:
        """Erstelle Schnellaktionen-Panel."""
        panel = QWidget()
        self.actions_panel = panel
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        self._update_actions_panel_style()
        
        title = QLabel(f"<h3>{t('quick_actions')}</h3>")
        layout.addWidget(title)
        
        # Auswahl-Info - store for theme updates
        self.selection_count_label = QLabel(f"<b>{t('no_selection')}</b>")
        self._update_selection_count_style()
        layout.addWidget(self.selection_count_label)
        
        # Batch-Auswahl-Buttons
        batch_group = QLabel(f"<b>{t('select_multiple')}</b>")
        layout.addWidget(batch_group)
        
        select_all_btn = QPushButton(t('select_all'))
        select_all_btn.setStyleSheet(
            _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'], padding="8px 10px", font_size=12)
        )
        select_all_btn.clicked.connect(self._select_all)
        select_all_btn.hide()
        layout.addWidget(select_all_btn)
        
        clear_selection_btn = QPushButton(t("clear_selection"))
        clear_selection_btn.setStyleSheet(
            _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'], padding="8px 10px", font_size=12)
        )
        clear_selection_btn.clicked.connect(self._clear_selection)
        clear_selection_btn.hide()
        layout.addWidget(clear_selection_btn)
        
        layout.addSpacing(10)
        
        # Vergleichs-Button (aktiviert wenn 2 ausgewählt)
        self.compare_btn = QPushButton(t("compare_two"))
        self.compare_btn.setEnabled(False)
        self.compare_btn.setStyleSheet(
            _build_button_style(get_semantic_colors()["warning"], padding="12px 14px")
        )
        self.compare_btn.clicked.connect(self._open_comparison)
        self.compare_btn.hide()
        layout.addWidget(self.compare_btn)

        self.split_group_btn = QPushButton(t("split_group"))
        self.split_group_btn.setEnabled(False)
        self.split_group_btn.setStyleSheet(
            _build_button_style(get_semantic_colors()["info"], padding="10px 12px", font_size=12)
        )
        self.split_group_btn.clicked.connect(self._split_selected_from_group)
        self.split_group_btn.hide()
        layout.addWidget(self.split_group_btn)
        
        layout.addSpacing(10)
        
        # Aktions-Buttons
        actions_label = QLabel(t("actions_on_selection"))
        layout.addWidget(actions_label)
        
        status_colors = get_status_colors()
        
        self.keep_btn = QPushButton(t("keep"))
        self.keep_btn.setStyleSheet(_build_button_style(status_colors['KEEP'], padding="12px 14px", font_size=14))
        self.keep_btn.clicked.connect(lambda: self._apply_status_to_selection(FileStatus.KEEP))
        layout.addWidget(self.keep_btn)
        
        self.del_btn = QPushButton(t("delete"))
        self.del_btn.setStyleSheet(_build_button_style(status_colors['DELETE'], padding="12px 14px", font_size=14))
        self.del_btn.clicked.connect(lambda: self._apply_status_to_selection(FileStatus.DELETE))
        layout.addWidget(self.del_btn)
        
        self.unsure_btn = QPushButton(t("unsure"))
        self.unsure_btn.setStyleSheet(_build_button_style(status_colors['UNSURE'], padding="12px 14px", font_size=14))
        self.unsure_btn.clicked.connect(lambda: self._apply_status_to_selection(FileStatus.UNSURE))
        layout.addWidget(self.unsure_btn)
        
        layout.addSpacing(20)
        
        self.lock_btn = QPushButton(t("lock_unlock_button"))
        self.lock_btn.setStyleSheet(
            _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'])
        )
        self.lock_btn.clicked.connect(self._toggle_lock_selection)
        self.lock_btn.hide()
        layout.addWidget(self.lock_btn)
        
        self.undo_btn = QPushButton(t("undo_button"))
        self.undo_btn.setStyleSheet(
            _build_button_style(get_theme_colors()['button'], text_color=get_theme_colors()['button_text'], hover_color=get_theme_colors()['alternate_base'])
        )
        self.undo_btn.clicked.connect(self._undo)
        self.undo_btn.hide()
        layout.addWidget(self.undo_btn)
        
        layout.addStretch()
        return panel
    
    def _build_status_bar(self) -> QWidget:
        """Build status bar - kompakt."""
        panel = QWidget()
        self.status_bar_panel = panel
        panel.setMaximumHeight(40)  # Kompakte Höhe
        colors = get_theme_colors()
        panel.setStyleSheet(
            f"background-color: {colors['window']}; border: 1px solid {colors['border']};"
        )
        layout = QHBoxLayout(panel)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 4, 6, 4)  # Minimal padding
        
        # FEATURE: Duplicate Count Label
        self.duplicate_count_label = QLabel(t("0_gruppen"))
        self.duplicate_count_label.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        self.duplicate_count_label.setMaximumWidth(80)
        self.duplicate_count_label.setToolTip(t("anzahl_duplikatgruppen"))
        layout.addWidget(self.duplicate_count_label)
        
        # Progress bar (kleiner) - store for theme updates
        self.progress = QProgressBar()
        self.progress.setFormat("%p%")
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setMaximumHeight(20)
        self._update_progress_bar_style()
        layout.addWidget(self.progress, stretch=1)
        
        # Status label (kleiner Text)
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        self.status_label.setMaximumWidth(260)
        layout.addWidget(self.status_label)
        
        # Finalize button (kompakt)
        self.finalize_btn = QPushButton(t("finalize_export"))
        self.finalize_btn.setMaximumHeight(28)
        success_color = get_semantic_colors()["success"]
        self.finalize_btn.setStyleSheet(
            _build_button_style(success_color, padding="4px 12px", font_size=11, radius=6)
        )
        self.finalize_btn.clicked.connect(self._finalize_and_export)
        layout.addWidget(self.finalize_btn)
        
        return panel
    
    # Data methods
    
    def refresh_groups(self):
        """Refresh group list from database."""
        import time
        start_time = time.monotonic()
        logger.info("[UI] refresh_groups() STARTED")
        
        query_start = time.monotonic()
        self.groups = self._query_groups()
        query_time = time.monotonic() - query_start
        logger.info(f"[UI] _query_groups() completed in {query_time:.3f}s, found {len(self.groups)} groups")
        
        render_start = time.monotonic()
        self._render_groups()
        render_time = time.monotonic() - render_start
        logger.info(f"[UI] _render_groups() completed in {render_time:.3f}s")
        
        self.current_group = None
        self.files_in_group = []
        self.thumbnail_cards = []
        self.current_page = 0
        
        # FEATURE: Update Duplicate Count Label
        if self.duplicate_count_label:
            dup_count = len([g for g in self.groups if not g.group_id.startswith("SINGLE_")])
            self.duplicate_count_label.setText(t("groups_count").format(count=dup_count))
        
        self._clear_grid()
        self.grid_title.setText(f"<h3>{t('select_group')}</h3>")
        self._update_menu_state()
        
        total_time = time.monotonic() - start_time
        logger.info(f"[UI] refresh_groups() FINISHED in {total_time:.3f}s (query={query_time:.3f}s, render={render_time:.3f}s)")
    
    def _show_large_image(self, file_row: FileRow):
        """Öffne Detailansicht in eigenständigem Fenster."""
        try:
            # Find current index in files_in_group for navigation (Feature 2)
            current_index = 0
            if self.files_in_group:
                for idx, f in enumerate(self.files_in_group):
                    if f.path == file_row.path:
                        current_index = idx
                        break
            
            window = ImageDetailWindow(
                file_row, 
                self, 
                all_files=self.files_in_group, 
                current_index=current_index
            )
            window.show()
            logger.info(f"Detailansicht geöffnet: {file_row.path.name}")
        except (RuntimeError, AttributeError, ValueError) as e:
            logger.error(f"Fehler beim Öffnen der Detailansicht für {file_row.path.name}: {e}", exc_info=True)
            self._show_status_message("Detailansicht konnte nicht geöffnet werden", error=True)
    
    def _query_groups(self) -> List[GroupRow]:
        """Query all duplicate groups INCLUDING single-image groups.
        
        Single-image groups are files that need decision but aren't in any duplicate group.
        They're critical for UX - users need to see ALL images that need decisions.
        """
        import time
        query_start = time.monotonic()
        logger.info("[UI] _query_groups() STARTED - querying database...")
        
        self.group_lookup = {}

        # User setting: hide completed groups (no undecided/unsure items)
        hide_completed_groups = False
        try:
            settings = AppConfig.get_user_settings()
            hide_completed_groups = settings.get("quality_settings", {}).get("hide_completed_groups", False)
        except (KeyError, AttributeError, ValueError):
            logger.debug("Could not load hide_completed_groups setting", exc_info=True)
            hide_completed_groups = False
        
        # 1. Get duplicate/similar groups (2+ images)
        cur = self.conn.execute(
            """
            SELECT d.group_id,
                   MIN(f.path) AS sample_path,
                   COUNT(*) AS total,
                   SUM(CASE WHEN f.file_status IN ('UNDECIDED','UNSURE') THEN 1 ELSE 0 END) AS open_cnt,
                   SUM(CASE WHEN f.file_status IN ('KEEP','DELETE') THEN 1 ELSE 0 END) AS decided_cnt,
                   SUM(CASE WHEN f.file_status = 'DELETE' THEN 1 ELSE 0 END) AS delete_cnt,
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
            ORDER BY (open_cnt > 0) DESC, open_cnt DESC, d.group_id
            """
        )
        
        rows = cur.fetchall()
        result: List[GroupRow] = []
        
        for r in rows:
            analyzed_count = int(r[7] or 0)
            min_conf_bucket = int(r[8] or 0)
            needs_review_count = int(r[9] or 0)
            confidence_score = min_conf_bucket if analyzed_count > 0 else 0
            diagnostics_text = build_group_diagnostics(
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
                confidence_level=classify_group_confidence(confidence_score),
                diagnostics_text=diagnostics_text,
            )

            if hide_completed_groups and grp.open_count == 0:
                continue

            result.append(grp)
            self.group_lookup[grp.group_id] = grp
        
        # 2. Get single images (not in any duplicate group) that need decisions
        # These are CRITICAL - they count toward progress but were invisible!
        cur = self.conn.execute(
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
              AND f.file_status IN ('UNDECIDED', 'UNSURE')
            ORDER BY f.path
            """
        )
        
        single_rows = cur.fetchall()
        
        # BUG #4 FIX: TOCTOU-safe file existence check
        # Instead of checking exists() then opening, try to access file stat directly
        for idx, row in enumerate(single_rows):
            file_id, path, status, quality_score, sharpness, lighting, resolution, face_quality = row
            file_path = Path(path)
            
            # TOCTOU-safe: Try to stat the file - if it fails, it doesn't exist
            try:
                file_path.stat()  # Raises FileNotFoundError if missing
            except (FileNotFoundError, OSError) as e:
                # File no longer exists or inaccessible - mark as deleted and skip
                logger.warning(f"Single-image group SINGLE_{file_id}: Datei nicht verfügbar ({file_path.name}): {e}")
                try:
                    self.conn.execute(
                        "UPDATE files SET is_deleted = 1 WHERE file_id = ?",
                        (file_id,)
                    )
                    self.conn.commit()
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as db_err:
                    logger.error(f"Fehler beim Markieren als gelöscht: {db_err}", exc_info=True)
                continue
            
            explanation = build_score_explanation(
                quality_score=float(quality_score) if quality_score is not None else None,
                sharpness_score=float(sharpness) if sharpness is not None else None,
                lighting_score=float(lighting) if lighting is not None else None,
                resolution_score=float(resolution) if resolution is not None else None,
                face_quality_score=float(face_quality) if face_quality is not None else None,
            )
            confidence_score = compute_file_confidence_bucket(
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
                open_count=1,  # Always needs decision
                decided_count=0,
                delete_count=0,
                similarity=0.0,
                needs_review_count=1 if confidence_score in (10, 25) else 0,
                confidence_score=confidence_score,
                confidence_level=classify_group_confidence(confidence_score),
                diagnostics_text=explanation.component_summary_text or "Diagnose: Einzelbild",
            )
            result.append(single_grp)
            self.group_lookup[single_grp.group_id] = single_grp
        
        query_time = time.monotonic() - query_start
        logger.info(f"Loaded {len(result)} groups (including {len(single_rows)} single-image groups) in {query_time:.3f}s")
        logger.info(f"[UI] _query_groups() returning to refresh_groups()...")
        
        return result
    
    def _render_groups(self):
        """Render group list with visual emphasis on undecided items.
        
        PERFORMANCE FIX (Feb 22, 2026): Thumbnails loaded async with ThumbnailLoader worker thread.
        - No sync I/O in UI thread (prevents 45s freeze)
        - QImage created in worker, QPixmap conversion in UI thread (correct Qt threading)
        - Lazy loading for memory efficiency
        """
        import time
        from pathlib import Path
        logger.info(f"[UI] _render_groups() starting for {len(self.groups)} groups...")
        self.group_list.clear()
        term = self.search_box.text().lower().strip()
        needs_review_only = hasattr(self, "needs_review_only_cb") and self.needs_review_only_cb.isChecked()

        self._group_thumb_total = 0
        self._group_thumb_done = 0
        
        render_count = 0
        queued_count = 0
        for grp_idx, grp in enumerate(self.groups):
            # Check if this is a single-image group
            is_single = grp.group_id.startswith("SINGLE_")
            
            if is_single:
                label = f"{t('group_list_single')} • {grp.sample_path.name}"
            else:
                label = t("group_list_many").format(id=grp.group_id, count=grp.total)
            
            if term and term not in label.lower() and term not in str(grp.sample_path).lower():
                continue
            if needs_review_only and grp.needs_review_count <= 0:
                continue
            
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, grp.group_id)

            # FIX (Feb 22, 2026): Set gray placeholder - actual thumbnail loaded by ThumbnailLoader
            placeholder = QPixmap(48, 48)
            placeholder.fill(Qt.gray)
            item.setIcon(QIcon(placeholder))
            
            # Store sample_path for async thumbnail loading in Qt.UserRole+1
            item.setData(Qt.UserRole + 1, str(grp.sample_path))
            
            render_count += 1
            
            # Status indicator with CLEAR visual distinction for undecided
            status_colors = get_status_colors()
            if grp.open_count == 0:
                status_icon = t("group_status_done")
                status_color = QColor(status_colors["KEEP"])
                bg_alpha = 60
            elif grp.open_count > 0 and grp.decided_count > 0:
                status_icon = t("group_status_partial")
                status_color = QColor(status_colors["UNSURE"])
                bg_alpha = 80
            else:
                status_icon = t("group_status_open")
                status_color = QColor(status_colors["UNDECIDED_ATTENTION"])
                bg_alpha = 100  # More opaque for better visibility
            
            needs_review_hint = (
                t("manual_review_hint").format(count=grp.needs_review_count)
                if grp.needs_review_count > 0
                else ""
            )
            item.setText(f"{status_icon} {label}{needs_review_hint}")
            
            # Enhanced tooltip
            if is_single:
                item.setToolTip(
                    f"EINZELBILD - ENTSCHEIDUNG BENOETIGT\n"
                    f"Datei: {grp.sample_path.name}\n"
                    f"Status: Noch nicht entschieden{needs_review_hint}\n"
                    f"Pruefstatus: {_get_confidence_i18n_label(grp.confidence_level)}\n"
                    f"{grp.diagnostics_text}"
                )
            else:
                item.setToolTip(
                    f"{t('group_counts_summary').format(open_count=grp.open_count, decided_count=grp.decided_count, delete_count=grp.delete_count)}\n"
                    f"{(t('group_action_needed') if grp.open_count > 0 else t('group_action_done'))}{needs_review_hint}\n"
                    f"Pruefstatus: {_get_confidence_i18n_label(grp.confidence_level)}\n"
                    f"{grp.diagnostics_text}"
                )
            
            status_color.setAlpha(bg_alpha)
            item.setBackground(QBrush(status_color))
            
            self.group_list.addItem(item)
        
        logger.info(f"[UI] _render_groups() added {render_count} items to list (filtered from {len(self.groups)} total groups)")
        if hasattr(self, "needs_review_counter_label"):
            total_needs_review = sum(1 for grp in self.groups if grp.needs_review_count > 0)
            visible_needs_review = sum(
                1
                for i in range(self.group_list.count())
                if self.group_lookup.get(str(self.group_list.item(i).data(Qt.UserRole)))
                and self.group_lookup[str(self.group_list.item(i).data(Qt.UserRole))].needs_review_count > 0
            )
            self.needs_review_counter_label.setText(
                t("needs_review_counter").format(visible=visible_needs_review, total=total_needs_review)
            )
        
        # FIX (Feb 23, 2026): Clear old thumbnail requests to prevent race condition
        # Without this, callbacks for old indices would cause "invalid index" warnings
        if self._group_thumb_loader:
            self._group_thumb_loader.clear_queue()
        
        # FIX (Feb 22, 2026): Queue thumbnails for async loading by ThumbnailLoader worker
        logger.info(f"[UI] Queueing {self.group_list.count()} thumbnails for async loading...")
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            thumb_path_str = item.data(Qt.UserRole + 1)
            if thumb_path_str:
                from pathlib import Path
                self._group_thumb_loader.enqueue(i, Path(thumb_path_str))
                self._group_thumb_total += 1
        logger.info(f"[UI] Thumbnail loading queued")
        self._update_thumbnail_progress()
    
    def _on_group_thumb_loaded(self, list_index: int, qimg: QImage) -> None:
        """Callback when thumbnail loaded by ThumbnailLoader thread.
        
        IMPORTANT Qt Rule: QPixmap can only be created in UI thread.
        Worker sends QImage, we convert here to QPixmap.
        
        This is the correct threading pattern:
        - Worker (background thread): Load image → create QImage → emit signal with QImage
        - UI thread (this slot): Convert QImage → QPixmap → update widget
        
        Args:
            list_index: Index in group_list widget
            qimg: QImage from ThumbnailLoader worker thread
        """
        logger.debug(f"[UI] Group thumbnail slot received index={list_index}")
        if list_index < 0 or list_index >= self.group_list.count():
            logger.warning(f"[UI] Thumbnail callback: invalid index {list_index}")
            return
        
        if qimg.isNull():
            logger.debug(f"[UI] Thumbnail callback: null image for index {list_index}, skipping")
            return
        
        # Convert QImage → QPixmap in UI thread (SAFE, only here!)
        from PySide6.QtGui import QPixmap, QIcon
        pixmap = QPixmap.fromImage(qimg)
        
        # Update item icon
        item = self.group_list.item(list_index)
        if item:
            item.setIcon(QIcon(pixmap))
            path_str = item.data(Qt.UserRole + 1)
            logger.debug(f"[UI] Thumbnail icon set for list item {list_index} path={path_str}")
            self._group_thumb_done += 1
            self._update_thumbnail_progress()

    def _on_grid_thumb_loaded(self, list_index: int, qimg: QImage) -> None:
        """Callback when grid thumbnail loaded by ThumbnailLoader thread."""
        logger.debug(f"[UI] Grid thumbnail slot received index={list_index}")
        card = self._grid_thumb_index_map.get(list_index)
        if not card:
            logger.debug(f"[UI] Grid thumbnail callback: stale index {list_index}")
            return
        if qimg.isNull():
            logger.debug(f"[UI] Grid thumbnail callback: null image index {list_index}")
            return
        card.set_thumbnail_image(qimg)
        logger.debug(f"[UI] Grid thumbnail set for index {list_index} path={card.file_row.path}")
        self._grid_thumb_done += 1
        self._update_thumbnail_progress()

    def _update_thumbnail_progress(self) -> None:
        """Update progress dialog while thumbnails are loading."""
        total = self._group_thumb_total + self._grid_thumb_total
        done = self._group_thumb_done + self._grid_thumb_done
        if total <= 0:
            return
        self._thumb_loading_active = done < total
        progress = self._post_indexing_progress_dialog
        if progress and progress.isVisible():
            progress.setMinimum(0)
            progress.setMaximum(100)
            mapped = 95 if total <= 0 else min(100, 95 + int(round((done / total) * 5)))
            elapsed = max(0.0, time.monotonic() - self._pipeline_start_ts)
            eta = self._format_eta(elapsed, done, total)
            label = f"Schritt 3/3: Vorschau wird aufgebaut ({done}/{total})"
            if eta:
                label += f"\n{eta}"
            self._update_progress_dialog(
                progress,
                value=mapped,
                label=label,
                force=True,
            )
            if done >= total:
                progress.close()
                self._post_indexing_progress_dialog = None
                self._indexing_progress_dialog = None
                self._thumb_loading_active = False
                if self._pending_rating_summary:
                    summary = self._pending_rating_summary
                    self._pending_rating_summary = None
                    self._show_analysis_summary(summary)
    
    def _on_group_selected(self):
        """Handle group selection."""
        items = self.group_list.selectedItems()
        
        # NEW Feature 3: Enable Merge button when 2+ groups selected
        if hasattr(self, 'merge_groups_btn'):
            num_selected = len(items)
            if num_selected >= 2:
                self.merge_groups_btn.setEnabled(True)
                self.merge_groups_btn.setText(f"{t('merge_groups')} ({num_selected})")
            else:
                self.merge_groups_btn.setEnabled(False)
                self.merge_groups_btn.setText(t("merge_groups"))
        
        if not items:
            return
        
        # Load first selected group
        group_id = items[0].data(Qt.UserRole)
        self.current_group = group_id
        self._load_group_files(group_id)
    
    def _load_group_files(self, group_id: str):
        """Load files for selected group, sorted by score (best first)."""
        # Save selection state of PREVIOUS group
        if self.current_group:
            self._save_group_selection_state(self.current_group)
        
        # Set current group
        self.current_group = group_id

        # Handle synthetic single-image groups
        if group_id.startswith("SINGLE_"):
            try:
                file_id = int(group_id.replace("SINGLE_", ""))
            except ValueError:
                logger.error(f"Invalid single group id: {group_id}")
                self.files_in_group = []
                self._render_grid()
                return

            cur = self.conn.execute(
                """
                SELECT f.file_id, f.path, f.file_status, f.is_locked, COALESCE(f.is_recommended, 0),
                      f.quality_score,
                      f.sharpness_component,
                      f.lighting_component,
                      f.resolution_component,
                      f.face_quality_component
                FROM files f
                WHERE f.file_id = ? AND f.is_deleted = 0
                """,
                (file_id,),
            )
            row = cur.fetchone()
            if row:
                file_path = Path(row[1])
                if file_path.exists():
                    self.files_in_group = [FileRow(
                        file_path, 
                        FileStatus(row[2]), 
                        bool(row[3]), 
                        bool(row[4]), 
                        float(row[5]) if row[5] is not None else None,
                        float(row[6]) if row[6] is not None else None,
                        float(row[7]) if row[7] is not None else None,
                        float(row[8]) if row[8] is not None else None,
                        float(row[9]) if row[9] is not None else None
                    )]
                else:
                    # File no longer exists - mark as deleted and show empty group
                    logger.warning(f"Single group {group_id}: Datei nicht gefunden: {file_path.name} (wird aus DB entfernt)")
                    try:
                        self.conn.execute(
                            "UPDATE files SET is_deleted = 1 WHERE file_id = ?",
                            (file_id,)
                        )
                        self.conn.commit()
                    except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                        logger.error(f"Fehler beim Markieren als gelöscht: {e}", exc_info=True)
                    self.files_in_group = []
            else:
                self.files_in_group = []
            
            logger.debug(
                f"Single group {group_id}: {len(self.files_in_group)} image loaded"
            )
            self.current_page = 0
            self._render_grid()
            return
        
        # First, get all quality scores if available (from auto-rating)
        cur = self.conn.execute(
            """
            SELECT f.file_id, f.path, f.file_status, f.is_locked, COALESCE(f.is_recommended, 0),
                 f.quality_score,
                 f.sharpness_component,
                 f.lighting_component,
                 f.resolution_component,
                 f.face_quality_component
            FROM files f
            JOIN duplicates d ON f.file_id = d.file_id
            WHERE d.group_id = ? AND f.is_deleted = 0
            ORDER BY 
                COALESCE(f.is_recommended, 0) DESC,
                COALESCE(f.quality_score, 0) DESC,
                f.file_status = 'KEEP' DESC,
                f.path
            """,
            (group_id,),
        )
        
        rows = cur.fetchall()
        # Filter out files that no longer exist on disk
        valid_files = []
        missing_files = []
        for r in rows:
            file_path = Path(r[1])
            if file_path.exists():
                valid_files.append(
                    FileRow(
                        file_path, 
                        FileStatus(r[2]), 
                        bool(r[3]), 
                        bool(r[4]), 
                        float(r[5]) if r[5] is not None else None,
                        float(r[6]) if r[6] is not None else None,
                        float(r[7]) if r[7] is not None else None,
                        float(r[8]) if r[8] is not None else None,
                        float(r[9]) if r[9] is not None else None
                    )
                )
            else:
                missing_files.append((r[0], file_path.name))
        
        # Log and clean up missing files from database
        if missing_files:
            logger.warning(f"Gruppe {group_id}: {len(missing_files)} Dateien nicht gefunden (werden aus DB entfernt):")
            for file_id, filename in missing_files:
                logger.warning(f"  - {filename}")
                # Mark as deleted in database to prevent future errors
                try:
                    self.conn.execute(
                        "UPDATE files SET is_deleted = 1 WHERE file_id = ?",
                        (file_id,)
                    )
                except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
                    logger.error(f"Fehler beim Markieren von {filename} als gelöscht: {e}", exc_info=True)
            self.conn.commit()
        
        self.files_in_group = valid_files
        
        logger.debug(
            f"Gruppe {group_id}: {len(self.files_in_group)} Bilder geladen "
            f"(sortiert nach Score/Empfehlung)"
        )
        self.current_page = 0
        self._render_grid()
    
    def _render_grid(self):
        """Render thumbnail grid with virtual scrolling if needed."""
        self._clear_grid()
        self._grid_thumb_index_map = {}
        self._grid_thumb_total = 0
        self._grid_thumb_done = 0
        
        # FIX (Feb 23, 2026): Clear old grid thumbnail requests to prevent race condition
        if self._grid_thumb_loader:
            self._grid_thumb_loader.clear_queue()
        
        if not self.files_in_group:
            self.grid_title.setText(f"<h3>{t('no_images_group')}</h3>")
            return
        
        # CRITICAL: Defensive Null-Check für verwaiste current_group
        if not self.current_group:
            logger.warning("_render_grid() called with None current_group - resetting to first group")
            self.grid_title.setText(f"<h3>{t('group_not_available')}</h3>")
            return
        
        grp = self.group_lookup.get(self.current_group)
        if grp and grp.group_id:
            self.grid_title.setText(
                f"<h3>{t('group_title').format(id=grp.group_id, count=len(self.files_in_group))}</h3>"
                f"<small>Pruefstatus: {_get_confidence_i18n_label(grp.confidence_level)} | {grp.diagnostics_text}</small>"
            )
        else:
            # Fallback: Group nicht in lookup - Log und zeige generischen Title
            logger.debug(f"Group {self.current_group} not in lookup, using generic title")
            self.grid_title.setText(f"<h3>{t('images_not_found').format(count=len(self.files_in_group))}</h3>")
        
        total_items = len(self.files_in_group)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, total_pages - 1)
        start = self.current_page * self.page_size
        end = min(total_items, start + self.page_size)

        # Create cards for current page only
        for idx, file_row in enumerate(self.files_in_group[start:end], start=start):
            card = ThumbnailCard(file_row, idx)
            card.clicked.connect(self._on_card_clicked)
            self.thumbnail_cards.append(card)
            if self._grid_thumb_loader:
                self._grid_thumb_index_map[idx] = card
                self._grid_thumb_loader.enqueue(idx, file_row.path)
                self._grid_thumb_total += 1
        
        # CRITICAL: Use items_per_row from VirtualScrollContainer if available, else default to 4
        cols = getattr(self, 'items_per_row', 4) if hasattr(self, 'items_per_row') else 4
        for local_idx, card in enumerate(self.thumbnail_cards):
            row = local_idx // cols
            col = local_idx % cols
            self.grid_layout.addWidget(card, row, col)
        self.grid_layout.setRowStretch(max(1, (len(self.thumbnail_cards) // cols) + 1), 1)

        # Restore selection state for visible page
        selected_indices, _ = self._get_group_selection_state(self.current_group or "")
        for idx in selected_indices:
            if start <= idx < end:
                local_idx = idx - start
                if 0 <= local_idx < len(self.thumbnail_cards):
                    self.thumbnail_cards[local_idx].set_selected(True)
        
        self._update_pagination_controls(total_pages, start, end, total_items)
        self._update_selection_ui()
        logger.info(f"[UI] Queued {self._grid_thumb_total} grid thumbnails (page {self.current_page + 1}/{total_pages})")
        self._update_thumbnail_progress()

    def _update_pagination_controls(self, total_pages: int, start: int, end: int, total_items: int) -> None:
        if not self.pagination_label or not self.prev_page_btn or not self.next_page_btn:
            return
        self.pagination_label.setText(
            t("page_info").format(
                page=self.current_page + 1,
                total=total_pages,
                start=start + 1,
                end=end,
                count=total_items
            )
        )
        if total_pages <= 1:
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
        else:
            self.prev_page_btn.setEnabled(self.current_page > 0)
            self.next_page_btn.setEnabled(self.current_page < total_pages - 1)

    def _next_page(self) -> None:
        total_items = len(self.files_in_group)
        total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._render_grid()

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._render_grid()
    
    def _clear_grid(self):
        """Clear thumbnail grid, preserving selection state."""
        # Don't clear selected_indices - they persist across renders
        
        # CRITICAL: Explicit cleanup to prevent memory leak
        for card in self.thumbnail_cards:
            try:
                card.cleanup()
            except (RuntimeError, AttributeError):
                logger.debug("Error cleaning up card", exc_info=True)
                pass  # Cleanup errors shouldn't block
        
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.thumbnail_cards = []
    
    def _on_card_clicked(self, index: int):
        """Handle card click - support batch selection or open detail dialog."""
        if 0 <= index < len(self.files_in_group):
            modifiers = QApplication.keyboardModifiers()
            page_start = self.current_page * self.page_size
            local_idx = index - page_start
            card = self.thumbnail_cards[local_idx] if 0 <= local_idx < len(self.thumbnail_cards) else None
            
            # Get current group's selection state
            selected_indices, last_selected = self._get_group_selection_state(self.current_group or "")
            
            # Ctrl+Click: Toggle selection
            if modifiers & Qt.ControlModifier:
                if index in selected_indices:
                    selected_indices.remove(index)
                    if card:
                        card.set_selected(False)
                else:
                    selected_indices.add(index)
                    if card:
                        card.set_selected(True)
                
                last_selected = index
                self._save_group_selection_state(self.current_group or "", selected_indices, last_selected)
                self._update_selection_ui()
            
            # Shift+Click: Range selection
            elif modifiers & Qt.ShiftModifier:
                if last_selected >= 0:
                    start = min(last_selected, index)
                    end = max(last_selected, index)
                    
                    for i in range(start, end + 1):
                        selected_indices.add(i)
                        if page_start <= i < page_start + len(self.thumbnail_cards):
                            local = i - page_start
                            self.thumbnail_cards[local].set_selected(True)
                    
                    self._save_group_selection_state(self.current_group or "", selected_indices, last_selected)
                    self._update_selection_ui()
            
            # Normal click: Zeige Bild groß im Hauptbereich
            else:
                if not selected_indices:
                    self.current_index = index
                    file_row = self.files_in_group[index]
                    self._show_large_image(file_row)
                else:
                    # If there's a selection, toggle this card
                    if index in selected_indices:
                        selected_indices.remove(index)
                        if card:
                            card.set_selected(False)
                    else:
                        selected_indices.add(index)
                        if card:
                            card.set_selected(True)
                    
                    last_selected = index
                    self._save_group_selection_state(self.current_group or "", selected_indices, last_selected)
                    self._update_selection_ui()
    
    def _select_all(self):
        """Select all images in current group."""
        selected_indices, _ = self._get_group_selection_state(self.current_group or "")
        page_start = self.current_page * self.page_size
        for offset in range(len(self.thumbnail_cards)):
            idx = page_start + offset
            selected_indices.add(idx)
            self.thumbnail_cards[offset].set_selected(True)
        last_idx = page_start + len(self.thumbnail_cards) - 1 if self.thumbnail_cards else -1
        self._save_group_selection_state(self.current_group or "", selected_indices, last_idx)
        self._update_selection_ui()
    
    def _clear_selection(self):
        """Clear all selections for current group."""
        selected_indices, _ = self._get_group_selection_state(self.current_group or "")
        for card in self.thumbnail_cards:
            card.set_selected(False)
        selected_indices.clear()
        self._save_group_selection_state(self.current_group or "", selected_indices, -1)
        self._update_selection_ui()
    
    def _get_group_selection_state(self, group_id: str) -> tuple[set[int], int]:
        """Get selection state for a specific group. Returns (selected_indices, last_selected_index)."""
        if group_id not in self._group_selection_state:
            self._group_selection_state[group_id] = (set(), -1)
        return self._group_selection_state[group_id]

    def _get_selected_indices(self) -> List[int]:
        """Compatibility helper for shortcuts; returns bounded, sorted indices for current group."""
        return self._selection_workflow.get_selected_indices(
            self.current_group,
            len(self.files_in_group),
            self._get_group_selection_state,
        )
    
    def _save_group_selection_state(self, group_id: str, selected_indices: Optional[set[int]] = None, last_selected_index: int = -1):
        """Save selection state for a specific group."""
        if selected_indices is None:
            selected_indices, last_selected_index = self._get_group_selection_state(group_id)
        self._group_selection_state[group_id] = (selected_indices, last_selected_index)
    
    def _update_selection_ui(self):
        """Update UI based on selection state of current group."""
        selected_indices, _ = self._get_group_selection_state(self.current_group or "")
        state = self._selection_workflow.build_selection_ui_state(len(selected_indices), t)

        self.selection_count_label.setText(state.count_text)
        self.compare_btn.setEnabled(state.compare_enabled)
        self.compare_btn.setText(state.compare_text)
        if state.compare_visible:
            self.compare_btn.show()
        else:
            self.compare_btn.hide()

        can_split = (
            self.current_group is not None
            and not str(self.current_group).startswith("SINGLE_")
            and len(selected_indices) >= 1
            and len(selected_indices) < len(self.files_in_group)
        )
        self.split_group_btn.setEnabled(can_split)
        if state.action_buttons_visible:
            self.split_group_btn.show()
        else:
            self.split_group_btn.hide()

        if state.action_buttons_visible:
            self.keep_btn.show()
            self.del_btn.show()
            self.unsure_btn.show()
        else:
            self.keep_btn.hide()
            self.del_btn.hide()
            self.unsure_btn.hide()
    
    def _open_comparison(self):
        """Öffne Seite-an-Seite-Vergleich in eigenständigem Fenster."""
        pair = self._selection_workflow.get_comparison_pair_indices(
            self.current_group,
            len(self.files_in_group),
            self._get_group_selection_state,
        )
        if pair is None:
            QMessageBox.warning(
                self,
                t("invalid_selection"),
                t("select_exactly_two_images")
            )
            return

        file_row_1 = self.files_in_group[pair[0]]
        file_row_2 = self.files_in_group[pair[1]]
        
        try:
            # Eigenständiges Fenster (nicht modal) - erscheint in Taskleiste
            window = SideBySideComparisonWindow(file_row_1, file_row_2, self)
            window.show()  # show() statt exec() - nicht blockierend
            logger.info(f"Vergleichsfenster geöffnet: {file_row_1.path.name} vs {file_row_2.path.name}")
        except (RuntimeError, AttributeError, ValueError) as e:
            logger.error(f"Fehler beim Öffnen des Vergleichsfensters: {e}", exc_info=True)
            self._show_status_message(t("comparison_window_failed"), error=True)
    
    # Action methods
    
    def _apply_status_to_selection(self, status: FileStatus):
        """Wende Status auf alle ausgewählten Bilder an (ATOMIC mit Transaktionen).
        
        BUG #10 FIX: Validate input before batch operation.
        """
        selected_indices = self._selection_workflow.get_selected_indices(
            self.current_group,
            len(self.files_in_group),
            self._get_group_selection_state,
        )
        if not selected_indices:
            self._show_status_message(t("no_images_selected_error"), error=True)
            return

        paths_to_update = self._selection_workflow.collect_valid_existing_paths(
            selected_indices,
            self.files_in_group,
        )
        for idx in selected_indices:
            if idx < 0 or idx >= len(self.files_in_group):
                continue
            file_path = self.files_in_group[idx].path
            if not file_path or not file_path.exists():
                logger.warning(f"Skipping invalid/missing file: {file_path}")
        
        if not paths_to_update:
            self._show_status_message(t("no_valid_images_to_update"), error=True)
            return
        
        # CRITICAL: Nutze atomare Batch-Methode
        res = self.actions.ui_batch_set_status(paths_to_update, status)
        
        if res.get("ok"):
            success_count = res.get("updated", len(paths_to_update))
            
            # Setze empfohlenes Bild (nur bei KEEP)
            if status == FileStatus.KEEP and paths_to_update:
                self._set_recommended(paths_to_update[0])
            
            self._show_status_message(t("images_updated_count").format(success=success_count, total=len(paths_to_update)))
            self._reload_after_action()
            self._save_session(f"Set {success_count} image(s) to {status.value}")
        else:
            error_msg = res.get("message", "Unbekannter Fehler")
            logger.error(f"Batch status update failed: {error_msg}")
            self._show_status_message(t("error_message").format(error=error_msg), error=True)
    
    def _toggle_lock_selection(self):
        """Sperre/Entsperre alle ausgewählten Bilder."""
        selected_indices, _ = self._get_group_selection_state(self.current_group or "")
        if not selected_indices:
            self._show_status_message(t("no_images_selected_error"), error=True)
            return
        
        success_count = 0
        for idx in selected_indices:
            if idx < len(self.files_in_group):
                file_row = self.files_in_group[idx]
                res = self.actions.ui_toggle_lock(file_row.path)
                
                if res.get("ok"):
                    success_count += 1
        
        self._show_status_message(t("lock_toggled_count").format(count=success_count))
        self._reload_after_action()
        
        # Save session after lock toggle
        self._save_session(f"Toggled lock for {success_count} image(s)")
    
    def _undo(self):
        """Letzte Aktion rückgängig machen."""
        res = self.actions.ui_undo()
        self._show_status_message(res.get("message", "Rückgängig erfolgreich"))
        self._reload_after_action()
    
    def _reload_after_action(self):
        """Reload current group after action, preserving selection."""
        if self.current_group:
            # Save selection (already saved in _group_selection_state)
            saved_selection, saved_last = self._get_group_selection_state(self.current_group)
            
            self._load_group_files(self.current_group)
            
            # Restore selection
            page_start = self.current_page * self.page_size
            for idx in saved_selection:
                if page_start <= idx < page_start + len(self.thumbnail_cards):
                    local = idx - page_start
                    card = self.thumbnail_cards[local]
                    card.update_status(self.files_in_group[idx].status)
                    card.set_selected(True)
            
            self._update_selection_ui()
        
        self._update_progress()

    def _split_selected_from_group(self):
        """Split selected files from current group into a new group with undo persistence."""
        if not self.current_group or str(self.current_group).startswith("SINGLE_"):
            QMessageBox.warning(self, t("split_failed"), t("split_single_not_allowed"))
            return

        selected_indices, _ = self._get_group_selection_state(self.current_group)
        if not selected_indices:
            QMessageBox.warning(self, t("split_failed"), t("no_images_selected_error"))
            return
        if len(selected_indices) >= len(self.files_in_group):
            QMessageBox.warning(self, t("split_failed"), t("split_not_all"))
            return

        reply = QMessageBox.question(
            self,
            t("split_group"),
            t("split_confirm").format(count=len(selected_indices)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            selected_paths = []
            for idx in sorted(selected_indices):
                if 0 <= idx < len(self.files_in_group):
                    selected_paths.append(str(self.files_in_group[idx].path))

            if not selected_paths:
                QMessageBox.warning(self, t("split_failed"), t("no_valid_images_to_update"))
                return

            placeholders = ",".join("?" for _ in selected_paths)
            rows = self.conn.execute(
                f"SELECT file_id FROM files WHERE path IN ({placeholders})",
                selected_paths,
            ).fetchall()
            file_ids = [int(row[0]) for row in rows]
            if len(file_ids) != len(selected_paths):
                raise ValueError("Nicht alle gewaehlten Dateien konnten in der Datenbank gefunden werden.")

            import time

            split_group_id = f"SPLIT_{int(time.time())}"
            split_action_id = f"GROUP_SPLIT_{int(time.time() * 1000)}"
            old_group_id = str(self.current_group)

            for file_id in file_ids:
                self.history.record_group_reassignment(
                    action_id=split_action_id,
                    file_id=file_id,
                    old_group_id=old_group_id,
                    new_group_id=split_group_id,
                    reason="source=split",
                )

            file_placeholders = ",".join("?" for _ in file_ids)
            self.conn.execute(
                f"UPDATE duplicates SET group_id = ? WHERE group_id = ? AND file_id IN ({file_placeholders})",
                [split_group_id, old_group_id, *file_ids],
            )
            self.conn.commit()

            self._show_status_message(t("split_success"))
            self.refresh_groups()
            for i in range(self.group_list.count()):
                item = self.group_list.item(i)
                if item.data(Qt.UserRole) == split_group_id:
                    self.group_list.setCurrentItem(item)
                    break
            self._save_session(f"Split {len(file_ids)} image(s) from group {old_group_id}")

        except (ValueError, sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Error splitting group {self.current_group}: {e}", exc_info=True)
            QMessageBox.critical(self, t("split_failed"), t("split_error").format(error=e))
    
    def _set_recommended(self, path: Path):
        """Set image as recommended."""
        if not self.current_group:
            return
        
        try:
            self.conn.execute(
                """
                UPDATE files
                SET is_recommended = 0, keeper_source = 'undecided'
                WHERE file_id IN (
                    SELECT f.file_id
                    FROM files f
                    JOIN duplicates d ON f.file_id = d.file_id
                    WHERE d.group_id = ?
                )
                """,
                (self.current_group,),
            )
            
            self.conn.execute(
                "UPDATE files SET is_recommended = 1, keeper_source = 'manual' WHERE path = ?",
                (str(path),),
            )
            
            self.conn.commit()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Error setting recommendation: {e}", exc_info=True)
    
    # UI update methods
    
    def _update_progress(self):
        """Update progress bar with detailed breakdown.
        
        CRITICAL FIX: Only count files that actually exist on disk (is_deleted = 0).
        """
        res = self.actions.ui_get_active_progress()
        if not res.get("ok"):
            return

        total = int(res.get("files_total", 0) or 0)
        keep_count = int(res.get("files_keep", 0) or 0)
        decided = int(res.get("files_decided", 0) or 0)
        open_files = int(res.get("files_open", 0) or 0)
        
        pct = int((decided / total) * 100) if total else 0
        
        # Count single-image groups for display
        single_count = sum(1 for g in self.groups if g.group_id.startswith("SINGLE_"))
        group_count = len(self.groups) - single_count
        
        self.progress.setValue(pct)
        
        # Compact status (no action messages, no icons)
        if total > 0:
            if open_files > 0:
                self.status_label.setText(f"{decided}/{total} • offen {open_files}")
            else:
                self.status_label.setText(f"{decided}/{total}")
        else:
            self.status_label.setText("0/0")
        
        # Change color based on progress
        semantic_colors = get_semantic_colors()
        if pct == 100:
            self.status_label.setStyleSheet(f"color: {semantic_colors['success']}; padding: 4px 12px; font-size: 13px; font-weight: bold;")  # Green
        elif pct > 50:
            self.status_label.setStyleSheet(f"color: {semantic_colors['warning']}; padding: 4px 12px; font-size: 13px; font-weight: bold;")  # Orange
        else:
            self.status_label.setStyleSheet(f"color: {semantic_colors['error']}; padding: 4px 12px; font-size: 13px; font-weight: bold;")  # Red
    
    def _show_status_message(self, message: str, error: bool = False):
        """Show status message."""
        # Avoid overwriting progress status with action messages
        if error:
            logger.warning("Status message suppressed: %s", message)
        else:
            logger.info("Status message suppressed: %s", message)
        self._update_progress()
    
    def _apply_group_filter(self):
        """Apply search filter to groups."""
        self._render_groups()
    
    def _merge_selected_groups(self):
        """Merge selected duplicate groups (Feature 3)."""
        try:
            items = self.group_list.selectedItems()
            group_ids: list[str] = []
            single_file_ids: list[int] = []
            for item in items:
                gid = str(item.data(Qt.UserRole))
                if gid.startswith("SINGLE_"):
                    try:
                        single_file_ids.append(int(gid.replace("SINGLE_", "")))
                    except ValueError:
                        continue
                else:
                    group_ids.append(gid)
            
            if (len(group_ids) + len(single_file_ids)) < 2:
                QMessageBox.warning(
                    self, 
                    t("merge_failed"), 
                    "Bitte wählen Sie mindestens 2 Gruppen zum Zusammenführen aus."
                )
                return
            
            # Confirmation dialog
            reply = QMessageBox.question(
                self,
                "Gruppen zusammenführen?",
                f"Möchten Sie {len(group_ids)} Gruppen zusammenführen?\n\n"
                f"Die Bilder werden in einer neuen Gruppe zusammengefasst und "
                f"automatisch neu bewertet.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Generate new merged group ID
            import time
            new_group_id = f"MERGED_{int(time.time())}"
            merge_action_id = f"GROUP_MERGE_{int(time.time() * 1000)}"
            
            logger.info(f"Merging groups {group_ids} into {new_group_id}")

            # Snapshot original group assignments for undo persistence.
            reassignments: list[tuple[int, str | None]] = []

            for old_group_id in group_ids:
                rows = self.conn.execute(
                    "SELECT file_id FROM duplicates WHERE group_id = ?",
                    (old_group_id,),
                ).fetchall()
                reassignments.extend((int(row[0]), old_group_id) for row in rows)

            for file_id in single_file_ids:
                existing_group = self.conn.execute(
                    "SELECT group_id FROM duplicates WHERE file_id = ? LIMIT 1",
                    (file_id,),
                ).fetchone()
                reassignments.append((int(file_id), str(existing_group[0]) if existing_group else None))
            
            # Update database: Move all files to new group
            for old_group_id in group_ids:
                self.conn.execute(
                    "UPDATE duplicates SET group_id = ? WHERE group_id = ?",
                    (new_group_id, old_group_id)
                )

            # Insert single-image groups into duplicates table
            for file_id in single_file_ids:
                existing = self.conn.execute(
                    "SELECT 1 FROM duplicates WHERE file_id = ? LIMIT 1",
                    (file_id,),
                ).fetchone()
                if existing:
                    self.conn.execute(
                        "UPDATE duplicates SET group_id = ? WHERE file_id = ?",
                        (new_group_id, file_id),
                    )
                else:
                    self.conn.execute(
                        "INSERT INTO duplicates (group_id, file_id, similarity_score, is_keeper) VALUES (?, ?, ?, 0)",
                        (new_group_id, file_id, 1.0),
                    )

            # Persist reassignment history for DB-level undo.
            seen_file_ids: set[int] = set()
            for file_id, old_group in reassignments:
                if file_id in seen_file_ids:
                    continue
                seen_file_ids.add(file_id)
                self.history.record_group_reassignment(
                    action_id=merge_action_id,
                    file_id=file_id,
                    old_group_id=old_group,
                    new_group_id=new_group_id,
                    reason="source=merge",
                )
            
            self.conn.commit()
            
            # Re-run quality scoring on merged group (can be expensive)
            progress = QProgressDialog(
                "Neue Gruppe wird bewertet...",
                t("cancel"),
                0,
                100,
                self,
            )
            progress.setWindowTitle(t("analysis_running"))
            progress.setMinimumDuration(0)
            progress.setMinimumWidth(460)
            progress.setMinimumHeight(140)
            progress.setStyleSheet(
                "QLabel { padding: 6px 8px; }"
                "QProgressBar { min-height: 18px; text-align: center; }"
            )
            self._center_progress_dialog_text(progress)
            progress.setValue(5)
            QApplication.processEvents()
            
            rated_ok = self._auto_rate_single_group(new_group_id, progress)
            progress.close()
            
            if rated_ok:
                total_merged = len(group_ids) + len(single_file_ids)
                self._show_status_message(f"✓ {t('merge_success')}: {total_merged} Gruppen → 1 Gruppe")
            else:
                self._show_status_message(t("merge_success") + " (ohne Neubewertung)")
            
            # Refresh groups and select the new merged group
            self.refresh_groups()
            
            # Find and select the new merged group
            for i in range(self.group_list.count()):
                item = self.group_list.item(i)
                if item.data(Qt.UserRole) == new_group_id:
                    self.group_list.setCurrentItem(item)
                    break
            
        except (KeyError, ValueError, sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"Error merging groups: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                t("merge_failed"),
                f"Fehler beim Zusammenführen: {e}"
            )
    
    # Theme and mode
    
    def _apply_dark_palette(self):
        """Apply dark theme."""
        apply_theme_to_palette(self, "dark")
    
    def _apply_light_palette(self):
        """Apply light theme."""
        apply_theme_to_palette(self, "light")
    
    def _apply_high_contrast_palette(self):
        """Apply high-contrast theme."""
        colors = get_high_contrast_colors()
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(colors["window"]))
        pal.setColor(QPalette.WindowText, QColor(colors["window_text"]))
        pal.setColor(QPalette.Base, QColor(colors["base"]))
        pal.setColor(QPalette.AlternateBase, QColor(colors["alternate_base"]))
        pal.setColor(QPalette.Text, QColor(colors["text"]))
        pal.setColor(QPalette.Button, QColor(colors["button"]))
        pal.setColor(QPalette.ButtonText, QColor(colors["button_text"]))
        pal.setColor(QPalette.Highlight, QColor(colors["highlight"]))
        pal.setColor(QPalette.HighlightedText, QColor(colors["highlighted_text"]))
        self.setPalette(pal)
    
    def _on_theme_changed(self, theme_name: str):
        """Behandle Theme-Wechsel."""
        self.current_theme = theme_name
        
        if theme_name == "Dunkel":
            self._apply_dark_palette()
        elif theme_name == "Hell":
            self._apply_light_palette()
        elif theme_name == "System":
            self.setPalette(QApplication.palette())
        elif theme_name == "Hoher Kontrast":
            self._apply_high_contrast_palette()
        
        self.update()
    
    def _on_mode_changed(self, mode_name: str):
        """Handle mode change."""
        mode_map = {
            "SAFE_MODE": AppMode.SAFE_MODE,
            "REVIEW_MODE": AppMode.REVIEW_MODE,
            "CLEANUP_MODE": AppMode.CLEANUP_MODE,
        }
        
        if mode_name in mode_map:
            self.mode_svc.set_mode(mode_map[mode_name])
            self._update_button_states()
            logger.debug(f"Mode changed to: {mode_name}")
    
    def _sync_mode_display(self):
        """Sync mode display."""
        current_mode = self.mode_svc.get_mode()
        self.mode_combo.setCurrentText(current_mode.name)
    
    def _update_button_states(self):
        """Update button states based on mode."""
        current_mode = self.mode_svc.get_mode()
        
        if current_mode == AppMode.SAFE_MODE:
            self.keep_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.unsure_btn.setEnabled(False)
            self.lock_btn.setEnabled(False)
            self.undo_btn.setEnabled(False)
        else:
            self.keep_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.unsure_btn.setEnabled(True)
            self.lock_btn.setEnabled(True)
            self.undo_btn.setEnabled(True)
    
    # Export
    
    def _finalize_and_export(self):
        """Finalisieren und exportiere behaltene Bilder (streaming ZIP)."""
        from photo_cleaner.exporter import StreamingExporter

        cur = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE file_status = 'KEEP' AND is_deleted = 0"
        )
        keep_count = cur.fetchone()[0]

        decision = self._export_delete_workflow.build_export_decision(self.output_path, keep_count, t)
        if not decision.can_continue:
            if decision.level == "warning":
                QMessageBox.warning(self, decision.title, decision.message)
            else:
                QMessageBox.information(self, decision.title, decision.message)
            return

        reply = QMessageBox.question(
            self,
            decision.title,
            decision.message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cur = self.conn.execute(
                "SELECT path FROM files WHERE file_status = 'KEEP' AND is_deleted = 0"
            )
            keep_paths = [Path(row[0]) for row in cur.fetchall()]

            # Progress dialog
            progress = QProgressDialog(
                "Exportiere Bilder...",
                "Abbrechen",
                0,
                len(keep_paths),
                self,
            )
            progress.setWindowTitle(t("export_running"))
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            exporter = StreamingExporter(self.output_path)

            def on_progress(current: int, total: int, name: str) -> None:
                progress.setMaximum(total)
                progress.setValue(current)
                progress.setLabelText(f"{name}\n({current}/{total})")
                QApplication.processEvents()
                if progress.wasCanceled():
                    exporter.request_cancel()

            success_count, failure_count, errors, archive_path, cancelled = exporter.export_files_streaming(
                keep_paths,
                progress_callback=on_progress,
            )

            progress.close()

            delete_summary = ""
            if not cancelled:
                delete_paths = self.files.list_by_status([FileStatus.DELETE])
                if delete_paths:
                    delete_result = self.actions.ui_batch_delete(delete_paths)
                    if delete_result.get("ok"):
                        deleted_ids = delete_result.get("deleted_ids", [])
                        skipped_locked = delete_result.get("skipped_locked", [])
                        delete_summary = f"\nLoeschen angewendet: {len(deleted_ids)} Datei(en)."
                        if skipped_locked:
                            delete_summary += f" Uebersprungen (gesperrt): {len(skipped_locked)}."
                    else:
                        delete_summary = f"\nLoeschen fehlgeschlagen: {delete_result.get('message', 'Unbekannter Fehler')}"

            result_message = self._export_delete_workflow.build_export_result_message(
                success_count,
                failure_count,
                errors,
                archive_path,
                cancelled,
            )
            if delete_summary:
                result_message = type(result_message)(
                    level=result_message.level,
                    title=result_message.title,
                    message=result_message.message + delete_summary,
                )
            if result_message.level == "warning":
                QMessageBox.warning(self, result_message.title, result_message.message)
            else:
                QMessageBox.information(self, result_message.title, result_message.message)
            self.refresh_groups()
            self._update_progress()
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.critical(self, t("export_failed_title"), t("export_failed_message").format(error=e))

    def _confirm_delete_marked(self):
        """Bestätige und lösche alle als DELETE markierten Dateien (DB-Markierung)."""
        delete_paths = self.files.list_by_status([FileStatus.DELETE])
        decision = self._export_delete_workflow.build_delete_decision(len(delete_paths), t)
        if not decision.can_continue:
            QMessageBox.information(self, decision.title, decision.message)
            return

        reply = QMessageBox.question(
            self,
            decision.title,
            decision.message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        result = self.actions.ui_batch_delete(delete_paths)
        result_message = self._export_delete_workflow.build_delete_result_message(result, t)
        if result_message.level == "warning":
            QMessageBox.warning(self, result_message.title, result_message.message)
        else:
            QMessageBox.information(self, result_message.title, result_message.message)

        self.refresh_groups()
        self._update_progress()
    
    # Shortcuts
    
    def _wire_shortcuts(self):
        """Wire keyboard shortcuts."""
        # Status shortcuts (ohne Dialog, nur Markierung)
        QShortcut(QKeySequence("K"), self, activated=lambda: self._apply_status_to_selection(FileStatus.KEEP))
        QShortcut(QKeySequence("D"), self, activated=lambda: self._apply_status_to_selection(FileStatus.DELETE))
        QShortcut(QKeySequence("U"), self, activated=lambda: self._apply_status_to_selection(FileStatus.UNSURE))
        
        # Gruppenwechsel (Ctrl+Up/Down statt Ctrl+J/K)
        QShortcut(QKeySequence("Ctrl+Down"), self, activated=self._group_next)
        QShortcut(QKeySequence("Ctrl+Up"), self, activated=self._group_prev)
        
        # Weitere Shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search_box.setFocus())
        QShortcut(QKeySequence("?"), self, activated=self._show_help)
        # Session management shortcuts
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._session_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self._session_redo)
    
    def _group_next(self):
        """Select next group."""
        row = self.group_list.currentRow()
        if row < self.group_list.count() - 1:
            self.group_list.setCurrentRow(row + 1)
    
    def _group_prev(self):
        """Select previous group."""
        row = self.group_list.currentRow()
        if row > 0:
            self.group_list.setCurrentRow(row - 1)
    
    def _show_help(self):
        """Zeige Hilfe-Dialog."""
        msg = QMessageBox(self)
        msg.setWindowTitle(t("keyboard_shortcuts"))
        msg.setTextFormat(Qt.RichText)
        msg.setText(t("keyboard_shortcuts_detailed"))
        msg.exec()
    
    # Cleanup
    
    def closeEvent(self, event):
        """Handle window close - cleanup threads before exit."""
        # FIX (Feb 22, 2026): Stop thumbnail loader thread properly
        try:
            if hasattr(self, '_group_thumb_loader'):
                logger.info("[UI] Stopping thumbnail loader thread...")
                self._group_thumb_loader.stop()
                self._group_thumb_loader.wait(500)  # Wait max 500ms
                logger.info("[UI] Thumbnail loader thread stopped")
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"[UI] Error stopping thumbnail loader: {e}")

        try:
            if self._grid_thumb_loader:
                logger.info("[UI] Stopping grid thumbnail loader thread...")
                self._grid_thumb_loader.stop()
                self._grid_thumb_loader.wait(500)
                logger.info("[UI] Grid thumbnail loader thread stopped")
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"[UI] Error stopping grid thumbnail loader: {e}")
        
        try:
            self.conn.close()
        except (sqlite3.DatabaseError, sqlite3.OperationalError):
            logger.debug("Error closing database connection", exc_info=True)
            pass
        super().closeEvent(event)

    
    # ==================== Session Management ====================
    
    def _load_session(self) -> None:
        """Load previous session if it exists."""
        session = self.session_manager.load_session(self.db_path)
        
        if session:
            logger.info(f"Session loaded: {len(session.image_groups)} groups")
            
            # Restore group selection states
            for group_id, group_snapshot in session.image_groups.items():
                selected_set = set(group_snapshot.selected_indices)
                self._group_selection_state[group_id] = (selected_set, group_snapshot.last_selected_index)

            # Do not block startup with a modal dialog; this also avoids terminal
            # KeyboardInterrupt crashes while the dialog is waiting for input.
            try:
                if hasattr(self, "status_bar") and self.status_bar is not None:
                    self.status_bar.showMessage(
                        f"Session restored: {len(session.image_groups)} groups (Ctrl+Z/Ctrl+Y)",
                        6000,
                    )
            except Exception as e:
                logger.debug(f"Could not show session restore status message: {e}")
    
    def _setup_auto_save(self) -> None:
        """Setup timer for auto-saving session."""
        from PySide6.QtCore import QTimer
        
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save_session)
        self._auto_save_timer.start(self._auto_save_interval)
        
        logger.info(f"Auto-save enabled ({self._auto_save_interval}ms interval)")
    
    def _auto_save_session(self) -> None:
        """Auto-save current session (called by timer)."""
        # Convert group selection state to dict for saving
        image_groups = {}
        for group_id, (selected_indices, last_selected) in self._group_selection_state.items():
            image_groups[group_id] = {
                'selected_indices': list(selected_indices),
                'last_selected_index': last_selected,
            }
        
        if image_groups:
            self.session_manager.save_auto(image_groups, self.db_path)
    
    def _save_session(self, description: str) -> None:
        """Save current session with action description."""
        # Convert group selection state to dict for saving
        image_groups = {}
        for group_id, (selected_indices, last_selected) in self._group_selection_state.items():
            image_groups[group_id] = {
                'selected_indices': list(selected_indices),
                'last_selected_index': last_selected,
            }
        
        self.session_manager.save_session(
            image_groups=image_groups,
            description=description,
            db_path=self.db_path
        )
    
    def _session_undo(self) -> None:
        """Undo last action (Ctrl+Z)."""
        if not self.session_manager.can_undo():
            QMessageBox.information(self, t("undo_title"), t("nothing_to_undo"))
            return
        
        previous_session = self.session_manager.undo()
        if previous_session:
            self._restore_session_state(previous_session)
            logger.info(f"Undo: {previous_session.description}")
    
    def _session_redo(self) -> None:
        """Redo last undone action (Ctrl+Y)."""
        if not self.session_manager.can_redo():
            QMessageBox.information(self, t("redo_title"), t("nothing_to_redo"))
            return
        
        next_session = self.session_manager.redo()
        if next_session:
            self._restore_session_state(next_session)
            logger.info(f"Redo: {next_session.description}")
    
    def _restore_session_state(self, session) -> None:
        """Restore UI to a previous session state."""
        # Restore group selection states
        self._group_selection_state.clear()
        
        for group_id, group_snapshot in session.image_groups.items():
            selected_set = set(group_snapshot.selected_indices)
            self._group_selection_state[group_id] = (selected_set, group_snapshot.last_selected_index)
        
        # Refresh UI to show restored state
        if self.current_group:
            self._load_group_files(self.current_group)
            self._update_selection_ui()
        
        logger.info(f"Session restored: {session.description}")


def run_modern_ui(
    db_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    input_path: Optional[Path] = None,
    app: Optional[QApplication] = None,
    splash = None,
    mtcnn_status: Optional[dict] = None,
) -> None:
    """Starte die moderne Benutzeroberfläche.
    
    Args:
        db_path: Optionaler Pfad zur Datenbank (falls nicht angegeben, wird Standard geprüft)
        output_path: Optionaler Ausgabeordner (falls nicht angegeben, wird Ordner-Dialog angezeigt)
        input_path: Optionaler Eingabeordner (überspringt Start-Dialog, startet Auto-Analyse)
        app: Optionale existierende QApplication (falls None, wird neue erstellt)
        splash: Optionaler existierender Splash Screen (für run_ui.py Integration)
        mtcnn_status: Optional MTCNN initialization status dict {"available": bool, "error": str}
    """
    # Use existing app or create new one
    if app is None:
        app = QApplication.instance() or QApplication([])
    
    # Create splash only if not provided
    if splash is None:
        try:
            from PySide6.QtWidgets import QSplashScreen
            from datetime import datetime

            splash_image = Path(__file__).resolve().parent.parent.parent / "assets" / "splash.png"
            pixmap = QPixmap(str(splash_image)) if splash_image.exists() else QPixmap()

            splash = QSplashScreen(pixmap)
            splash.showMessage(
                "PhotoCleaner Testversion\nBuild: " + datetime.now().strftime("%Y-%m-%d") + "\nNur fuer Testzwecke",
                Qt.AlignBottom | Qt.AlignHCenter,
                Qt.white,
            )
            splash.show()
            app.processEvents()
        except (RuntimeError, AttributeError, ValueError):
            logger.warning("Could not create splash screen", exc_info=True)
            splash = None
    
    from PySide6.QtWidgets import QMessageBox

    # Create main window with error handling
    try:
        win = ModernMainWindow(db_path, output_path, input_path, mtcnn_status)
    except (RuntimeError, AttributeError, ValueError, sqlite3.DatabaseError) as e:
        logger.error(f"Failed to create main window: {e}", exc_info=True)
        import traceback
        logger.debug(traceback.format_exc())
        
        # Show error dialog
        error_msg = f"PhotoCleaner konnte nicht starten:\n\n{str(e)}"
        QMessageBox.critical(None, t("startup_error_title"), error_msg)
        
        if splash:
            try:
                splash.hide()
                splash.deleteLater()
            except (RuntimeError, AttributeError):
                logger.debug("Error cleaning up splash screen", exc_info=True)
                pass
        
        raise  # Re-raise for outer exception handler
    
    # Set window icon if available
    try:
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            win.setWindowIcon(QIcon(str(icon_path)))
    except (OSError, IOError):
        logger.debug("Could not load window icon", exc_info=True)
        pass
    
    win.show()

    # Finish splash screen (immediate, robust)
    if splash:
        try:
            splash.finish(win)
            splash.hide()
            splash.deleteLater()
            QApplication.processEvents()
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"Failed to finish splash: {e}; forcing hide", exc_info=True)
            try:
                splash.hide()
                splash.deleteLater()
                QApplication.processEvents()
            except (RuntimeError, AttributeError):
                logger.debug("Error during splash cleanup", exc_info=True)
                pass

    # Show MTCNN warning to user if initialization failed
    if mtcnn_status and not mtcnn_status.get("available", True):
        logger.warning("Showing MTCNN fallback warning dialog to user...")
        error_msg = mtcnn_status.get("error", "Unknown error")
        
        warning_dialog = QMessageBox(win)
        warning_dialog.setIcon(QMessageBox.Warning)
        warning_dialog.setWindowTitle("Gesichtserkennung Hinweis")
        warning_dialog.setText(
            "<b>Moderne Gesichtserkennung nicht verfügbar</b>"
        )
        warning_dialog.setInformativeText(
            "PhotoCleaner konnte die moderne Gesichtserkennung (MTCNN) nicht initialisieren.\n\n"
            f"Fehler: {error_msg}\n\n"
            "Das Programm funktioniert weiterhin, verwendet aber eine ältere Methode (Haar Cascade) "
            "zur Gesichtserkennung. Dies kann die Genauigkeit bei der Auswahl der besten Fotos "
            "mit Gesichtern beeinträchtigen.\n\n"
            "Die Analyse von Bildschärfe, Belichtung und anderen Qualitätsmerkmalen funktioniert normal."
        )
        warning_dialog.setStandardButtons(QMessageBox.Ok)
        warning_dialog.setDefaultButton(QMessageBox.Ok)
        
        # Keep a reference so dialog isn't garbage-collected
        win._mtcnn_warning_dialog = warning_dialog
        warning_dialog.show()
        QApplication.processEvents()

    # Run event loop (only if not already running)
    if QApplication.instance() and not QApplication.instance().property("running"):
        app.setProperty("running", True)
        app.exec()


if __name__ == "__main__":
    run_modern_ui()
