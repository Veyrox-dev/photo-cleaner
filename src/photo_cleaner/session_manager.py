"""
Session Manager for PhotoCleaner

Handles persistence of selection state, undo/redo stack, and auto-save.

Structure:
- Session: Complete state snapshot at a point in time
- UndoRedoStack: Manages undo/redo history
- SessionManager: Coordinates persistence and in-memory state
"""

import json
import logging
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


@dataclass
class FileReference:
    """Safe file reference that works even if file path changes."""
    
    original_path: str  # Original full path
    relative_path: str  # Path relative to input folder
    file_hash: str      # First 1KB hash for identification
    file_size: int      # File size in bytes
    
    @classmethod
    def create(cls, file_path: Path, base_path: Optional[Path] = None) -> "FileReference":
        """Create FileReference from actual file."""
        try:
            relative = file_path.relative_to(base_path) if base_path else file_path
        except (ValueError, TypeError):
            relative = file_path
        
        # Get file hash (first 1KB)
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024)
                file_hash = hashlib.md5(content).hexdigest()
        except OSError:
            logger.debug(f"Failed to hash {file_path.name}", exc_info=True)
            file_hash = "unknown"
        
        try:
            file_size = file_path.stat().st_size
        except OSError:
            logger.debug(f"Failed to stat {file_path.name}", exc_info=True)
            file_size = 0
        
        return cls(
            original_path=str(file_path),
            relative_path=str(relative),
            file_hash=file_hash,
            file_size=file_size,
        )


@dataclass
class GroupSelectionSnapshot:
    """Selection state for a single group."""
    
    group_id: str
    selected_indices: List[int]  # Indices of selected images
    last_selected_index: int = -1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GroupSelectionSnapshot":
        """Create from dict."""
        return cls(
            group_id=data.get('group_id', ''),
            selected_indices=data.get('selected_indices', []) or [],
            last_selected_index=data.get('last_selected_index', -1),
            timestamp=data.get('timestamp', datetime.now().isoformat()),
        )


@dataclass
class SessionSnapshot:
    """Complete selection state snapshot at a point in time."""
    
    timestamp: str
    description: str  # User-facing description of action
    image_groups: Dict[str, GroupSelectionSnapshot]  # group_id -> selection state
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            'timestamp': self.timestamp,
            'description': self.description,
            'image_groups': {
                gid: snap.to_dict() 
                for gid, snap in self.image_groups.items()
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SessionSnapshot":
        """Create from dict."""
        return cls(
            timestamp=data['timestamp'],
            description=data['description'],
            image_groups={
                gid: GroupSelectionSnapshot.from_dict(snap)
                for gid, snap in data['image_groups'].items()
            },
        )


class UndoRedoStack:
    """Manages undo/redo history of session snapshots."""
    
    def __init__(self, max_history: int = 50):
        """
        Initialize undo/redo stack.
        
        Args:
            max_history: Maximum number of states to keep in history
        """
        self.max_history = max_history
        self.undo_stack: List[SessionSnapshot] = []
        self.redo_stack: List[SessionSnapshot] = []
    
    def push(self, snapshot: SessionSnapshot) -> None:
        """
        Add state to undo stack.
        
        Args:
            snapshot: State snapshot to add
        """
        self.undo_stack.append(snapshot)
        
        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        # Clear redo stack on new action
        self.redo_stack.clear()
    
    def undo(self) -> Optional[SessionSnapshot]:
        """
        Pop state from undo stack and move to redo stack.
        
        Returns:
            Previous state or None if nothing to undo
        """
        if not self.undo_stack:
            return None
        
        current = self.undo_stack.pop()
        self.redo_stack.append(current)
        
        # Return the previous state (now at top of undo stack)
        return self.undo_stack[-1] if self.undo_stack else None
    
    def redo(self) -> Optional[SessionSnapshot]:
        """
        Pop state from redo stack and move to undo stack.
        
        Returns:
            Next state or None if nothing to redo
        """
        if not self.redo_stack:
            return None
        
        snapshot = self.redo_stack.pop()
        self.undo_stack.append(snapshot)
        
        return snapshot
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 1
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0
    
    def get_undo_description(self) -> str:
        """Get description of undo action."""
        if len(self.undo_stack) >= 2:
            return self.undo_stack[-2].description
        return ""
    
    def get_redo_description(self) -> str:
        """Get description of redo action."""
        if self.redo_stack:
            return self.redo_stack[-1].description
        return ""


class SessionManager:
    """Manages session persistence and state."""
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize session manager.
        
        Args:
            sessions_dir: Directory for session files (default: ~/.photocleaner/sessions/)
        """
        if sessions_dir is None:
            sessions_dir = Path.home() / '.photocleaner' / 'sessions'
        
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session_file: Optional[Path] = None
        self.undo_redo_stack = UndoRedoStack()
        
        logger.info(f"SessionManager initialized: {self.sessions_dir}")
    
    def create_session(self, db_path: Path) -> SessionSnapshot:
        """
        Create new session for database.
        
        Args:
            db_path: Path to database file
        
        Returns:
            New empty session
        """
        self.current_session_file = self._get_session_file(db_path)
        
        session = SessionSnapshot(
            timestamp=datetime.now().isoformat(),
            description="Initial",
            image_groups={},
        )
        
        logger.info(f"Created new session: {self.current_session_file}")
        return session
    
    def load_session(self, db_path: Path) -> Optional[SessionSnapshot]:
        """
        Load existing session for database.
        
        Args:
            db_path: Path to database file
        
        Returns:
            Loaded session or None if doesn't exist
        """
        session_file = self._get_session_file(db_path)
        self.current_session_file = session_file
        
        if not session_file.exists():
            logger.info(f"No existing session for {db_path}")
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = SessionSnapshot.from_dict(data)
            
            # Initialize undo/redo stack with loaded session
            self.undo_redo_stack.push(session)
            
            logger.info(f"Loaded session: {session_file}")
            return session
        
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def save_session(
        self,
        image_groups: Dict[str, Dict[str, Any]],
        description: str = "User action",
        db_path: Optional[Path] = None
    ) -> bool:
        """
        Save current session state.
        
        Args:
            image_groups: Dict of group_id -> selection state
            description: Description of action
            db_path: Path to database (uses current if not provided)
        
        Returns:
            True if successful
        """
        if db_path and not self.current_session_file:
            self.current_session_file = self._get_session_file(db_path)
        
        if not self.current_session_file:
            logger.error("No session file configured")
            return False
        
        try:
            # Convert image_groups to snapshots
            snapshots = {}
            for group_id, selection_data in image_groups.items():
                if isinstance(selection_data, dict):
                    # From _group_selection_state: {group_id: (set[int], int)}
                    selected_indices = list(selection_data.get('selected_indices', []))
                    last_selected = selection_data.get('last_selected_index', -1)
                elif isinstance(selection_data, tuple):
                    # Direct tuple: (set[int], int)
                    selected_indices, last_selected = selection_data
                    selected_indices = list(selected_indices)
                else:
                    continue
                
                snapshots[group_id] = GroupSelectionSnapshot(
                    group_id=group_id,
                    selected_indices=selected_indices,
                    last_selected_index=last_selected,
                )
            
            session = SessionSnapshot(
                timestamp=datetime.now().isoformat(),
                description=description,
                image_groups=snapshots,
            )
            
            # Add to undo/redo stack
            self.undo_redo_stack.push(session)
            
            # Save to file
            with open(self.current_session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2)
            
            logger.debug(f"Saved session: {description}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def save_auto(
        self,
        image_groups: Dict[str, Any],
        db_path: Optional[Path] = None
    ) -> bool:
        """
        Auto-save session (less verbose logging).
        
        Args:
            image_groups: Dict of group selections
            db_path: Database path
        
        Returns:
            True if successful
        """
        return self.save_session(
            image_groups=image_groups,
            description="Auto-save",
            db_path=db_path
        )
    
    def undo(self) -> Optional[SessionSnapshot]:
        """
        Undo last action.
        
        Returns:
            Previous session state or None
        """
        return self.undo_redo_stack.undo()
    
    def redo(self) -> Optional[SessionSnapshot]:
        """
        Redo last undone action.
        
        Returns:
            Next session state or None
        """
        return self.undo_redo_stack.redo()
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.undo_redo_stack.can_undo()
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.undo_redo_stack.can_redo()
    
    def get_undo_description(self) -> str:
        """Get tooltip for undo button."""
        desc = self.undo_redo_stack.get_undo_description()
        return f"Rückgängig: {desc}" if desc else "Rückgängig"
    
    def get_redo_description(self) -> str:
        """Get tooltip for redo button."""
        desc = self.undo_redo_stack.get_redo_description()
        return f"Wiederherstellen: {desc}" if desc else "Wiederherstellen"
    
    def export_session(self, db_path: Path, export_path: Path) -> bool:
        """
        Export session to file for backup.
        
        Args:
            db_path: Database path
            export_path: Where to export session
        
        Returns:
            True if successful
        """
        session_file = self._get_session_file(db_path)
        
        if not session_file.exists():
            logger.error(f"No session file to export: {session_file}")
            return False
        
        try:
            with open(session_file, 'rb') as src:
                with open(export_path, 'wb') as dst:
                    dst.write(src.read())
            logger.info(f"Exported session to {export_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return False
    
    def import_session(self, import_path: Path, db_path: Path) -> bool:
        """
        Import session from file.
        
        Args:
            import_path: Path to import from
            db_path: Target database
        
        Returns:
            True if successful
        """
        session_file = self._get_session_file(db_path)
        
        try:
            with open(import_path, 'rb') as src:
                with open(session_file, 'wb') as dst:
                    dst.write(src.read())
            logger.info(f"Imported session from {import_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return False
    
    def clear_session(self, db_path: Path) -> bool:
        """
        Clear session for database.
        
        Args:
            db_path: Database path
        
        Returns:
            True if successful
        """
        session_file = self._get_session_file(db_path)
        
        try:
            if session_file.exists():
                session_file.unlink()
            self.undo_redo_stack = UndoRedoStack()
            logger.info(f"Cleared session for {db_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False
    
    def _get_session_file(self, db_path: Path) -> Path:
        """
        Get session file path for database.
        
        Args:
            db_path: Database path
        
        Returns:
            Path to session file
        """
        # Use database filename + hash of full path as session filename
        db_name = db_path.stem
        db_hash = hashlib.md5(str(db_path).encode()).hexdigest()[:8]
        session_filename = f"{db_name}_{db_hash}.session.json"
        
        return self.sessions_dir / session_filename
