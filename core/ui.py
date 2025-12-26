# core/ui.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, 
                               QListWidgetItem, QGraphicsDropShadowEffect, 
                               QStyledItemDelegate, QStyle, QFileIconProvider,
                               QLabel, QHBoxLayout, QFrame, QAbstractItemView,
                               QSizePolicy)
from PySide6.QtCore import (Qt, QSize, QRect, QTimer, QEvent, QFileInfo, 
                            QThread, Signal, Slot, QPropertyAnimation, 
                            QEasingCurve)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QIcon, QPixmap

# --- THEME CONFIGURATION ---
THEME = {
    "bg": "#232324",
    "mantle": "#2E2E30",
    "surface": "#38394B",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "accent": "#89b4fa",  # Blue
    "highlight": "#45475a",
    "border": "#45475a",
    "red": "#f38ba8"
}

# --- ICON GENERATOR ---
def create_app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(THEME["bg"]))
    painter.setPen(QPen(QColor(THEME["border"]), 2))
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QPen(QColor(THEME["accent"]), 4))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(20, 20, 16, 16)
    painter.drawLine(34, 34, 44, 44)
    painter.end()
    return QIcon(pixmap)

# --- WORKER THREAD ---
class QueryThread(QThread):
    results_ready = Signal(list, str)
    def __init__(self, core, text):
        super().__init__()
        self.core = core
        self.text = text
    def run(self):
        try:
            results = self.core.query(self.text)
            self.results_ready.emit(results, self.text)
        except:
            self.results_ready.emit([], self.text)

# --- DELEGATE ---
class ResultDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_provider = QFileIconProvider()
        self.h_margin = 12
        self.v_margin = 6
        self.row_height = 64

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.row_height)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        item_data = index.data(Qt.UserRole)
        if not item_data:
            painter.restore()
            return

        full_rect = option.rect
        card_rect = full_rect.adjusted(self.h_margin, self.v_margin, -self.h_margin, -self.v_margin)
        
        # Selection
        if option.state & QStyle.State_Selected:
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(card_rect, 12, 12)
            pill_rect = QRect(card_rect.left() + 4, card_rect.top() + 12, 4, card_rect.height() - 24)
            painter.setBrush(QColor(THEME["accent"]))
            painter.drawRoundedRect(pill_rect, 2, 2)

        # Icon
        icon_size = 28
        icon_x = card_rect.left() + 20
        icon_y = card_rect.top() + (card_rect.height() - icon_size) // 2
        icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
        
        if item_data.icon_path:
            icon = self.icon_provider.icon(QFileInfo(item_data.icon_path))
            icon.paint(painter, icon_rect, Qt.AlignCenter)
        else:
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(icon_rect)

        # Text
        text_left = icon_rect.right() + 15
        text_width = card_rect.right() - text_left - 15
        
        title_rect = QRect(text_left, card_rect.top() + 10, text_width, 22)
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.setPen(QColor(THEME["text"]))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                         painter.fontMetrics().elidedText(item_data.name, Qt.ElideRight, title_rect.width()))
        
        desc_rect = QRect(text_left, title_rect.bottom(), text_width, 18)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(THEME["subtext"] if not (option.state & QStyle.State_Selected) else "#bac2de"))
        painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                         painter.fontMetrics().elidedText(item_data.description, Qt.ElideMiddle, desc_rect.width()))
        
        painter.restore()

# --- WINDOW ---
class LauncherWindow(QWidget):
    # Dimensions
    VISUAL_WIDTH = 720
    VISUAL_COMPACT_HEIGHT = 100 # Search (60) + Footer (40)
    ROW_HEIGHT = 64
    MAX_VISIBLE_ITEMS = 6
    WINDOW_MARGIN = 50 
    
    def __init__(self, core_app):
        super().__init__()
        self.core = core_app
        self.query_thread = None
        self.target_height = 0 
        
        self.setup_ui()
        self.setup_styling()
        
        # Animation
        self.anim_geometry = QPropertyAnimation(self, b"geometry")
        # OutExpo is snappier than OutQuint
        self.anim_geometry.setEasingCurve(QEasingCurve.OutExpo) 
        self.anim_geometry.setDuration(250) # Slightly faster duration
        self.anim_geometry.finished.connect(self.on_animation_finished)

        # Timers & Inputs
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(100)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.search_input.textEdited.connect(self.on_text_edited)
        self.search_input.returnPressed.connect(self.execute_selection)
        self.result_list.itemActivated.connect(self.execute_selection)
        self.result_list.currentItemChanged.connect(self.update_footer)

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Initial Geometry
        self.compact_h_total = self.VISUAL_COMPACT_HEIGHT + (self.WINDOW_MARGIN * 2)
        total_w = self.VISUAL_WIDTH + (self.WINDOW_MARGIN * 2)
        self.resize(total_w, self.compact_h_total)
        
        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(self.WINDOW_MARGIN, self.WINDOW_MARGIN, self.WINDOW_MARGIN, self.WINDOW_MARGIN)
        
        # Visual Container
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)

        # 1. Search Bar
        self.search_frame = QFrame()
        self.search_frame.setObjectName("SearchFrame")
        self.search_frame.setFixedHeight(60)
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(20, 0, 20, 0)
        search_layout.setSpacing(15)
        
        self.search_icon_lbl = QLabel("🔎")
        self.search_icon_lbl.setObjectName("SearchIcon")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps, files, commands...")
        self.search_input.installEventFilter(self)
        
        search_layout.addWidget(self.search_icon_lbl)
        search_layout.addWidget(self.search_input)

        # 2. Separator
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setObjectName("Separator")
        self.line.hide()

        # 3. List
        self.result_list = QListWidget()
        self.result_list.setItemDelegate(ResultDelegate())
        self.result_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.result_list.setUniformItemSizes(True)
        self.result_list.setFocusPolicy(Qt.NoFocus)
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.result_list.hide()

        # 4. Footer
        self.footer = QFrame()
        self.footer.setObjectName("Footer")
        self.footer.setFixedHeight(40)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        self.footer_lbl = QLabel("Ready")
        self.footer_lbl.setObjectName("FooterLabel")
        footer_layout.addWidget(self.footer_lbl)
        
        self.inner_layout.addWidget(self.search_frame)
        self.inner_layout.addWidget(self.line)
        self.inner_layout.addWidget(self.result_list)
        self.inner_layout.addWidget(self.footer)
        
        self.main_layout.addWidget(self.container)
        
        # Shadow (Save reference to self.shadow)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setColor(QColor(0, 0, 0, 150))
        self.shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(self.shadow)

    def setup_styling(self):
        css = f"""
            QWidget {{ font-family: "Segoe UI", sans-serif; }}
            QFrame#Container {{
                background-color: {THEME['bg']};
                border-radius: 16px;
                border: 1px solid {THEME['border']};
            }}
            QFrame#SearchFrame {{ background: transparent; }}
            QLabel#SearchIcon {{ font-size: 20px; color: {THEME['accent']}; }}
            QLineEdit {{
                background: transparent; color: {THEME['text']};
                border: none; font-size: 20px; font-weight: 500;
                selection-background-color: {THEME['accent']}; selection-color: {THEME['bg']};
            }}
            QFrame#Separator {{
                color: {THEME['surface']}; background-color: {THEME['surface']};
                border: none; min-height: 1px; max-height: 1px;
            }}
            QListWidget {{ background: transparent; border: none; padding: 5px 0; }}
                        /* Custom Scrollbar */
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['surface']};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME['border']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QFrame#Footer {{ background: transparent; border-top: 1px solid transparent; }}
            QLabel#FooterLabel {{ color: {THEME['subtext']}; font-size: 12px; font-weight: 600; }}
        """
        self.setStyleSheet(css)
        
        # Snap geometry back to compact
        geo = self.geometry()
        geo.setHeight(self.compact_h_total)
        self.setGeometry(geo)

    def on_text_edited(self, text):
        if not text.strip():
            self.footer_lbl.setText("Start typing...")
            self.result_list.clear()
            self.animate_resize(0) 
            self.search_timer.stop()
        else:
            self.search_timer.start()

    def perform_search(self):
        text = self.search_input.text()
        if not text: return
        if self.query_thread and self.query_thread.isRunning():
            self.query_thread.quit()
            self.query_thread.wait()
        
        self.footer_lbl.setText("Searching...")
        self.query_thread = QueryThread(self.core, text)
        self.query_thread.results_ready.connect(self.handle_results)
        self.query_thread.start()

    @Slot(list, str)
    def handle_results(self, results, query_text):
        if query_text != self.search_input.text(): return

        self.result_list.clear()
        count = len(results)
        
        if count == 0:
            self.footer_lbl.setText("No results found.")
            self.animate_resize(0)
        else:
            for item in results:
                l_item = QListWidgetItem()
                l_item.setData(Qt.UserRole, item)
                self.result_list.addItem(l_item)
            
            self.result_list.setCurrentRow(0)
            self.update_footer()
            self.animate_resize(count)

    def animate_resize(self, item_count):
        current_geo = self.geometry()
        
        # Calculate Target Height
        if item_count == 0:
            visual_h = self.VISUAL_COMPACT_HEIGHT
            self.target_height = self.compact_h_total
        else:
            list_h = min(item_count * self.ROW_HEIGHT, self.MAX_VISIBLE_ITEMS * self.ROW_HEIGHT)
            list_h += 10 # padding
            visual_h = self.VISUAL_COMPACT_HEIGHT + list_h
            
            self.line.show()
            self.result_list.show()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid {THEME['surface']}; }}")

        target_total_h = visual_h + (self.WINDOW_MARGIN * 2)
        
        if current_geo.height() == target_total_h:
            if item_count == 0: self.on_animation_finished()
            return

        # --- KEY FIX: DISABLE SHADOW FOR PERFORMANCE ---
        self.shadow.setEnabled(False)

        # Calculate new Y position
        # Move TOP up by 15%, let BOTTOM expand 85%
        height_diff = target_total_h - current_geo.height()
        bias = 0.15 
        new_y = current_geo.y() - int(height_diff * bias)
        
        target_rect = QRect(current_geo.x(), new_y, current_geo.width(), target_total_h)
        
        self.anim_geometry.stop()
        self.anim_geometry.setStartValue(current_geo)
        self.anim_geometry.setEndValue(target_rect)
        self.anim_geometry.start()

    def on_animation_finished(self):
        # --- RE-ENABLE SHADOW ---
        self.shadow.setEnabled(True)

        if self.geometry().height() <= self.compact_h_total + 2:
            self.line.hide()
            self.result_list.hide()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid transparent; }}")

    def update_footer(self):
        count = self.result_list.count()
        if count == 0: return
        item = self.result_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            self.footer_lbl.setText(f"Open '{data.name}'")

    def execute_selection(self):
        current = self.result_list.currentItem()
        if not current: return
        result_item = current.data(Qt.UserRole)
        if result_item and result_item.action:
            if result_item.action.close_on_action:
                self.core.hide_window()
            result_item.action.handler()

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                self.nav(1)
                return True
            elif event.key() == Qt.Key_Up:
                self.nav(-1)
                return True
            elif event.key() == Qt.Key_PageDown:
                self.nav(5)
                return True
            elif event.key() == Qt.Key_PageUp:
                self.nav(-5)
                return True
            elif event.key() == Qt.Key_Escape:
                self.core.hide_window()
                return True
        return super().eventFilter(obj, event)

    def nav(self, direction):
        if not self.result_list.isVisible() or self.result_list.count() == 0: return
        curr = self.result_list.currentRow()
        new_idx = max(0, min(curr + direction, self.result_list.count() - 1))
        self.result_list.setCurrentRow(new_idx)