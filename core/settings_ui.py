# core/settings_ui.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QListWidget, QListWidgetItem, QCheckBox, 
                               QStackedWidget, QFrame, QPushButton, QScrollArea)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor

from .ui import THEME

class ExtensionRow(QFrame):
    def __init__(self, extension, settings_manager):
        super().__init__()
        self.extension = extension
        self.settings = settings_manager
        
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Text Info
        text_layout = QVBoxLayout()
        
        # --- FIX: Safe attribute access for Name ---
        # Tries to get 'name', falls back to 'id' (folder name), then Class Name
        display_name = getattr(extension, 'name', getattr(extension, 'id', extension.__class__.__name__))
        
        name_lbl = QLabel(display_name)
        name_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {THEME['text']};")
        
        # --- FIX: Safe attribute access for Description ---
        desc_text = getattr(extension, 'description', "No description provided.")
        desc_lbl = QLabel(desc_text)
        desc_lbl.setStyleSheet(f"font-size: 12px; color: {THEME['subtext']};")
        
        text_layout.addWidget(name_lbl)
        text_layout.addWidget(desc_lbl)
        
        # Checkbox (Toggle)
        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.PointingHandCursor)
        
        # Safely get ID (PluginManager should have assigned this, but we fallback safely)
        ext_id = getattr(extension, 'id', display_name)
        is_enabled = self.settings.is_extension_enabled(ext_id)
        
        self.checkbox.setChecked(is_enabled)
        self.checkbox.toggled.connect(self.on_toggle)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(self.checkbox)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['mantle']};
                border-radius: 8px;
                border: 1px solid {THEME['border']};
            }}
            QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 4px; border: 1px solid {THEME['subtext']}; }}
            QCheckBox::indicator:checked {{ background-color: {THEME['accent']}; border: 1px solid {THEME['accent']}; }}
        """)

    def on_toggle(self, checked):
        # Safely get ID
        ext_id = getattr(self.extension, 'id', self.extension.__class__.__name__)
        self.settings.set_extension_enabled(ext_id, checked)

class SettingsWindow(QWidget):
    def __init__(self, core_app):
        super().__init__()
        self.core = core_app
        self.setWindowTitle("Settings")
        self.resize(800, 600)
        
        # Stay on top to match Launcher behavior
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {THEME['accent']}; margin-bottom: 20px;")
        self.sidebar_layout.addWidget(title)

        self.btn_extensions = QPushButton("Extensions")
        self.btn_extensions.setCheckable(True)
        self.btn_extensions.setChecked(True)
        self.btn_extensions.setFixedHeight(40)
        self.sidebar_layout.addWidget(self.btn_extensions)
        self.sidebar_layout.addStretch()

        # --- Content Area ---
        self.content_area = QStackedWidget()
        
        self.ext_page = QWidget()
        ext_layout = QVBoxLayout(self.ext_page)
        ext_layout.setContentsMargins(40, 40, 40, 40)
        
        lbl_ext_header = QLabel("Manage Extensions")
        lbl_ext_header.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {THEME['text']}; margin-bottom: 10px;")
        ext_layout.addWidget(lbl_ext_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch() 
        
        scroll.setWidget(self.scroll_content)
        ext_layout.addWidget(scroll)

        self.content_area.addWidget(self.ext_page)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

    def refresh_extensions(self):
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for ext in self.core.pm.extensions:
            row = ExtensionRow(ext, self.core.settings)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row)

    def setup_style(self):
        self.setStyleSheet(f"""
            QWidget {{ font-family: "Segoe UI", sans-serif; background-color: {THEME['bg']}; }}
            QFrame {{ background-color: {THEME['mantle']}; }}
            QPushButton {{
                text-align: left; padding-left: 15px; border: none; border-radius: 6px;
                color: {THEME['subtext']}; font-size: 14px; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {THEME['surface']}; color: {THEME['text']}; }}
            QPushButton:checked {{ background-color: {THEME['surface']}; color: {THEME['accent']}; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {THEME['surface']}; border-radius: 4px; }}
        """)

    def show(self):
        self.refresh_extensions()
        super().show()