"""
Cache Management Dialog for PhotoCleaner GUI.

Provides UI for managing image cache:
- View cache statistics
- Clear cache (all or by age)
- Configure cache behavior
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QMessageBox,
    QGroupBox,
    QTextEdit,
    QCheckBox,
)
from PyQt6.QtCore import Qt

from photo_cleaner.cache.image_cache_manager import ImageCacheManager
from photo_cleaner.i18n import t

logger = logging.getLogger(__name__)


class CacheManagementDialog(QDialog):
    """Dialog for managing image cache."""
    
    def __init__(self, cache_manager: Optional[ImageCacheManager], parent=None):
        """
        Initialize cache management dialog.
        
        Args:
            cache_manager: ImageCacheManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.cache_manager = cache_manager
        self.setWindowTitle(t("cache_dialog_title"))
        self.setGeometry(100, 100, 600, 500)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout()
        
        # Statistics group
        stats_group = QGroupBox(t("cache_stats_group"))
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
        stats_layout.addWidget(self.stats_text)
        
        refresh_stats_btn = QPushButton(t("cache_refresh_stats"))
        refresh_stats_btn.clicked.connect(self._refresh_stats)
        stats_layout.addWidget(refresh_stats_btn)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Cache control group
        control_group = QGroupBox(t("cache_control_group"))
        control_layout = QVBoxLayout()
        
        # Use cache checkbox
        self.use_cache_checkbox = QCheckBox(t("cache_enable_checkbox"))
        self.use_cache_checkbox.setChecked(True)
        control_layout.addWidget(self.use_cache_checkbox)
        
        # Force reanalyze checkbox
        self.force_reanalyze_checkbox = QCheckBox(
            t("cache_force_reanalyze_checkbox")
        )
        control_layout.addWidget(self.force_reanalyze_checkbox)
        
        control_layout.addSpacing(10)
        
        # Clear old entries
        clear_old_layout = QHBoxLayout()
        clear_old_label = QLabel(t("cache_clear_older_than"))
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setMinimum(1)
        self.days_spinbox.setMaximum(365)
        self.days_spinbox.setValue(30)
        self.days_spinbox.setSuffix(t("cache_days_suffix"))
        clear_old_btn = QPushButton(t("cache_clear_button"))
        clear_old_btn.clicked.connect(self._clear_old)
        
        clear_old_layout.addWidget(clear_old_label)
        clear_old_layout.addWidget(self.days_spinbox)
        clear_old_layout.addWidget(clear_old_btn)
        clear_old_layout.addStretch()
        control_layout.addLayout(clear_old_layout)
        
        # Clear all button
        clear_all_btn = QPushButton(t("cache_clear_all_button"))
        clear_all_btn.setStyleSheet("background-color: #ffcccc;")
        clear_all_btn.clicked.connect(self._clear_all)
        control_layout.addWidget(clear_all_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Close button
        close_btn = QPushButton(t("close"))
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setLayout(main_layout)
        
        # Load initial stats
        self._refresh_stats()
    
    def _refresh_stats(self):
        """Refresh and display cache statistics."""
        if not self.cache_manager:
            self.stats_text.setText(t("cache_manager_unavailable"))
            return
        
        try:
            size_info = self.cache_manager.get_cache_size()
            stats = self.cache_manager.get_cache_stats()
            
            lines = [
                "=" * 50,
                t("cache_stats_header"),
                "=" * 50,
                t("cache_total_entries").format(count=size_info['entries']),
                t("cache_avg_quality").format(value=size_info['avg_quality_score']),
                t("cache_topn_entries").format(count=size_info['top_n_entries']),
                t("cache_oldest_entry").format(value=size_info['oldest_entry'] or t("cache_not_available")),
                t("cache_newest_entry").format(value=size_info['newest_entry'] or t("cache_not_available")),
                "",
                t("cache_session_stats_header"),
                "-" * 50,
                t("cache_hits").format(count=stats.cache_hits),
                t("cache_misses").format(count=stats.cache_misses),
                t("cache_updates").format(count=stats.cache_updates),
            ]
            
            total = stats.cache_hits + stats.cache_misses
            if total > 0:
                hit_rate = stats.cache_hits / total * 100
                lines.append(t("cache_hit_rate").format(rate=hit_rate))
            
            lines.append("=" * 50)
            
            self.stats_text.setText("\n".join(lines))
        except Exception as e:
            self.stats_text.setText(t("cache_stats_error").format(error=e))
    
    def _clear_old(self):
        """Clear cache entries older than N days."""
        if not self.cache_manager:
            QMessageBox.warning(self, t("error"), t("cache_manager_unavailable"))
            return
        
        days = self.days_spinbox.value()
        reply = QMessageBox.question(
            self,
            t("cache_confirm_title"),
            t("cache_clear_old_confirm").format(days=days),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cleared = self.cache_manager.clear_cache(older_than_days=days)
            QMessageBox.information(
                self,
                t("success"),
                t("cache_cleared_count").format(count=cleared),
            )
            self._refresh_stats()
        except Exception as e:
            QMessageBox.critical(self, t("error"), t("cache_clear_failed_detail").format(error=e))
    
    def _clear_all(self):
        """Clear entire cache."""
        if not self.cache_manager:
            QMessageBox.warning(self, t("error"), t("cache_manager_unavailable"))
            return
        
        reply = QMessageBox.question(
            self,
            t("cache_confirm_title"),
            t("cache_clear_all_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cleared = self.cache_manager.clear_cache(older_than_days=None)
            QMessageBox.information(
                self,
                t("success"),
                t("cache_cleared_count").format(count=cleared),
            )
            self._refresh_stats()
        except Exception as e:
            QMessageBox.critical(self, t("error"), t("cache_clear_failed_detail").format(error=e))
    
    def get_cache_settings(self) -> dict:
        """
        Get cache settings from dialog.
        
        Returns:
            Dict with cache configuration
        """
        return {
            "use_cache": self.use_cache_checkbox.isChecked(),
            "force_reanalyze": self.force_reanalyze_checkbox.isChecked(),
        }


class CacheStatusWidget:
    """Simple status widget for cache information."""
    
    def __init__(self, cache_manager: Optional[ImageCacheManager]):
        """Initialize cache status widget."""
        self.cache_manager = cache_manager
    
    def get_status_text(self) -> str:
        """Get cache status as text."""
        if not self.cache_manager:
            return t("cache_status_disabled")
        
        try:
            size_info = self.cache_manager.get_cache_size()
            stats = self.cache_manager.get_cache_stats()
            
            hit_rate = 0
            if stats.cache_hits + stats.cache_misses > 0:
                hit_rate = stats.cache_hits / (stats.cache_hits + stats.cache_misses) * 100
            
            return (
                t("cache_status_summary").format(
                    entries=size_info['entries'],
                    hits=stats.cache_hits,
                    rate=hit_rate,
                )
            )
        except (KeyError, ValueError, OSError):
            logger.debug("Cache stats retrieval failed", exc_info=True)
            return t("cache_status_error")
