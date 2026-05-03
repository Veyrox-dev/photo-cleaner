#!/usr/bin/env python3
"""Phase 4 Exception Handling refactoring for cleanup_ui.py files."""

import re
from pathlib import Path

def refactor_cleanup_ui(file_path: str):
    """Refactor cleanup_ui.py exception handlers."""
    path = Path(file_path)
    content = path.read_text(encoding='utf-8')
    
    # Define replacements with their exact context
    replacements = [
        # Neueste zuerst sorting
        (
            r"""elif key == "Neueste zuerst":
            def _ctime\(g\):
                k = g\.get\("keep"\)
                try:
                    return Path\(k\)\.stat\(\)\.st_ctime
                except Exception:
                    return 0""",
            """elif key == "Neueste zuerst":
            def _ctime(g):
                k = g.get("keep")
                try:
                    return Path(k).stat().st_ctime
                except OSError:
                    logger.debug(f"Failed to stat {Path(k).name}", exc_info=True)
                    return 0"""
        ),
        # Älteste zuerst sorting
        (
            r"""elif key == "Älteste zuerst":
            def _ctime2\(g\):
                k = g\.get\("keep"\)
                try:
                    return Path\(k\)\.stat\(\)\.st_ctime
                except Exception:
                    return 0""",
            """elif key == "Älteste zuerst":
            def _ctime2(g):
                k = g.get("keep")
                try:
                    return Path(k).stat().st_ctime
                except OSError:
                    logger.debug(f"Failed to stat {Path(k).name}", exc_info=True)
                    return 0"""
        ),
        # _get_exif_date
        (
            """            if decoded in ("DateTimeOriginal", "DateTime"):
                        return val
        except Exception:
            return None

    def _parse_exif_datetime""",
            """            if decoded in ("DateTimeOriginal", "DateTime"):
                        return val
        except (OSError, AttributeError, TypeError):
            logger.debug(f"Failed to extract EXIF from {path.name}", exc_info=True)
            return None

    def _parse_exif_datetime"""
        ),
        # _parse_exif_datetime
        (
            """            y,m,d = date.split(":")
            return int(y), int(m), int(d)
        except Exception:
            return None

    def _organize_folder""",
            """            y,m,d = date.split(":")
            return int(y), int(m), int(d)
        except (ValueError, IndexError):
            logger.debug(f"Failed to parse EXIF datetime: {dt_str}", exc_info=True)
            return None

    def _organize_folder"""
        ),
        # keeper_override loop
        (
            """            for r in rows:
                try:
                    if len(r) > 2 and bool(r[2]):
                        keeper_override = Path(r[0])
                        break
                except Exception:
                    pass""",
            """            for r in rows:
                try:
                    if len(r) > 2 and bool(r[2]):
                        keeper_override = Path(r[0])
                        break
                except (IndexError, TypeError):
                    logger.debug("Failed to check keeper flag", exc_info=True)"""
        ),
        # Exact duplicate thumbnail
        (
            """            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except Exception:
                pass
            self.list_widget.addItem(item)

        # Similar pairs (pairwise)""",
            """            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to create thumbnail for exact match", exc_info=True)
            self.list_widget.addItem(item)

        # Similar pairs (pairwise)"""
        ),
        # Similar duplicate thumbnail
        (
            """            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except Exception:
                pass
            self.list_widget.addItem(item)

        if not self.groups:""",
            """            self.groups.append({"keep": best.path, "remove": to_remove, "title": title})
            item = QListWidgetItem(title)
            try:
                if best.path.exists():
                    t = get_thumbnail(best.path, (64, 64))
                    pix = QPixmap(str(t))
                    item.setIcon(QIcon(pix))
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to create thumbnail for similar match", exc_info=True)
            self.list_widget.addItem(item)

        if not self.groups:"""
        ),
        # preview load
        (
            """                else:
                    self.preview.setText("(file not found)")
            except Exception:
                self.preview.setText("(preview error)")

        self.delete_btn""",
            """                else:
                    self.preview.setText("(file not found)")
            except (OSError, TypeError, RuntimeError):
                logger.debug(f"Failed to load preview", exc_info=True)
                self.preview.setText("(preview error)")

        self.delete_btn"""
        ),
        # apply filter
        (
            """                try:
                    if g["keep"].exists():
                        pix = QPixmap(str(g["keep"])) .scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(pix))
                except Exception:
                    pass
                self.list_widget.addItem(item)

    def _mark_keep""",
            """                try:
                    if g["keep"].exists():
                        pix = QPixmap(str(g["keep"])) .scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(pix))
                except (OSError, TypeError, RuntimeError):
                    logger.debug(f"Failed to create filter thumbnail", exc_info=True)
                self.list_widget.addItem(item)

    def _mark_keep"""
        ),
        # deleted_at format
        (
            """            if deleted_at:
                try:
                    display += f" (gelöscht: {int(float(deleted_at))})"
                except Exception:
                    pass""",
            """            if deleted_at:
                try:
                    display += f" (gelöscht: {int(float(deleted_at))})"
                except (ValueError, TypeError):
                    logger.debug(f"Failed to format deleted_at timestamp", exc_info=True)"""
        ),
        # restore_selected
        (
            """            if trash_path and Path(trash_path).exists():
                try:
                    Path(orig_path).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(trash_path, orig_path)
                except Exception as e:
                    QMessageBox.warning(self, "Fehler", f"Wiederherstellung fehlgeschlagen: {e}")
                    continue""",
            """            if trash_path and Path(trash_path).exists():
                try:
                    Path(orig_path).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(trash_path, orig_path)
                except (OSError, PermissionError) as e:
                    logger.error(f"Restore failed: {e}", exc_info=True)
                    QMessageBox.warning(self, "Fehler", f"Wiederherstellung fehlgeschlagen: {e}")
                    continue"""
        ),
        # perm delete - unlink
        (
            """            # remove trash file
            try:
                if trash_path and Path(trash_path).exists():
                    Path(trash_path).unlink()
            except Exception:
                pass""",
            """            # remove trash file
            try:
                if trash_path and Path(trash_path).exists():
                    Path(trash_path).unlink()
            except OSError:
                logger.debug(f"Failed to delete trash file", exc_info=True)"""
        ),
        # perm delete - DB
        (
            """            # remove DB row
            try:
                cursor.execute("DELETE FROM files WHERE file_id = ?", (fid,))
            except Exception:
                pass""",
            """            # remove DB row
            try:
                cursor.execute("DELETE FROM files WHERE file_id = ?", (fid,))
            except sqlite3.Error:
                logger.debug(f"Failed to delete from database", exc_info=True)"""
        ),
    ]
    
    # Add imports if not present
    if "import sqlite3" not in content:
        content = content.replace("import os", "import os\nimport sqlite3")
    
    if 'logger = logging.getLogger' not in content:
        # Add logger after imports
        content = re.sub(
            r"(import logging\n\n)",
            r"\1logger = logging.getLogger(__name__)\n\n",
            content
        )
    
    # Apply replacements
    for old_pattern, new_text in replacements:
        content = re.sub(old_pattern, new_text, content, flags=re.MULTILINE | re.DOTALL)
    
    path.write_text(content, encoding='utf-8')
    print(f"✓ Refactored {path}")

if __name__ == "__main__":
    for file_path in [
        "src/photo_cleaner/ui/cleanup_ui.py",
    ]:
        refactor_cleanup_ui(file_path)
