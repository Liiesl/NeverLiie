# extensions/clipboard/monitor.py
import os
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer, QIODevice, QByteArray, QUrl, QMimeData
from .database import ClipboardDB

class ClipboardMonitor:
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        db_path = os.path.join(base_dir, "clipboard_history.db")
        media_dir = os.path.join(base_dir, "media")
        
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
        self.ignore_next = True
        self.clipboard.setText(text)
        self.db.add_text(text)

    def set_image(self, abs_path):
        """Load internal image from disk and set as bitmap."""
        from PySide6.QtGui import QImage
        self.ignore_next = True
        img = QImage(abs_path)
        self.clipboard.setImage(img)

    def set_files(self, json_paths):
        """Restore file paths to clipboard so they can be pasted in Explorer."""
        try:
            paths = json.loads(json_paths)
            urls = [QUrl.fromLocalFile(p) for p in paths]
            
            mime = QMimeData()
            mime.setUrls(urls)
            
            self.ignore_next = True
            self.clipboard.setMimeData(mime)
            
            # Update timestamp in DB
            self.db.add_file_ref(paths)
        except Exception as e:
            print(f"Error restoring files: {e}")

    def get_history(self, query="", limit=50):
        return self.db.search(query, limit)
        
    def get_image_path(self, filename):
        return self.db.get_full_path(filename)