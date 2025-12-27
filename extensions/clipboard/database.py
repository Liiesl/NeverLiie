# extensions/clipboard/database.py
import sqlite3
import os
import time
import hashlib
import json

class ClipboardDB:
    def __init__(self, db_path, media_dir):
        self.db_path = db_path
        self.media_dir = media_dir
        if not os.path.exists(self.media_dir): os.makedirs(self.media_dir)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS clipboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,         -- 'text', 'image', 'files'
                content_text TEXT,          -- Text search / Preview
                content_html TEXT,
                file_path TEXT,             -- For internal media OR external JSON list of paths
                content_hash TEXT UNIQUE,
                timestamp REAL
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON clipboard(timestamp DESC)")
        conn.commit()
        conn.close()

    def _get_hash(self, content):
        if isinstance(content, bytes): return hashlib.md5(content).hexdigest()
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    # --- HELPER METHODS ---
    def _entry_exists(self, content_hash):
        """Checks if a hash already exists in the database."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM clipboard WHERE content_hash = ?", (content_hash,))
        result = cur.fetchone()
        conn.close()
        return result is not None

    def _touch_entry(self, content_hash):
        """Updates the timestamp of an existing entry to now."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE clipboard SET timestamp = ? WHERE content_hash = ?", (time.time(), content_hash))
        conn.commit()
        conn.close()

    # --- Handle File References ---
    def add_file_ref(self, file_paths):
        """
        Stores a reference to files existing on disk.
        file_paths: list of strings ['C:/Users/img.jpg', 'C:/Users/vid.mp4']
        """
        # Sort paths to ensure consistent hash regardless of selection order
        file_paths.sort()
        
        # Serialize list to JSON string
        json_paths = json.dumps(file_paths)
        
        # Hash the PATHS, not the file content (fast)
        content_hash = self._get_hash(json_paths)
        
        # Create a preview string
        if len(file_paths) == 1:
            preview = f"File: {os.path.basename(file_paths[0])}"
        else:
            preview = f"Files: {os.path.basename(file_paths[0])} +{len(file_paths)-1} others"

        self._upsert('files', preview, None, json_paths, content_hash)

    def add_image(self, image_bytes):
        content_hash = self._get_hash(image_bytes)
        
        # Avoid writing duplicate images to disk
        if self._entry_exists(content_hash):
            self._touch_entry(content_hash)
            return

        filename = f"{content_hash}.png"
        file_path = os.path.join(self.media_dir, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            self._upsert('image', "[Image]", None, filename, content_hash)
        except Exception as e:
            print(f"Failed to save image: {e}")

    def add_text(self, text, html=None):
        content_hash = self._get_hash(text)
        self._upsert('text', text, html, None, content_hash)

    def _upsert(self, item_type, text, html, path, content_hash):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO clipboard (type, content_text, content_html, file_path, content_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET timestamp = excluded.timestamp
            """, (item_type, text, html, path, content_hash, time.time()))
            conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")
        finally:
            conn.close()

    def search(self, query="", limit=50):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if query:
            cur.execute("SELECT * FROM clipboard WHERE content_text LIKE ? ORDER BY timestamp DESC LIMIT ?", (f"%{query}%", limit))
        else:
            cur.execute("SELECT * FROM clipboard ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_full_path(self, filename):
        if not filename: return None
        return os.path.join(self.media_dir, filename)