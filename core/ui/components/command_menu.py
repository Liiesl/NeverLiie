# core/ui/components/command_menu.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont
from ..theme import THEME

class CommandMenu(QFrame):
    action_triggered = Signal(object) # Emits the Action object
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandMenu")
        self.setup_ui()
        self.setup_style()
        self.hide()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = QLabel("Actions")
        self.header.setFixedHeight(30)
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setIndent(10)
        layout.addWidget(self.header)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.NoFocus) 
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list_widget)

    def setup_style(self):
        self.setStyleSheet(f"""
            QFrame#CommandMenu {{
                background-color: {THEME['mantle']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
            }}
            QLabel {{
                color: {THEME['subtext']};
                font-size: 11px;
                font-weight: bold;
                background-color: transparent;
                border-bottom: 1px solid {THEME['surface']};
            }}
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                height: 32px;
                padding-left: 5px;
                color: {THEME['text']};
            }}
            QListWidget::item:selected {{
                background-color: {THEME['surface']};
                border-radius: 4px;
                color: {THEME['text']};
            }}
        """)

    def set_actions(self, actions):
        self.list_widget.clear()
        self.actions_map = {} # row -> action
        
        if not actions:
            return

        for i, action in enumerate(actions):
            item = QListWidgetItem(action.name)
            item.setSizeHint(QSize(200, 32))
            item.setFont(QFont("Segoe UI", 10))
            self.list_widget.addItem(item)
            self.actions_map[i] = action
            
        self.list_widget.setCurrentRow(0)
        
        # Auto-resize height based on content (max 5 items)
        count = len(actions)
        item_h = 32
        header_h = 30
        margin = 10
        total_h = header_h + (count * item_h) + margin
        self.setFixedHeight(min(total_h, 300))
        self.setFixedWidth(220)

    def navigate(self, direction):
        curr = self.list_widget.currentRow()
        count = self.list_widget.count()
        if count == 0: return
        
        new_idx = max(0, min(curr + direction, count - 1))
        self.list_widget.setCurrentRow(new_idx)

    def execute_current(self):
        row = self.list_widget.currentRow()
        if row in self.actions_map:
            action = self.actions_map[row]
            self.action_triggered.emit(action)
            self.hide()