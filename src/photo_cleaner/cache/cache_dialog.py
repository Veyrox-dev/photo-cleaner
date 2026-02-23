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
        self.setWindowTitle("Image Cache Management")
        self.setGeometry(100, 100, 600, 500)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout()
        
        # Statistics group
        stats_group = QGroupBox("Cache Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
        stats_layout.addWidget(self.stats_text)
        
        refresh_stats_btn = QPushButton("Refresh Statistics")
        refresh_stats_btn.clicked.connect(self._refresh_stats)
        stats_layout.addWidget(refresh_stats_btn)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # Cache control group
        control_group = QGroupBox("Cache Control")
        control_layout = QVBoxLayout()
        
        # Use cache checkbox
        self.use_cache_checkbox = QCheckBox("Enable caching (recommended)")
        self.use_cache_checkbox.setChecked(True)
        control_layout.addWidget(self.use_cache_checkbox)
        
        # Force reanalyze checkbox
        self.force_reanalyze_checkbox = QCheckBox(
            "Force re-analyze on next run (ignores cache)"
        )
        control_layout.addWidget(self.force_reanalyze_checkbox)
        
        control_layout.addSpacing(10)
        
        # Clear old entries
        clear_old_layout = QHBoxLayout()
        clear_old_label = QLabel("Clear entries older than:")
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setMinimum(1)
        self.days_spinbox.setMaximum(365)
        self.days_spinbox.setValue(30)
        self.days_spinbox.setSuffix(" days")
        clear_old_btn = QPushButton("Clear")
        clear_old_btn.clicked.connect(self._clear_old)
        
        clear_old_layout.addWidget(clear_old_label)
        clear_old_layout.addWidget(self.days_spinbox)
        clear_old_layout.addWidget(clear_old_btn)
        clear_old_layout.addStretch()
        control_layout.addLayout(clear_old_layout)
        
        # Clear all button
        clear_all_btn = QPushButton("Clear All Cache")
        clear_all_btn.setStyleSheet("background-color: #ffcccc;")
        clear_all_btn.clicked.connect(self._clear_all)
        control_layout.addWidget(clear_all_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setLayout(main_layout)
        
        # Load initial stats
        self._refresh_stats()
    
    def _refresh_stats(self):
        """Refresh and display cache statistics."""
        if not self.cache_manager:
            self.stats_text.setText("Cache manager not available")
            return
        
        try:
            size_info = self.cache_manager.get_cache_size()
            stats = self.cache_manager.get_cache_stats()
            
            lines = [
                "=" * 50,
                "IMAGE CACHE STATISTICS",
                "=" * 50,
                f"Total entries:      {size_info['entries']}",
                f"Average quality:    {size_info['avg_quality_score']:.2f}",
                f"Top-N entries:      {size_info['top_n_entries']}",
                f"Oldest entry:       {size_info['oldest_entry'] or 'N/A'}",
                f"Newest entry:       {size_info['newest_entry'] or 'N/A'}",
                "",
                "SESSION STATISTICS",
                "-" * 50,
                f"Cache hits:         {stats.cache_hits}",
                f"Cache misses:       {stats.cache_misses}",
                f"Cache updates:      {stats.cache_updates}",
            ]
            
            total = stats.cache_hits + stats.cache_misses
            if total > 0:
                hit_rate = stats.cache_hits / total * 100
                lines.append(f"Hit rate:           {hit_rate:.1f}%")
            
            lines.append("=" * 50)
            
            self.stats_text.setText("\n".join(lines))
        except Exception as e:
            self.stats_text.setText(f"Error retrieving statistics:\n{e}")
    
    def _clear_old(self):
        """Clear cache entries older than N days."""
        if not self.cache_manager:
            QMessageBox.warning(self, "Error", "Cache manager not available")
            return
        
        days = self.days_spinbox.value()
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Clear cache entries older than {days} days?\n\nThese images will need to be re-analyzed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cleared = self.cache_manager.clear_cache(older_than_days=days)
            QMessageBox.information(
                self,
                "Success",
                f"Cleared {cleared} cache entries.",
            )
            self._refresh_stats()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear cache:\n{e}")
    
    def _clear_all(self):
        """Clear entire cache."""
        if not self.cache_manager:
            QMessageBox.warning(self, "Error", "Cache manager not available")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Clear entire cache?\n\n"
            "All cached analysis results will be deleted.\n"
            "Next scan will require full re-analysis of all images.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cleared = self.cache_manager.clear_cache(older_than_days=None)
            QMessageBox.information(
                self,
                "Success",
                f"Cleared {cleared} cache entries.",
            )
            self._refresh_stats()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear cache:\n{e}")
    
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
            return "Cache: Disabled"
        
        try:
            size_info = self.cache_manager.get_cache_size()
            stats = self.cache_manager.get_cache_stats()
            
            hit_rate = 0
            if stats.cache_hits + stats.cache_misses > 0:
                hit_rate = stats.cache_hits / (stats.cache_hits + stats.cache_misses) * 100
            
            return (
                f"Cache: {size_info['entries']} entries | "
                f"Hits: {stats.cache_hits} | "
                f"Hit rate: {hit_rate:.0f}%"
            )
        except (KeyError, ValueError, OSError):
            logger.debug("Cache stats retrieval failed", exc_info=True)
            return "Cache: Error retrieving status"
