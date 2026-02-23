"""
PhotoCleaner Central Configuration and App Mode Management.

This module handles:
1. App Mode (DEBUG vs RELEASE)
2. Centralized Logging Setup
3. App Paths (relative to app directory or user data dir)
4. Feature Flags
"""

import os
import sys
import logging
from pathlib import Path
from enum import Enum
from typing import Optional


class AppMode(Enum):
    """Application Operating Mode."""
    DEBUG = "DEBUG"
    RELEASE = "RELEASE"


class AppConfig:
    """Centralized application configuration."""
    
    # === APP MODE ===
    _mode: Optional[AppMode] = None
    
    # === PATHS ===
    _app_dir: Optional[Path] = None
    _user_data_dir: Optional[Path] = None
    
    @classmethod
    def set_mode(cls, mode: AppMode) -> None:
        """Set application mode (DEBUG or RELEASE)."""
        cls._mode = mode
        cls._setup_logging()
    
    @classmethod
    def get_mode(cls) -> AppMode:
        """Get current application mode. Defaults to DEBUG if not set."""
        if cls._mode is None:
            debug_flag = os.environ.get("PHOTOCLEANER_DEBUG", "0").lower() in ("1", "true", "yes")
            if debug_flag:
                cls._mode = AppMode.DEBUG
            else:
                # Auto-detect from environment or default to RELEASE for EXE builds
                env_mode = os.environ.get("PHOTOCLEANER_MODE", "RELEASE").upper()
                cls._mode = AppMode(env_mode) if env_mode in ("DEBUG", "RELEASE") else AppMode.RELEASE
            cls._setup_logging()
        return cls._mode
    
    @classmethod
    def is_debug(cls) -> bool:
        """Check if running in DEBUG mode."""
        return cls.get_mode() == AppMode.DEBUG
    
    @classmethod
    def is_release(cls) -> bool:
        """Check if running in RELEASE mode."""
        return cls.get_mode() == AppMode.RELEASE
    
    # === APP PATHS ===
    
    @classmethod
    def set_app_dir(cls, path: Path) -> None:
        """Set application directory (where app is installed/running from)."""
        cls._app_dir = Path(path)
    
    @classmethod
    def get_app_dir(cls) -> Path:
        """Get application directory. Defaults to script directory."""
        if cls._app_dir is None:
            # If running as EXE, __file__ points to the EXE
            # If running as script, __file__ points to this file
            try:
                cls._app_dir = Path(sys.argv[0]).resolve().parent
            except (IndexError, TypeError):
                cls._app_dir = Path(__file__).resolve().parent.parent.parent
        return cls._app_dir
    
    @classmethod
    def set_user_data_dir(cls, path: Path) -> None:
        """Set user data directory (where databases, caches, etc. are stored)."""
        cls._user_data_dir = Path(path)
    
    @classmethod
    def get_user_data_dir(cls) -> Path:
        """Get user data directory. Defaults to platform-specific location."""
        if cls._user_data_dir is None:
            if sys.platform == "win32":
                base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            elif sys.platform == "darwin":
                base = Path.home() / "Library" / "Application Support"
            else:
                base = Path.home() / ".local" / "share"
            
            cls._user_data_dir = base / "PhotoCleaner"
            cls._user_data_dir.mkdir(parents=True, exist_ok=True)
        return cls._user_data_dir
    
    @classmethod
    def get_db_dir(cls) -> Path:
        """Get directory for database files."""
        db_dir = cls.get_user_data_dir() / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir
    
    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get directory for thumbnail cache."""
        cache_dir = cls.get_user_data_dir() / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    # === USER SETTINGS (JSON persistence) ===
    
    @classmethod
    def get_user_settings(cls) -> dict:
        """Get user settings from settings.json in user data dir."""
        import json
        settings_file = cls.get_user_data_dir() / "settings.json"
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load settings: {e}")
                return {}
        return {}
    
    @classmethod
    def set_user_settings(cls, settings: dict) -> None:
        """Save user settings to settings.json in user data dir."""
        import json
        settings_file = cls.get_user_data_dir() / "settings.json"
        
        try:
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")
    
    # === LOGGING ===
    
    _logger_configured = False
    
    @classmethod
    def _setup_logging(cls) -> None:
        """Setup central logging based on current mode."""
        if cls._logger_configured:
            return
        
        mode = cls.get_mode()
        
        # Root logger
        root_logger = logging.getLogger()
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        if mode == AppMode.DEBUG:
            # DEBUG MODE: Verbose logging with detailed information
            root_logger.setLevel(logging.DEBUG)
            
            # Console handler with detailed format
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            
            # Detailed format for DEBUG
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            file_level = logging.DEBUG
            
        else:
            # RELEASE MODE: Only errors and warnings to console
            root_logger.setLevel(logging.WARNING)
            
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.WARNING)
            
            # Minimal format for RELEASE (user-facing)
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            file_level = logging.INFO

        # File handler for both modes (use user data dir so EXE logs are available)
        try:
            log_path = cls.get_user_data_dir() / "PhotoCleaner.log"
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(file_level)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as exc:
            root_logger.warning(f"File logging disabled: {exc}")
        
        # Suppress noisy third-party loggers in both modes
        for logger_name in ["PIL", "PIL.Image", "PySide6", "PyQt6", "urllib3", "requests"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        
        cls._logger_configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with automatic configuration."""
        # Ensure logging is set up
        cls.get_mode()
        return logging.getLogger(name)


# Module-level convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return AppConfig.get_logger(name)


def is_debug() -> bool:
    """Check if in DEBUG mode."""
    return AppConfig.is_debug()


def is_release() -> bool:
    """Check if in RELEASE mode."""
    return AppConfig.is_release()
