# extensions/clipboard/monitor.py
import threading
import time
import os
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer, QIODevice, QByteArray, QUrl, QMimeData
from .database import ClipboardDB
# You likely have a platform specific clipboard listener here (like pyclip or win32clipboard)
# For brevity, I'll focus on the data storage aspect.

class ClipboardMonitor:
    def __init__(self, db_path=None, media_dir=None):
        """
        :param db_path: Full path to sqlite file
        :param media_dir: Full path to folder for storing images
        """
        # If no paths provided, fallback to current directory (legacy support)
        if not db_path:
            base = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base, 'clipboard.db')
            media_dir = os.path.join(base, 'media')

        self.db = ClipboardDB(db_path, media_dir)
        
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.ignore_next = False

    def on_clipboard_change(self):
        if self.ignore_next:
            self.ignore_next = False
            return

        mime = self.clipboard.mimeData()

        # 1. PRIORITY: Files (References)
        if mime.hasUrls():
            urls = mime.urls()
            # Convert QUrl to local paths
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if paths:
                self.db.add_file_ref(paths)
                return # Stop processing (don't save as image or text)

        # 2. Images (Bitmaps / Screenshots)
        if mime.hasImage():
            image = self.clipboard.image()
            if not image.isNull():
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QIODevice.WriteOnly)
                image.save(buf, "PNG")
                self.db.add_image(ba.data())
                return

        # 3. Text
        if mime.hasText():
            text = mime.text().strip()
            if text:
                html = mime.html() if mime.hasHtml() else None
                self.db.add_text(text, html)

    # --- RESTORING CLIPBOARD ---
    
    def set_text(self, text):
        try:
            self.ignore_next = True
            self.clipboard.setText(text)
            self.db.add_text(text, None)
        except Exception as e:
            self.ignore_next = False
            print(f"Error setting text: {e}")
            raise

    def set_image(self, abs_path):
        """Load internal image from disk and set as bitmap."""
        from PySide6.QtGui import QImage
        try:
            img = QImage(abs_path)
            if img.isNull():
                raise ValueError(f"Failed to load image from {abs_path}")
            
            self.ignore_next = True
            self.clipboard.setImage(img)
            
            # Optionally update DB to track restoration
            # (consider consistency with set_text and set_files)
        except Exception as e:
            self.ignore_next = False
            print(f"Error setting image: {e}")
            raise

    def set_files(self, json_paths):
        """Restore file paths to clipboard so they can be pasted in Explorer."""
        try:
            paths = json.loads(json_paths)
            urls = [QUrl.fromLocalFile(p) for p in paths]
            
            mime = QMimeData()
            mime.setUrls(urls)
            
            try:
                self.ignore_next = True
                self.clipboard.setMimeData(mime)
                
                # Update timestamp in DB
                self.db.add_file_ref(paths)
            except Exception as db_error:
                self.ignore_next = False
                raise RuntimeError(f"Failed to update clipboard/database: {db_error}")
        except Exception as e:
            self.ignore_next = False
            print(f"Error restoring files: {e}")  # Consider using logging module
            raise
    def get_history(self, query="", limit=50):
        return self.db.search(query, limit)

    def get_image_path(self, filename):
        return self.db.get_full_path(filename)
        
    def set_text(self, text):
        import pyperclip
        pyperclip.copy(text)
        # Also update DB timestamp
        self.db.add_text(text)

    def set_files(self, json_files):
        # Implementation depends on platform (win32clipboard for Windows file drop)
        pass 

    def set_image(self, path):
        # Implementation depends on platform
        pass