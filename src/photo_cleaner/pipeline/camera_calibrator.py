"""
PHASE 4 TASK 1: ML-Based Camera Calibration

Learn camera-specific sharpness factors from user behavior.
Instead of hardcoded profiles, train from actual user decisions (kept vs deleted).

Architecture:
- CameraCalibrator: Main class for learning camera profiles
- Statistics: Per-camera (kept_count, deleted_count, avg_sharpness_kept, avg_sharpness_deleted)
- Training: camera_factor = avg_sharpness_kept / avg_sharpness_deleted
- Storage: SQLite table camera_profiles_learned
- Fallback: Use Phase 3 hardcoded profiles if insufficient data (<5 samples)
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CameraStatistics:
    """Statistics for a specific camera model."""
    
    camera_model: str
    kept_count: int = 0
    deleted_count: int = 0
    avg_sharpness_kept: float = 0.0
    avg_sharpness_deleted: float = 0.0
    
    @property
    def total_samples(self) -> int:
        """Total images analyzed for this camera."""
        return self.kept_count + self.deleted_count
    
    @property
    def keep_rate(self) -> float:
        """Percentage of images kept for this camera."""
        if self.total_samples == 0:
            return 0.0
        return (self.kept_count / self.total_samples) * 100.0
    
    @property
    def learned_factor(self) -> Optional[float]:
        """Compute learned sharpness factor from statistics.
        
        Returns:
            Calibration factor or None if insufficient data (<5 samples)
        """
        if self.total_samples < 5:
            return None  # Insufficient data, use fallback
        
        if self.avg_sharpness_deleted == 0:
            return 1.0  # Avoid division by zero
        
        # Factor represents how much sharper kept images are vs deleted
        # Higher factor = more selective (kept images much sharper than deleted)
        factor = self.avg_sharpness_kept / self.avg_sharpness_deleted
        
        # Clamp to reasonable range (0.5 to 2.0)
        return max(0.5, min(2.0, factor))


class CameraCalibrator:
    """PHASE 4 TASK 1: Learn camera profiles from user behavior.
    
    Instead of hardcoded sharpness factors for each phone, learn them from:
    1. User decisions (which images were kept vs deleted)
    2. Actual sharpness values
    3. Generate per-camera calibration factors
    
    Database schema (camera_profiles_learned table):
    CREATE TABLE camera_profiles_learned (
        camera_model TEXT PRIMARY KEY,
        kept_count INTEGER,
        deleted_count INTEGER,
        avg_sharpness_kept REAL,
        avg_sharpness_deleted REAL,
        learned_factor REAL,
        last_updated TIMESTAMP,
        confidence_score REAL  -- Based on sample count
    )
    """
    
    # Minimum samples before trusting learned factor
    MIN_SAMPLES_FOR_LEARNING = 5
    
    # Maximum samples to weight (prevent very old data from dominating)
    MAX_SAMPLES_WEIGHT = 100
    
    def __init__(self, db_conn=None):
        """Initialize camera calibrator with optional database connection.
        
        Args:
            db_conn: SQLite database connection (optional)
        """
        self.db_conn = db_conn
        self._stats_cache: Dict[str, CameraStatistics] = {}
        self._init_db_table()
    
    def _init_db_table(self) -> None:
        """Create camera_profiles_learned table if it doesn't exist."""
        if not self.db_conn:
            return
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS camera_profiles_learned (
                    camera_model TEXT PRIMARY KEY,
                    kept_count INTEGER DEFAULT 0,
                    deleted_count INTEGER DEFAULT 0,
                    avg_sharpness_kept REAL DEFAULT 0.0,
                    avg_sharpness_deleted REAL DEFAULT 0.0,
                    learned_factor REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence_score REAL DEFAULT 0.0
                )
            """)
            self.db_conn.commit()
            logger.debug("[PHASE-4] camera_profiles_learned table initialized")
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to create camera_profiles_learned table: {e}")
    
    def record_image_decision(
        self,
        camera_model: str,
        sharpness_value: float,
        was_kept: bool,
    ) -> None:
        """Record user decision for image and update camera statistics.
        
        This is called after user marks image as KEEP or DELETE.
        Accumulates statistics for learning.
        
        Args:
            camera_model: Camera manufacturer (iPhone, Samsung, etc.)
            sharpness_value: Laplacian variance (sharpness score)
            was_kept: True if user kept/liked, False if deleted
        """
        if not self.db_conn:
            return
        
        try:
            cursor = self.db_conn.cursor()
            
            # Get or create statistics record
            cursor.execute(
                "SELECT * FROM camera_profiles_learned WHERE camera_model = ?",
                (camera_model,)
            )
            row = cursor.fetchone()
            
            if row is None:
                # New camera model
                cursor.execute("""
                    INSERT INTO camera_profiles_learned
                    (camera_model, kept_count, deleted_count, avg_sharpness_kept, avg_sharpness_deleted)
                    VALUES (?, 0, 0, 0.0, 0.0)
                """, (camera_model,))
            
            # Update statistics
            if was_kept:
                cursor.execute("""
                    UPDATE camera_profiles_learned
                    SET kept_count = kept_count + 1,
                        avg_sharpness_kept = 
                            CASE 
                                WHEN kept_count = 0 THEN ?
                                ELSE (avg_sharpness_kept * kept_count + ?) / (kept_count + 1)
                            END,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE camera_model = ?
                """, (sharpness_value, sharpness_value, camera_model))
            else:
                cursor.execute("""
                    UPDATE camera_profiles_learned
                    SET deleted_count = deleted_count + 1,
                        avg_sharpness_deleted = 
                            CASE 
                                WHEN deleted_count = 0 THEN ?
                                ELSE (avg_sharpness_deleted * deleted_count + ?) / (deleted_count + 1)
                            END,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE camera_model = ?
                """, (sharpness_value, sharpness_value, camera_model))
            
            # Recompute learned factor
            self._update_learned_factor(camera_model)
            
            self.db_conn.commit()
            self._stats_cache.clear()  # Invalidate cache
            
            logger.debug(f"[PHASE-4] Recorded decision for {camera_model}: "
                        f"{'KEPT' if was_kept else 'DELETED'} (sharpness={sharpness_value:.1f})")
            
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to record decision: {e}")
    
    def _update_learned_factor(self, camera_model: str) -> None:
        """Compute and store learned sharpness factor in database."""
        if not self.db_conn:
            return
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT kept_count, deleted_count, avg_sharpness_kept, avg_sharpness_deleted "
                "FROM camera_profiles_learned WHERE camera_model = ?",
                (camera_model,)
            )
            row = cursor.fetchone()
            
            if not row:
                return
            
            kept_count, deleted_count, avg_kept, avg_deleted = row
            total = kept_count + deleted_count
            
            # Compute factor
            if total < self.MIN_SAMPLES_FOR_LEARNING:
                learned_factor = None  # Insufficient data
                confidence = 0.0
            else:
                if avg_deleted == 0:
                    learned_factor = 1.0
                else:
                    factor = avg_kept / avg_deleted
                    learned_factor = max(0.5, min(2.0, factor))
                
                # Confidence: more samples = higher confidence
                # Max out at 100 samples for reasonable ratio
                confidence = min(100.0, total) / 100.0 * 100.0
            
            cursor.execute("""
                UPDATE camera_profiles_learned
                SET learned_factor = ?, confidence_score = ?
                WHERE camera_model = ?
            """, (learned_factor, confidence, camera_model))
            
            self.db_conn.commit()
            
            if learned_factor:
                logger.info(f"[PHASE-4] {camera_model}: Learned factor={learned_factor:.2f} "
                           f"(samples={total}, confidence={confidence:.0f}%)")
            
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to update learned factor: {e}")
    
    def get_learned_factor(self, camera_model: str) -> Optional[float]:
        """Get learned sharpness factor for camera model.
        
        Returns:
            Learned factor if sufficient data, None otherwise (use fallback)
        """
        if not self.db_conn:
            return None
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT learned_factor FROM camera_profiles_learned WHERE camera_model = ?",
                (camera_model,)
            )
            row = cursor.fetchone()
            
            if row and row[0] is not None:
                return row[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to get learned factor: {e}")
            return None
    
    def get_statistics(self, camera_model: str) -> Optional[CameraStatistics]:
        """Get accumulated statistics for camera model.
        
        Returns:
            CameraStatistics or None if no data
        """
        if not self.db_conn:
            return None
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT camera_model, kept_count, deleted_count, "
                "avg_sharpness_kept, avg_sharpness_deleted "
                "FROM camera_profiles_learned WHERE camera_model = ?",
                (camera_model,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return CameraStatistics(
                camera_model=row[0],
                kept_count=row[1],
                deleted_count=row[2],
                avg_sharpness_kept=row[3],
                avg_sharpness_deleted=row[4],
            )
        except (ValueError, IndexError, TypeError):
            logger.debug("Failed to parse camera statistics row", exc_info=True)
            return None
    
    def get_all_statistics(self) -> Dict[str, CameraStatistics]:
        """Get statistics for all calibrated cameras.
        
        Returns:
            Dict mapping camera_model to CameraStatistics
        """
        if not self.db_conn:
            return {}
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT camera_model, kept_count, deleted_count, "
                "avg_sharpness_kept, avg_sharpness_deleted "
                "FROM camera_profiles_learned"
            )
            rows = cursor.fetchall()
            
            return {
                row[0]: CameraStatistics(
                    camera_model=row[0],
                    kept_count=row[1],
                    deleted_count=row[2],
                    avg_sharpness_kept=row[3],
                    avg_sharpness_deleted=row[4],
                )
                for row in rows
            }
        except (ValueError, IndexError, TypeError):
            logger.debug("Failed to fetch all camera statistics", exc_info=True)
            return {}
    
    def track_generational_trend(self, camera_type: str) -> dict:
        """PHASE 4 TASK 5: Analyze generational improvements for camera type.
        
        Tracks how image quality metrics have evolved across device generations.
        For example, iPhone 12 vs iPhone 13 vs iPhone 14 vs iPhone 15.
        
        Args:
            camera_type: Camera manufacturer (iPhone, Samsung, Pixel, etc.)
            
        Returns:
            Dict with generational analysis:
            {
                "camera_type": "iPhone",
                "generations": [
                    {"generation": "iPhone-12", "avg_keep_rate": 0.65, "avg_sharpness": 45.2},
                    {"generation": "iPhone-13", "avg_keep_rate": 0.68, "avg_sharpness": 47.1},
                    ...
                ],
                "trend": "improving" | "declining" | "stable"
            }
        """
        if not self.db_conn:
            return {}
        
        try:
            cursor = self.db_conn.cursor()
            
            # Query camera profiles that match this camera type
            cursor.execute("""
                SELECT camera_model, kept_count, deleted_count,
                       avg_sharpness_kept, avg_sharpness_deleted, last_updated
                FROM camera_profiles_learned
                WHERE camera_model LIKE ?
                ORDER BY last_updated ASC
            """, (f"{camera_type}%",))
            
            rows = cursor.fetchall()
            
            if not rows:
                return {"camera_type": camera_type, "generations": [], "trend": "no_data"}
            
            # Analyze trends
            generations = []
            for row in rows:
                camera_model, kept, deleted, avg_sharp_kept, avg_sharp_del, timestamp = row
                total = kept + deleted
                
                if total == 0:
                    continue
                
                keep_rate = kept / total
                avg_sharpness = (avg_sharp_kept + avg_sharp_del) / 2 if avg_sharp_del > 0 else avg_sharp_kept
                
                generations.append({
                    "generation": camera_model,
                    "avg_keep_rate": round(keep_rate, 3),
                    "avg_sharpness": round(avg_sharpness, 1),
                    "samples": total,
                    "timestamp": timestamp,
                })
            
            # Determine trend
            if len(generations) >= 2:
                keep_rates = [g["avg_keep_rate"] for g in generations]
                sharpness_values = [g["avg_sharpness"] for g in generations]
                
                # Calculate trend: if last is higher than first → improving
                keep_rate_trend = keep_rates[-1] - keep_rates[0]
                sharpness_trend = sharpness_values[-1] - sharpness_values[0]
                
                if keep_rate_trend > 0.05 or sharpness_trend > 2.0:
                    trend = "improving"
                elif keep_rate_trend < -0.05 or sharpness_trend < -2.0:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            logger.info(f"[PHASE-4] Generational trend for {camera_type}: {trend}")
            
            return {
                "camera_type": camera_type,
                "generations": generations,
                "trend": trend,
            }
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to analyze generational trend: {e}")
            return {"camera_type": camera_type, "generations": [], "trend": "error"}
    
    def get_generation_quality_delta(self, camera_type: str) -> Optional[float]:
        """PHASE 4 TASK 5: Get quality improvement between generations.
        
        Computes average improvement (in percentage points) between successive generations.
        Useful for adjusting factors based on device age.
        
        Args:
            camera_type: Camera manufacturer
            
        Returns:
            Average quality improvement per generation or None
        """
        trend_data = self.track_generational_trend(camera_type)
        
        if not trend_data.get("generations") or len(trend_data["generations"]) < 2:
            return None
        
        generations = trend_data["generations"]
        deltas = []
        
        for i in range(1, len(generations)):
            prev_rate = generations[i-1]["avg_keep_rate"]
            curr_rate = generations[i]["avg_keep_rate"]
            delta = (curr_rate - prev_rate) * 100  # Convert to percentage points
            deltas.append(delta)
        
        if not deltas:
            return None
        
        avg_delta = sum(deltas) / len(deltas)
        logger.info(f"[PHASE-4] {camera_type}: Avg quality delta per generation: {avg_delta:.2f}pp")
        
        return avg_delta
    
    def get_statistics(self, camera_model: str) -> Optional[CameraStatistics]:
        """Get statistics for a specific camera.
        
        Returns:
            CameraStatistics or None if no data
        """
        if not self.db_conn:
            return None
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT camera_model, kept_count, deleted_count, "
                "avg_sharpness_kept, avg_sharpness_deleted "
                "FROM camera_profiles_learned WHERE camera_model = ?",
                (camera_model,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return CameraStatistics(
                camera_model=row[0],
                kept_count=row[1],
                deleted_count=row[2],
                avg_sharpness_kept=row[3],
                avg_sharpness_deleted=row[4],
            )
            
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to get statistics: {e}")
            return None
    
    def get_all_statistics(self) -> Dict[str, CameraStatistics]:
        """Get statistics for all cameras.
        
        Returns:
            Dict mapping camera_model to CameraStatistics
        """
        if not self.db_conn:
            return {}
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT camera_model, kept_count, deleted_count, "
                "avg_sharpness_kept, avg_sharpness_deleted "
                "FROM camera_profiles_learned "
                "ORDER BY kept_count + deleted_count DESC"  # Most data first
            )
            
            stats_dict = {}
            for row in cursor.fetchall():
                stats = CameraStatistics(
                    camera_model=row[0],
                    kept_count=row[1],
                    deleted_count=row[2],
                    avg_sharpness_kept=row[3],
                    avg_sharpness_deleted=row[4],
                )
                stats_dict[row[0]] = stats
            
            return stats_dict
            
        except Exception as e:
            logger.warning(f"[PHASE-4] Failed to get all statistics: {e}")
            return {}
    
    def print_calibration_report(self) -> str:
        """Generate human-readable calibration report.
        
        Returns:
            Formatted string with calibration status
        """
        stats = self.get_all_statistics()
        
        if not stats:
            return "[PHASE-4] No camera calibration data yet"
        
        report = "[PHASE-4] CAMERA CALIBRATION REPORT\n"
        report += "=" * 60 + "\n"
        
        for camera_model, stat in stats.items():
            factor = stat.learned_factor
            if factor:
                status = "✅ CALIBRATED"
            else:
                status = f"⏳ LEARNING ({stat.total_samples}/{self.MIN_SAMPLES_FOR_LEARNING} samples)"
            
            report += f"{camera_model:15s} {status:20s} Keep_Rate={stat.keep_rate:5.1f}%\n"
            report += f"  Samples: {stat.total_samples:3d} (kept={stat.kept_count:3d}, "
            report += f"deleted={stat.deleted_count:3d})\n"
            
            if factor:
                report += f"  Learned factor: {factor:.2f} "
                report += f"(sharp_kept={stat.avg_sharpness_kept:.0f}, "
                report += f"sharp_deleted={stat.avg_sharpness_deleted:.0f})\n"
        
        return report
