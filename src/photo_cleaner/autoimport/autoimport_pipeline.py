"""
AutoimportPipeline: Orchestrierung der Analyse-Pipeline für neue Bilder.

Verantwortung:
    - Validiert neue Bilder (Format, Quota, Existenz)
    - Triggert DuplicateFinder + RatingWorkerThread
    - Speichert Ergebnisse
    - Signalisiert UI-Updates
"""

import logging
import uuid
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QObject, Signal

from photo_cleaner.core.indexer import PhotoIndexer
from photo_cleaner.db.schema import Database
from photo_cleaner.duplicates.finder import DuplicateFinder
from photo_cleaner.ui.worker_threads.analysis_workers import RatingWorkerThread

logger = logging.getLogger(__name__)


class AutoimportPipeline(QObject):
    """
    Orchestriert die Analyse-Pipeline für neue Bilder.
    
    Workflow:
        1. Validiere Dateien (Format, Quota)
        2. Finde Duplikate (DuplicateFinder)
        3. Bewerte Qualität (RatingWorkerThread)
        4. Speichere Ergebnisse
        5. Signalisiere Completion
    """
    
    # Signale
    import_started = Signal(int)  # count: int
    import_progress = Signal(int, int)  # current: int, total: int
    import_completed = Signal(dict)  # result: dict
    import_error = Signal(str)  # error_message: str
    
    def __init__(self, db_path: Path, config, license_manager):
        """
        Initialisiert die Pipeline.
        
        Args:
            db_path: Path zur PhotoCleaner SQLite DB
            config: AppConfig-Instanz
            license_manager: Instanz des LicenseManager
        """
        super().__init__()
        self.db_path = db_path
        self.config = config
        self.license_manager = license_manager
        
        # [FILL: Import usage_tracker für FREE-Lizenz-Quota-Checks]
        # from photo_cleaner.license.usage_tracker import get_usage_tracker
        # self.usage_tracker = get_usage_tracker()
        self.usage_tracker = None
        
        self._is_running = False
        self._duplicate_finder = None
        self._rating_worker = None
        
        logger.debug("AutoimportPipeline initialisiert")
    
    def analyze_files(self, file_paths: list):
        """
        Startet die Analyse für neue Dateien.
        
        Args:
            file_paths: Liste von Dateipfaden (str) zur Analyse
        """
        if self._is_running:
            logger.warning("AutoimportPipeline: Analyse läuft bereits, ignoriere neue Anfrage")
            return
        
        if not file_paths:
            logger.info("AutoimportPipeline: Leere Dateiliste, keine Analyse")
            return
        
        # Validierung
        valid_files = self._validate_and_filter(file_paths)
        if not valid_files:
            logger.info("AutoimportPipeline: Keine gültigen Bilder nach Filterung")
            return
        
        self._is_running = True
        
        try:
            logger.info(f"AutoimportPipeline: Starte Analyse für {len(valid_files)} Bilder")
            self.import_started.emit(len(valid_files))

            indexing_stats = self._index_files(valid_files)
            
            # 1. Duplikate finden
            logger.info(f"AutoimportPipeline: Starten Duplikaterkennung")
            duplicates = self._find_duplicates(valid_files)
            
            # 2. Ratings durchführen
            logger.info(f"AutoimportPipeline: Starten Qualitätsbewertung")
            rating_info = self._rate_images(valid_files)
            
            # 3. Ergebnis zusammenfassen
            result = {
                "total_files": len(valid_files),
                "indexed_files": indexing_stats.get("hashed_files", 0),
                "cached_files": indexing_stats.get("cached_files", 0),
                "duplicates_found": len(duplicates),
                "duplicates": duplicates,
                "rating": rating_info,
                "timestamp": datetime.now().isoformat(),
                "source": "autoimport"
            }
            
            logger.info(f"AutoimportPipeline: Analyse abgeschlossen. "
                       f"{result['total_files']} Dateien, "
                       f"{result['duplicates_found']} Duplikate")
            
            self.import_completed.emit(result)
        
        except Exception as e:
            error_msg = f"Fehler in AutoimportPipeline: {e}"
            logger.error(error_msg, exc_info=True)
            self.import_error.emit(error_msg)
        
        finally:
            self._is_running = False
    
    def _validate_and_filter(self, file_paths: list) -> list:
        """
        Validiert Dateien: Format, Existenz, Quotas.
        
        Args:
            file_paths: Liste von Dateipfaden (str)
        
        Returns:
            Gefilterte Liste von gültigen Dateipfaden (str)
        """
        valid = []
        
        # 1. Format-Check
        for path_str in file_paths:
            path = Path(path_str)
            
            # Prüfe ob Datei existiert
            if not path.is_file():
                logger.debug(f"AutoimportPipeline: Datei nicht vorhanden: {path}")
                continue
            
            # Prüfe Bildformat (Whitelist)
            if not self._is_supported_format(path):
                logger.debug(f"AutoimportPipeline: Format nicht unterstützt: {path.suffix}")
                continue
            
            valid.append(str(path))
        
        # 2. Quota-Check (nur für FREE-Lizenzen)
        # [FILL: Integration mit usage_tracker]
        # if self.license_manager.license_type == LicenseType.FREE:
        #     can_scan, remaining = self.usage_tracker.can_scan(len(valid))
        #     if not can_scan:
        #         logger.warning(f"AutoimportPipeline: FREE-Quota überschritten. "
        #                        f"Begrenze auf {remaining} Bilder.")
        #         valid = valid[:remaining]
        
        logger.info(f"AutoimportPipeline: {len(valid)} gültige Bilder nach Filterung "
                   f"(von {len(file_paths)} ursprünglich)")
        
        return valid

    def _index_files(self, file_paths: list[str]) -> dict:
        """Index the imported files into the main DB using PhotoIndexer helpers."""
        logger.info(f"AutoimportPipeline._index_files(): {len(file_paths)} Dateien")

        db = Database(self.db_path)
        db.connect()
        indexer = PhotoIndexer(db, max_workers=None)
        scan_id = str(uuid.uuid4())[:8]
        paths = [Path(path_str) for path_str in file_paths]

        try:
            indexer._reactivate_scanned_files(paths)
            new_files, modified_files, unchanged_files = indexer._categorize_files(paths)
            files_to_hash = new_files + modified_files
            results_to_store: list[tuple[Path, dict]] = []

            total_to_hash = len(files_to_hash)
            for index, path in enumerate(files_to_hash, start=1):
                result = indexer._process_file(path)
                if result is not None:
                    results_to_store.append((path, result))
                self.import_progress.emit(index, max(1, total_to_hash))

            if results_to_store:
                indexer._batch_store_incremental_records(results_to_store, scan_id)

            duplicates_found = indexer._count_new_duplicates(results_to_store)
            return {
                "total_files": len(paths),
                "new_files": len(new_files),
                "modified_files": len(modified_files),
                "hashed_files": len(results_to_store),
                "cached_files": len(unchanged_files),
                "duplicates_found": duplicates_found,
            }
        finally:
            db.close()
    
    def _find_duplicates(self, file_paths: list) -> list:
        """
        Führt Duplikaterkennung durch.
        
        Args:
            file_paths: Liste von Dateipfaden zur Analyse
        
        Returns:
            Liste von erkannten Duplikaten: [{"path": "...", "duplicate_of": "...", "class": "A|B"}, ...]
        """
        logger.info(f"AutoimportPipeline._find_duplicates(): {len(file_paths)} Dateien")

        imported_paths = [str(Path(path_str)) for path_str in file_paths]
        if not imported_paths:
            return []

        db = Database(self.db_path)
        db.connect()
        try:
            finder = DuplicateFinder(db, phash_threshold=5)
            finder.build_groups()

            placeholders = ",".join("?" for _ in imported_paths)
            cursor = db.conn.execute(
                f"""
                SELECT d.group_id, COUNT(*) AS group_size
                FROM duplicates d
                WHERE d.group_id IN (
                    SELECT DISTINCT d2.group_id
                    FROM duplicates d2
                    JOIN files f2 ON f2.file_id = d2.file_id
                    WHERE f2.path IN ({placeholders})
                )
                GROUP BY d.group_id
                ORDER BY d.group_id
                """,
                imported_paths,
            )
            return [
                {"group_id": row[0], "group_size": int(row[1])}
                for row in cursor.fetchall()
            ]
        finally:
            db.close()
    
    def _rate_images(self, file_paths: list):
        """
        Führt Qualitätsbewertung durch.
        
        Args:
            file_paths: Liste von Dateipfaden zur Bewertung
        """
        logger.info(f"AutoimportPipeline._rate_images(): {len(file_paths)} Dateien")

        worker = RatingWorkerThread(
            self.db_path,
            top_n=3,
            mtcnn_status={"available": False, "error": "autoimport"},
        )
        rating_info: dict = {"rated": False, "warn": False}
        rating_errors: list[str] = []

        worker.progress.connect(lambda pct, _status: self.import_progress.emit(max(0, pct), 100))
        worker.finished.connect(lambda info: rating_info.update(info))
        worker.error.connect(lambda error_msg: rating_errors.append(error_msg))
        worker.run()

        if rating_errors:
            raise RuntimeError(rating_errors[-1])
        return rating_info
    
    def _save_rating_to_db(self, file_path: str, rating_data: dict):
        """
        Speichert Bewertungsergebnisse in der Datenbank.
        
        """
        logger.debug(f"AutoimportPipeline._save_rating_to_db(): {Path(file_path).name}")
        db = Database(self.db_path)
        db.connect()
        try:
            updates = []
            for column_name in (
                "quality_score",
                "sharpness_component",
                "lighting_component",
                "resolution_component",
                "face_quality_component",
            ):
                if column_name in rating_data:
                    updates.append((column_name, rating_data[column_name]))

            if not updates:
                return

            set_clause = ", ".join(f"{column_name} = ?" for column_name, _ in updates)
            params = [value for _, value in updates] + [str(Path(file_path))]
            db.conn.execute(
                f"UPDATE files SET {set_clause} WHERE path = ?",
                params,
            )
            db.conn.commit()
        finally:
            db.close()
    
    @staticmethod
    def _is_supported_format(path: Path) -> bool:
        """
        Prüft, ob ein Bildformat unterstützt ist.
        
        Args:
            path: Zu prüfende Datei
        
        Returns:
            True wenn Format unterstützt, False sonst
        """
        supported = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            '.raw', '.cr2', '.nef', '.arw', '.raf', '.dng', '.webp'
        }
        return path.suffix.lower() in supported
    
    def is_running(self) -> bool:
        """Gibt an, ob eine Analyse gerade läuft."""
        return self._is_running
    
    def stop(self):
        """Stoppt eine laufende Analyse (gracefully)."""
        if self._is_running:
            logger.info("AutoimportPipeline: Stoppe laufende Analyse")
            # [FILL: Signal Worker zum Stopp senden]
            self._is_running = False
