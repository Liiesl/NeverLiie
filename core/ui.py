# core/ui.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, 
                               QListWidgetItem, QGraphicsDropShadowEffect, 
                               QStyledItemDelegate, QStyle, QFileIconProvider,
                               QLabel, QHBoxLayout, QFrame, QAbstractItemView,
                               QSizePolicy, QStackedWidget)
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
    "accent": "#89b4fa",
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
        # Cache icons to prevent IO/RAM spikes during repaint
        self._icon_cache = {}

    def sizeHint(self, option, index):
        size_data = index.data(Qt.SizeHintRole)
        if size_data and size_data.isValid():
            return QSize(option.rect.width(), size_data.height())
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
        
        # Selection Background
        if option.state & QStyle.State_Selected:
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(card_rect, 12, 12)
            
            # Accent Pill
            pill_rect = QRect(card_rect.left() + 4, card_rect.top() + 12, 4, card_rect.height() - 24)
            painter.setBrush(QColor(THEME["accent"]))
            painter.drawRoundedRect(pill_rect, 2, 2)

        # Custom Widget Support (Inline)
        if item_data.widget_factory:
            painter.restore()
            return

        # --- STANDARD ITEM PAINTING ---
        icon_size = 28
        icon_x = card_rect.left() + 20
        icon_y = card_rect.top() + (card_rect.height() - icon_size) // 2
        icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
        
        if item_data.icon_path:
            if item_data.icon_path not in self._icon_cache:
                self._icon_cache[item_data.icon_path] = self.icon_provider.icon(QFileInfo(item_data.icon_path))
            
            icon = self._icon_cache[item_data.icon_path]
            icon.paint(painter, icon_rect, Qt.AlignCenter)
        else:
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(icon_rect)

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
    VISUAL_WIDTH = 800 # Wider for split view
    VISUAL_COMPACT_HEIGHT = 80 
    ROW_HEIGHT = 64
    MAX_VISIBLE_ITEMS = 6
    WINDOW_MARGIN = 50 
    
    def __init__(self, core_app):
        super().__init__()
        self.core = core_app
        self.query_thread = None
        
        # [FIX] Stable Anchor Variable
        # Stores the theoretical Y position of the window when in Compact Mode.
        # This prevents calculation drift during rapid animations.
        self.base_y_anchor = None
        
        self.setup_ui()
        self.setup_styling()
        
        self.anim_geometry = QPropertyAnimation(self, b"geometry")
        self.anim_geometry.setEasingCurve(QEasingCurve.OutExpo) 
        self.anim_geometry.setDuration(250)
        self.anim_geometry.finished.connect(self.on_animation_finished)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.search_input.textEdited.connect(self.on_text_edited)
        self.search_input.returnPressed.connect(self.execute_selection)
        
        self.result_list.itemActivated.connect(self.execute_selection)
        self.result_list.currentItemChanged.connect(self.update_footer)
        
        self.back_btn.mousePressEvent = self.go_back_click

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.compact_h_total = self.VISUAL_COMPACT_HEIGHT + (self.WINDOW_MARGIN * 2)
        total_w = self.VISUAL_WIDTH + (self.WINDOW_MARGIN * 2)
        self.resize(total_w, self.compact_h_total)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(self.WINDOW_MARGIN, self.WINDOW_MARGIN, self.WINDOW_MARGIN, self.WINDOW_MARGIN)
        
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)

        # 1. Header (Search Bar + Nav)
        self.search_frame = QFrame()
        self.search_frame.setObjectName("SearchFrame")
        self.search_frame.setFixedHeight(60)
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(15, 0, 20, 0)
        search_layout.setSpacing(10)
        
        self.back_btn = QLabel("←")
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.hide()

        self.search_icon_lbl = QLabel("🔎")
        self.search_icon_lbl.setObjectName("SearchIcon")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps, files, commands...")
        self.search_input.installEventFilter(self)
        
        self.context_lbl = QLabel("")
        self.context_lbl.setObjectName("ContextLabel")
        self.context_lbl.hide()

        search_layout.addWidget(self.back_btn)
        search_layout.addWidget(self.search_icon_lbl)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.context_lbl)

        # 2. Separator
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setObjectName("Separator")
        self.line.hide()

        # 3. Content Stack (Page 0: List, Page 1: Custom)
        self.content_stack = QStackedWidget()
        
        self.result_list = QListWidget()
        self.result_list.setItemDelegate(ResultDelegate())
        self.result_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.result_list.setUniformItemSizes(False)
        self.result_list.setFocusPolicy(Qt.NoFocus)
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        self.content_stack.addWidget(self.result_list)
        self.content_stack.hide()

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
        self.inner_layout.addWidget(self.content_stack)
        self.inner_layout.addWidget(self.footer)
        
        self.main_layout.addWidget(self.container)
        
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
                border-radius: 12px;
                border: 1px solid {THEME['border']};
            }}
            QFrame#SearchFrame {{ background: transparent; }}
            QLabel#SearchIcon {{ font-size: 20px; color: {THEME['subtext']}; }}
            
            QLabel#BackButton {{ 
                font-size: 24px; color: {THEME['text']}; font-weight: bold;
                padding: 4px; border-radius: 4px;
            }}
            QLabel#BackButton:hover {{ background: {THEME['surface']}; }}
            
            QLabel#ContextLabel {{ 
                color: {THEME['subtext']}; font-weight: bold; 
                background: {THEME['surface']}; padding: 4px 8px; border-radius: 6px;
            }}

            QLineEdit {{
                background: transparent; color: {THEME['text']};
                border: none; font-size: 20px; font-weight: 500;
                selection-background-color: {THEME['accent']}; selection-color: {THEME['bg']};
            }}
            
            QFrame#Separator {{
                color: {THEME['surface']}; background-color: {THEME['surface']};
                border: none; min-height: 1px; max-height: 1px;
            }}
            
            QListWidget {{ background: transparent; border: none; padding: 5px 0; outline: 0; }}
            QListWidget::item {{ border: none; padding: 0px; }}
            QListWidget::item:selected {{ background: transparent; }}
            
            QScrollBar:vertical {{
                border: none; background: transparent; width: 8px; margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['surface']}; min-height: 30px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {THEME['border']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            
            QFrame#Footer {{ background: transparent; border-top: 1px solid transparent; }}
            QLabel#FooterLabel {{ color: {THEME['subtext']}; font-size: 12px; font-weight: 600; }}
        """
        self.setStyleSheet(css)
        geo = self.geometry()
        geo.setHeight(self.compact_h_total)
        self.setGeometry(geo)

    def showEvent(self, event):
        # [FIX] Capture the anchor position when window appears.
        # We calculate 'base_y_anchor' as the Y position if the window were Compact.
        # This gives us a mathematically stable reference point for all animations.
        current_y = self.y()
        current_h = self.height()
        expansion_diff = current_h - self.compact_h_total
        
        # Reverse the expansion bias (15% up) to find the stable compact Y
        self.base_y_anchor = current_y + (expansion_diff * 0.15)
        super().showEvent(event)

    def go_back_click(self, event):
        self.core.exit_extension_mode()

    # --- MODE SWITCHING ---

    def set_mode_root(self):
        self.back_btn.hide()
        self.context_lbl.hide()
        self.search_icon_lbl.show()
        self.search_input.setPlaceholderText("Search apps, files, commands...")
        self.search_input.setText("")
        self.search_input.setFocus()
        
        if self.content_stack.count() > 1:
            w = self.content_stack.widget(1)
            self.content_stack.removeWidget(w)
            w.deleteLater()
            
        self.content_stack.setCurrentIndex(0) 
        self.result_list.clear()
        self.animate_resize(0, 0)

    def set_mode_extension(self, ext_name, custom_widget=None):
        self.back_btn.show()
        self.search_icon_lbl.hide()
        self.context_lbl.setText(ext_name)
        self.context_lbl.show()
        self.search_input.setText("")
        self.search_input.setPlaceholderText(f"Search in {ext_name}...")
        self.search_input.setFocus()

        if custom_widget:
            self.content_stack.addWidget(custom_widget)
            self.content_stack.setCurrentIndex(1)
            
            self.line.show()
            self.content_stack.show()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid {THEME['surface']}; }}")
            self.animate_geometry(600) 
        else:
            self.content_stack.setCurrentIndex(0)
            self.result_list.clear()
            self.perform_search() 

    # --- LOGIC ---

    def on_text_edited(self, text):
        if self.content_stack.currentIndex() == 1:
            widget = self.content_stack.currentWidget()
            if hasattr(widget, "filter_items"):
                widget.filter_items(text)
            return

        stripped = text.strip()
        lower_text = stripped.lower()
        allow_short = {"ai"} 
        should_search = len(stripped) >= 3 or lower_text in allow_short

        if not should_search:
            if len(stripped) == 0:
                self.footer_lbl.setText("Start typing...")
            else:
                self.footer_lbl.setText(f"Type {3 - len(stripped)} more chars...")
            
            self.result_list.clear()
            self.animate_resize(0, 0)
            self.search_timer.stop()
            return

        self.search_timer.start()

    def perform_search(self):
        if self.content_stack.currentIndex() != 0:
            return

        text = self.search_input.text()
        
        if self.query_thread and self.query_thread.isRunning():
            self.query_thread.quit()
            self.query_thread.wait()
        
        self.footer_lbl.setText("Searching...")
        self.query_thread = QueryThread(self.core, text)
        self.query_thread.results_ready.connect(self.handle_results)
        self.query_thread.start()

    @Slot(list, str)
    def handle_results(self, results, query_text):
        if self.content_stack.currentIndex() != 0: return
        if query_text != self.search_input.text(): return

        self.result_list.clear()
        count = len(results)
        total_content_height = 0
        
        if count == 0:
            self.footer_lbl.setText("No results found.")
            self.animate_resize(0, 0)
        else:
            for item_data in results:
                l_item = QListWidgetItem()
                l_item.setData(Qt.UserRole, item_data)
                
                height = item_data.height
                total_content_height += height
                
                l_item.setSizeHint(QSize(self.result_list.width(), height))
                self.result_list.addItem(l_item)
                
                if item_data.widget_factory:
                    widget = item_data.widget_factory()
                    self.result_list.setItemWidget(l_item, widget)
            
            self.result_list.setCurrentRow(0)
            self.update_footer()
            self.animate_resize(count, total_content_height)

    def animate_resize(self, item_count, content_height):
        if self.content_stack.currentIndex() == 1:
            return

        if item_count == 0:
            target_h = self.compact_h_total
            self.line.hide()
            self.content_stack.hide()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid transparent; }}")
        else:
            max_list_h = self.MAX_VISIBLE_ITEMS * self.ROW_HEIGHT
            list_h = min(content_height, max_list_h) + 10
            target_h = self.compact_h_total + list_h
            
            self.line.show()
            self.content_stack.show()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid {THEME['surface']}; }}")

        self.animate_geometry(target_h)

    def animate_geometry(self, target_h):
        current = self.geometry()
        target_total_h = target_h if target_h == self.compact_h_total else target_h + (self.WINDOW_MARGIN * 2)
        
        if current.height() == target_total_h:
            if target_h == self.compact_h_total: self.on_animation_finished()
            return

        self.shadow.setEnabled(False)
        self.result_list.setUpdatesEnabled(False)
        
        # [FIX] MATH STABILITY
        # Instead of calculating new_y based on the drifting 'current.y()',
        # we calculate it based on the stable 'self.base_y_anchor'.
        # Target Y = Anchor - (Expansion Amount * Bias)
        
        if self.base_y_anchor is None:
            self.base_y_anchor = current.y()

        expansion = target_total_h - self.compact_h_total
        bias = 0.15 # 15% Up, 85% Down
        
        target_y = int(self.base_y_anchor - (expansion * bias))
        target_rect = QRect(current.x(), target_y, current.width(), target_total_h)
        
        self.anim_geometry.stop()
        self.anim_geometry.setStartValue(current)
        self.anim_geometry.setEndValue(target_rect)
        self.anim_geometry.start()

    def on_animation_finished(self):
        self.result_list.setUpdatesEnabled(True)
        self.shadow.setEnabled(True)
        
        if self.geometry().height() <= self.compact_h_total + 2:
            self.line.hide()
            self.content_stack.hide()
            self.footer.setStyleSheet(f"QFrame#Footer {{ border-top: 1px solid transparent; }}")

    def update_footer(self):
        if self.content_stack.currentIndex() == 0:
            count = self.result_list.count()
            if count == 0: return
            item = self.result_list.currentItem()
            if item:
                data = item.data(Qt.UserRole)
                self.footer_lbl.setText(f"Action: {data.name}")

    def execute_selection(self):
        if self.content_stack.currentIndex() == 1:
            widget = self.content_stack.currentWidget()
            if hasattr(widget, "handle_enter"):
                widget.handle_enter()
            return

        current = self.result_list.currentItem()
        if not current: return
        result_item = current.data(Qt.UserRole)
        if result_item and result_item.action:
            if result_item.action.close_on_action:
                self.core.hide_window()
            result_item.action.handler()

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.core.active_extension:
                    self.core.exit_extension_mode()
                    return True
                else:
                    self.core.hide_window()
                    return True

            if self.content_stack.currentIndex() == 1:
                widget = self.content_stack.currentWidget()
                if hasattr(widget, "handle_key"):
                    if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Backtab):
                        widget.handle_key(event)
                        return True

            if event.key() == Qt.Key_Down:
                self.nav(1)
                return True
            elif event.key() == Qt.Key_Up:
                self.nav(-1)
                return True
                
        return super().eventFilter(obj, event)

    def nav(self, direction):
        if self.content_stack.currentIndex() != 0: return
        if not self.content_stack.isVisible() or self.result_list.count() == 0: return
        
        curr = self.result_list.currentRow()
        new_idx = max(0, min(curr + direction, self.result_list.count() - 1))
        self.result_list.setCurrentRow(new_idx)