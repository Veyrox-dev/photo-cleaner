"""
Pipeline Results UI

Display duplicate groups with Top-N marking and deletion controls.
"""

import logging
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from photo_cleaner.db.schema import Database
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository
from photo_cleaner.services.mode_service import ModeService
from photo_cleaner.models.mode import AppMode

logger = logging.getLogger(__name__)


class PipelineResultsUI:
    """
    UI to display and manage pipeline results.
    
    Shows duplicate groups with:
    - Top-N images clearly marked as "KEEP"
    - Remaining images marked as "DELETE" (pending user confirmation)
    - Preview images
    - Batch delete button
    """
    
    def __init__(
        self,
        db: Database,
        parent: Optional[tk.Tk] = None,
    ):
        """
        Initialize pipeline results UI.
        
        Args:
            db: Database instance
            parent: Parent Tkinter window (creates new if None)
        """
        self.db = db
        self.file_repo = FileRepository(db.conn)
        self.mode_service = ModeService(db.conn)
        
        # Create window
        if parent is None:
            self.root = tk.Tk()
            self.root.title("PhotoCleaner - Pipeline Results")
            self.root.geometry("1200x800")
        else:
            self.root = parent
        
        self.groups = []
        self.current_group_idx = 0
        self.thumbnails = {}
        
        self._create_widgets()
        self._load_groups()
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Top bar with navigation
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(top_frame, text="Duplicate Groups:").pack(side=tk.LEFT, padx=5)
        
        self.group_label = ttk.Label(top_frame, text="0 / 0", font=("Arial", 12, "bold"))
        self.group_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="← Previous", command=self._prev_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Next →", command=self._next_group).pack(side=tk.LEFT, padx=5)
        
        # Main content area
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Top-N section (KEEP)
        keep_frame = ttk.LabelFrame(content_frame, text="✓ Top Images to KEEP", padding=10)
        keep_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas with scrollbar for top images
        self.keep_canvas = tk.Canvas(keep_frame, height=250)
        keep_scrollbar = ttk.Scrollbar(keep_frame, orient=tk.HORIZONTAL, command=self.keep_canvas.xview)
        self.keep_canvas.configure(xscrollcommand=keep_scrollbar.set)
        
        self.keep_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        keep_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.keep_frame_inner = ttk.Frame(self.keep_canvas)
        self.keep_canvas.create_window((0, 0), window=self.keep_frame_inner, anchor=tk.NW)
        
        # Delete section (remaining images)
        delete_frame = ttk.LabelFrame(content_frame, text="✗ Images to DELETE", padding=10)
        delete_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas with scrollbar for delete images
        self.delete_canvas = tk.Canvas(delete_frame, height=250)
        delete_scrollbar = ttk.Scrollbar(delete_frame, orient=tk.HORIZONTAL, command=self.delete_canvas.xview)
        self.delete_canvas.configure(xscrollcommand=delete_scrollbar.set)
        
        self.delete_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        delete_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.delete_frame_inner = ttk.Frame(self.delete_canvas)
        self.delete_canvas.create_window((0, 0), window=self.delete_frame_inner, anchor=tk.NW)
        
        # Bottom bar with actions
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Statistics
        self.stats_label = ttk.Label(
            action_frame,
            text="",
            font=("Arial", 10),
        )
        self.stats_label.pack(side=tk.LEFT, padx=10)
        
        # Action buttons
        ttk.Button(
            action_frame,
            text="🗑️ Delete All Marked Images in This Group",
            command=self._delete_group_files,
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="🗑️ Delete ALL Marked Images (All Groups)",
            command=self._delete_all_marked,
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="🔄 Refresh",
            command=self._load_groups,
        ).pack(side=tk.RIGHT, padx=5)
    
    def _load_groups(self):
        """Load duplicate groups from database."""
        cursor = self.db.conn.cursor()
        
        # Get all duplicate groups
        cursor.execute(
            """
            SELECT DISTINCT group_id
            FROM duplicates
            ORDER BY group_id
            """
        )
        
        group_ids = [row[0] for row in cursor.fetchall()]
        
        self.groups = []
        for group_id in group_ids:
            # Get files in group
            cursor.execute(
                """
                SELECT f.path, f.file_status, f.is_locked, f.overall_score
                FROM files f
                JOIN duplicates d ON f.file_id = d.file_id
                WHERE d.group_id = ?
                ORDER BY f.file_status DESC, f.overall_score DESC
                """,
                (group_id,)
            )
            
            files = []
            for row in cursor.fetchall():
                files.append({
                    "path": Path(row[0]),
                    "status": FileStatus(row[1]),
                    "locked": bool(row[2]),
                    "score": row[3] or 0.0,
                })
            
            if files:
                self.groups.append({
                    "group_id": group_id,
                    "files": files,
                })
        
        # Show first group
        self.current_group_idx = 0
        self._display_current_group()
        self._update_stats()
    
    def _display_current_group(self):
        """Display the current group."""
        if not self.groups:
            self.group_label.config(text="No groups found")
            return
        
        group = self.groups[self.current_group_idx]
        self.group_label.config(
            text=f"{self.current_group_idx + 1} / {len(self.groups)} (Group {group['group_id']})"
        )
        
        # Clear previous thumbnails
        for widget in self.keep_frame_inner.winfo_children():
            widget.destroy()
        for widget in self.delete_frame_inner.winfo_children():
            widget.destroy()
        
        self.thumbnails.clear()
        
        # Separate KEEP and DELETE files
        keep_files = [f for f in group["files"] if f["status"] == FileStatus.KEEP]
        delete_files = [f for f in group["files"] if f["status"] == FileStatus.DELETE]
        
        # Display KEEP files
        for i, file_info in enumerate(keep_files):
            self._create_thumbnail(
                file_info,
                self.keep_frame_inner,
                i,
                is_keep=True,
            )
        
        # Display DELETE files
        for i, file_info in enumerate(delete_files):
            self._create_thumbnail(
                file_info,
                self.delete_frame_inner,
                i,
                is_keep=False,
            )
        
        # Update canvas scroll regions
        self.keep_frame_inner.update_idletasks()
        self.keep_canvas.config(scrollregion=self.keep_canvas.bbox("all"))
        
        self.delete_frame_inner.update_idletasks()
        self.delete_canvas.config(scrollregion=self.delete_canvas.bbox("all"))
    
    def _create_thumbnail(self, file_info: dict, parent: ttk.Frame, index: int, is_keep: bool):
        """Create thumbnail widget for a file."""
        frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
        frame.grid(row=0, column=index, padx=5, pady=5)
        
        # Load and display image
        try:
            img = Image.open(file_info["path"])
            img.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(img)
            
            self.thumbnails[str(file_info["path"])] = photo  # Keep reference
            
            label = ttk.Label(frame, image=photo)
            label.pack()
        except Exception as e:
            logger.warning(f"Failed to load thumbnail: {e}")
            ttk.Label(frame, text="[Image not available]", width=20).pack()
        
        # File info
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status badge
        status_color = "green" if is_keep else "red"
        status_text = "✓ KEEP" if is_keep else "✗ DELETE"
        status_label = tk.Label(
            info_frame,
            text=status_text,
            bg=status_color,
            fg="white",
            font=("Arial", 10, "bold"),
            padx=5,
        )
        status_label.pack()
        
        # Score
        ttk.Label(
            info_frame,
            text=f"Score: {file_info['score']:.1f}",
            font=("Arial", 9),
        ).pack()
        
        # Filename (truncated)
        name = file_info["path"].name
        if len(name) > 25:
            name = name[:22] + "..."
        ttk.Label(info_frame, text=name, font=("Arial", 8)).pack()
        
        # Lock indicator
        if file_info["locked"]:
            ttk.Label(
                info_frame,
                text="🔒 LOCKED",
                font=("Arial", 8, "bold"),
                foreground="orange",
            ).pack()
    
    def _prev_group(self):
        """Navigate to previous group."""
        if self.current_group_idx > 0:
            self.current_group_idx -= 1
            self._display_current_group()
    
    def _next_group(self):
        """Navigate to next group."""
        if self.current_group_idx < len(self.groups) - 1:
            self.current_group_idx += 1
            self._display_current_group()
    
    def _delete_group_files(self):
        """Delete all marked files in current group."""
        if not self.groups:
            return
        
        group = self.groups[self.current_group_idx]
        delete_files = [
            f["path"] for f in group["files"]
            if f["status"] == FileStatus.DELETE and not f["locked"]
        ]
        
        if not delete_files:
            messagebox.showinfo("Info", "No files marked for deletion in this group.")
            return
        
        # Confirm
        response = messagebox.askyesno(
            "Confirm Deletion",
            f"Delete {len(delete_files)} file(s) from this group?\n\n"
            "Files will be moved to trash/recycle bin.",
        )
        
        if response:
            self._perform_delete(delete_files)
            self._load_groups()  # Refresh
    
    def _delete_all_marked(self):
        """Delete all marked files across all groups."""
        # Check mode
        mode = self.mode_service.get_mode()
        if mode != AppMode.CLEANUP_MODE:
            messagebox.showerror(
                "Permission Denied",
                "Deletion only allowed in CLEANUP_MODE.\n\n"
                f"Current mode: {mode.value}"
            )
            return
        
        # Get all files marked DELETE
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT path FROM files
            WHERE file_status = 'DELETE' AND is_locked = 0
            """
        )
        
        delete_files = [Path(row[0]) for row in cursor.fetchall()]
        
        if not delete_files:
            messagebox.showinfo("Info", "No files marked for deletion.")
            return
        
        # Confirm
        response = messagebox.askyesno(
            "Confirm Deletion",
            f"Delete {len(delete_files)} file(s) across all groups?\n\n"
            "This cannot be undone (files go to trash).",
        )
        
        if response:
            self._perform_delete(delete_files)
            self._load_groups()  # Refresh
    
    def _perform_delete(self, paths: list[Path]):
        """
        Perform actual deletion (move to trash).
        
        Args:
            paths: List of file paths to delete
        """
        import send2trash
        
        success_count = 0
        failed_count = 0
        
        for path in paths:
            try:
                if path.exists():
                    send2trash.send2trash(str(path))
                    
                    # Update database
                    cursor = self.db.conn.cursor()
                    cursor.execute(
                        "UPDATE files SET is_deleted = 1, deleted_at = unixepoch() WHERE path = ?",
                        (str(path),)
                    )
                    self.db.conn.commit()
                    
                    success_count += 1
                else:
                    logger.warning(f"File not found: {path}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to delete {path}: {e}")
                failed_count += 1
        
        messagebox.showinfo(
            "Deletion Complete",
            f"Successfully deleted: {success_count}\n"
            f"Failed: {failed_count}"
        )
    
    def _update_stats(self):
        """Update statistics label."""
        cursor = self.db.conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN file_status = 'KEEP' THEN 1 ELSE 0 END) as keep_count,
                SUM(CASE WHEN file_status = 'DELETE' THEN 1 ELSE 0 END) as delete_count,
                SUM(CASE WHEN is_locked = 1 THEN 1 ELSE 0 END) as locked_count
            FROM files
            WHERE file_id IN (SELECT file_id FROM duplicates)
            """
        )
        
        row = cursor.fetchone()
        keep = row[0] or 0
        delete = row[1] or 0
        locked = row[2] or 0
        
        self.stats_label.config(
            text=f"Total: {len(self.groups)} groups | "
            f"Keep: {keep} | Delete: {delete} | Locked: {locked}"
        )
    
    def run(self):
        """Run the UI main loop."""
        self.root.mainloop()


def show_pipeline_results(db: Database):
    """
    Show pipeline results UI.
    
    Args:
        db: Database instance
    """
    ui = PipelineResultsUI(db)
    ui.run()
