# extensions/clipboard/ui.py
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
                               QListWidgetItem, QLabel, QTextEdit, QFrame, 
                               QLabel)
from PySide6.QtCore import Qt, QSize, QDateTime
from PySide6.QtGui import QPixmap
from .monitor import ClipboardMonitor
from .input_sim import send_ctrl_v
import os, json

# Reuse Main Theme
THEME = {
    "bg": "#232324",
    "surface": "#38394B",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "accent": "#89b4fa",
    "border": "#45475a"
}

# Supported extensions for text preview
TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.json', '.js', '.html', '.css', '.xml', 
    '.yml', '.yaml', '.ini', '.cfg', '.log', '.bat', '.sh', '.cpp', 
    '.h', '.java', '.c', '.sql', '.csv', '.tsv'
}

class ClipboardView(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        from . import _monitor
        self.monitor = _monitor
        
        self.setup_ui()
        self.refresh_list("")
        
    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- LEFT: LIST ---
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setFixedWidth(300)
        self.list_widget.setIconSize(QSize(24, 24))
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ 
                background: transparent; 
                border-right: 1px solid {THEME['border']}; 
                outline: 0;
            }}
            QListWidget::item {{ 
                height: 56px; 
                color: {THEME['subtext']};
                padding-left: 10px;
                border-bottom: 1px solid #2a2a2c;
            }}
            QListWidget::item:selected {{ 
                background: {THEME['surface']}; 
                color: {THEME['text']};
                border-left: 2px solid {THEME['accent']};
            }}
        """)
        self.list_widget.currentItemChanged.connect(self.on_selection_change)
        self.list_widget.itemActivated.connect(self.handle_enter)
        
        # --- RIGHT: DETAILS ---
        self.detail_frame = QFrame()
        self.detail_layout = QVBoxLayout(self.detail_frame)
        self.detail_layout.setContentsMargins(20, 20, 20, 20)
        
        # Type Badge
        self.type_badge = QLabel("TEXT")
        self.type_badge.setStyleSheet(f"background: {THEME['accent']}; color: {THEME['bg']}; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        self.type_badge.setFixedSize(50, 20)

        # Header Time
        self.time_lbl = QLabel("")
        self.time_lbl.setStyleSheet(f"color: {THEME['subtext']}; font-size: 12px;")

        head_lay = QHBoxLayout()
        head_lay.addWidget(self.type_badge)
        head_lay.addStretch()
        head_lay.addWidget(self.time_lbl)
        
        # Content Viewers (Stack)
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setStyleSheet(f"background: transparent; border: none; color: {THEME['text']}; font-family: Consolas;")
        
        self.image_view = QLabel()
        self.image_view.setAlignment(Qt.AlignCenter)
        self.image_view.setStyleSheet("background: transparent;")
        self.image_view.hide()
        
        self.detail_layout.addLayout(head_lay)
        self.detail_layout.addWidget(self.text_view)
        self.detail_layout.addWidget(self.image_view)
        
        self.main_layout.addWidget(self.list_widget)
        self.main_layout.addWidget(self.detail_frame, 1)

    def filter_items(self, query):
        self.refresh_list(query)

    def refresh_list(self, query):
        self.list_widget.clear()
        results = self.monitor.get_history(query, limit=50)
        
        for row in results:
            item_type = row['type']
            content = row['content_text']
            
            display_text = ""
            if item_type == 'files':
                # content_text contains "File: filename.txt"
                display_text = f"📁 {content}"
            elif item_type == 'image':
                display_text = "📸 Image Capture"
            else:
                display_text = " ".join(content.split())[:35]
            
            w_item = QListWidgetItem(display_text)
            w_item.setData(Qt.UserRole, row)
            self.list_widget.addItem(w_item)
            
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _show_image(self, path):
        """Helper to display image given a path."""
        self.text_view.hide()
        self.image_view.show()
        if path and os.path.exists(path):
            pix = QPixmap(path)
            w = self.detail_frame.width() - 40 
            h = self.detail_frame.height() - 80 
            if w < 100: w = 400
            if h < 100: h = 400
            self.image_view.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.image_view.setText("Image file missing or unreadable.")

    def on_selection_change(self, current, previous):
        if not current: return
        data = current.data(Qt.UserRole)
        
        ts = QDateTime.fromSecsSinceEpoch(int(data['timestamp']))
        self.time_lbl.setText(ts.toString("MMM d, h:mm ap"))
        self.type_badge.setText(data['type'].upper())

        # Logic for File References
        if data['type'] == 'files':
            try:
                paths = json.loads(data['file_path'])
                
                # We only attempt preview if it's a single file
                if len(paths) == 1:
                    path = paths[0]
                    ext = os.path.splitext(path)[1].lower()
                    
                    # 1. IMAGE PREVIEW
                    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                        self._show_image(path)
                        return

                    # 2. TEXT/CODE PREVIEW
                    if ext in TEXT_EXTENSIONS:
                        try:
                            # Read first 4KB only for preview
                            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read(4096)
                                if len(content) == 4096: content += "\n\n... (preview truncated)"
                            
                            self.image_view.hide()
                            self.text_view.show()
                            self.text_view.setText(content)
                            return
                        except Exception as e:
                            # If read fails (permissions/encoding), fall through to list view
                            pass

                # 3. DEFAULT LIST VIEW
                self.image_view.hide()
                self.text_view.show()
                formatted = "Files:\n" + "\n".join([f"- {p}" for p in paths])
                self.text_view.setText(formatted)

            except Exception as e:
                self.image_view.hide()
                self.text_view.show()
                self.text_view.setText("Error reading file list.")

        # Logic for Direct Image Captures
        elif data['type'] == 'image':
            full_path = self.monitor.get_image_path(data['file_path'])
            self._show_image(full_path)
            
        # Logic for Clipboard Text
        else:
            self.image_view.hide()
            self.text_view.show()
            self.text_view.setText(data['content_text'])

    def handle_key(self, event):
        if event.key() == Qt.Key_Down:
            curr = self.list_widget.currentRow()
            if curr < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self.list_widget.currentRow()
            if curr > 0:
                self.list_widget.setCurrentRow(curr - 1)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.handle_enter()

    def handle_enter(self):
        item = self.list_widget.currentItem()
        if not item: return
        data = item.data(Qt.UserRole)
        
        self.context.hide_window()
        import time

        if data['type'] == 'files':
            self.monitor.set_files(data['file_path'])
        elif data['type'] == 'image':
            path = self.monitor.get_image_path(data['file_path'])
            if path: self.monitor.set_image(path)
        else:
            self.monitor.set_text(data['content_text'])
            
        time.sleep(0.15)
        send_ctrl_v()