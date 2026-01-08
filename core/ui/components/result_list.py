# core/ui/components/result_list.py
from PySide6.QtWidgets import (QStackedWidget, QListWidget, QListWidgetItem, 
                               QStyledItemDelegate, QStyle, QFileIconProvider, 
                               QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt, QSize, QRect, QFileInfo, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen
import time

from ..theme import THEME

from PySide6.QtGui import QPixmap # Add QPixmap to imports

class ResultDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.h_margin = 12
        self.v_margin = 6
        self.row_height = 64
        
        # We don't load icons here anymore. 
        # We expect the Container to inject a 'cache' dictionary.
        self.pixmap_cache = {} 

    def sizeHint(self, option, index):
        size_data = index.data(Qt.SizeHintRole)
        if size_data and size_data.isValid():
            return QSize(option.rect.width(), size_data.height())
        return QSize(option.rect.width(), self.row_height)

    def paint(self, painter, option, index):
        # No Profiler needed here anymore once fixed, but keep it for verification if you want
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        item_data = index.data(Qt.UserRole)
        if not item_data:
            painter.restore()
            return

        full_rect = option.rect
        card_rect = full_rect.adjusted(self.h_margin, self.v_margin, -self.h_margin, -self.v_margin)
        
        # --- 1. Background (Fast) ---
        if option.state & QStyle.State_Selected:
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(card_rect, 12, 12)
            
            # Accent Pill
            pill_rect = QRect(card_rect.left() + 4, card_rect.top() + 12, 4, card_rect.height() - 24)
            painter.setBrush(QColor(THEME["accent"]))
            painter.drawRoundedRect(pill_rect, 2, 2)

        if item_data.widget_factory:
            painter.restore()
            return

        # --- 2. Icon (Optimized) ---
        icon_size = 28
        icon_x = card_rect.left() + 20
        icon_y = card_rect.top() + (card_rect.height() - icon_size) // 2
        
        # DIRECT DRAWING: No file access, no scaling calculations.
        # We look up a pre-scaled QPixmap from the cache.
        if item_data.icon_path and item_data.icon_path in self.pixmap_cache:
            pixmap = self.pixmap_cache[item_data.icon_path]
            painter.drawPixmap(icon_x, icon_y, pixmap)
        else:
            # Fallback circle if no icon
            painter.setBrush(QColor(THEME["surface"]))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(icon_x, icon_y, icon_size, icon_size)

        # --- 3. Text (Optimized) ---
        text_left = icon_x + icon_size + 15
        text_width = card_rect.right() - text_left - 15
        
        # Title
        title_rect = QRect(text_left, card_rect.top() + 10, text_width, 22)
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.setPen(QColor(THEME["text"]))

        # FIXED: Use fontMetrics for elision
        fm_title = painter.fontMetrics()
        elided_title = fm_title.elidedText(item_data.name, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)
        
        # Description
        desc_rect = QRect(text_left, title_rect.bottom(), text_width, 18)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(THEME["subtext"] if not (option.state & QStyle.State_Selected) else "#bac2de"))

        # FIXED: Use fontMetrics for elision
        fm_desc = painter.fontMetrics()
        elided_desc = fm_desc.elidedText(item_data.description, Qt.ElideRight, desc_rect.width())
        painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_desc)
        
        painter.restore()

class ResultListContainer(QStackedWidget):
    item_activated = Signal(object) # Emits the item data object
    selection_changed = Signal(object) # Emits the item data object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_list()
        self.setup_style()
        
    def setup_list(self):
        self.result_list = QListWidget()
        self.delegate = ResultDelegate(self.result_list) # Keep reference to delegate
        self.result_list.setItemDelegate(self.delegate)
        self.result_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.result_list.setUniformItemSizes(False)
        self.result_list.setFocusPolicy(Qt.NoFocus)
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        self.result_list.itemActivated.connect(self._on_activate)
        self.result_list.currentItemChanged.connect(self._on_change)
        
        self.addWidget(self.result_list)
        self.icon_provider = QFileIconProvider() # Move provider here
        
    def setup_style(self):
        self.setStyleSheet(f"""
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
        """)

    def update_results(self, results):
        self.remove_custom_widget()
        
        # --- PRE-CACHING LOGIC ---
        for item in results:
            if item.icon_path and item.icon_path not in self.delegate.pixmap_cache:
                qicon = self.icon_provider.icon(QFileInfo(item.icon_path))
                pixmap = qicon.pixmap(28, 28) 
                self.delegate.pixmap_cache[item.icon_path] = pixmap
        # -------------------------

        current_row = self.result_list.currentRow()
        
        # --- CHANGE START ---
        # 1. Block signals so footer/selection logic doesn't freak out during clear()
        self.result_list.blockSignals(True)
        # 2. Disable viewport updates to prevent painting an empty white box
        self.result_list.setUpdatesEnabled(False)
        self.result_list.viewport().setUpdatesEnabled(False)
        
        self.result_list.clear()
        
        if not results:
            # Re-enable if empty
            self.result_list.blockSignals(False)
            self.result_list.viewport().setUpdatesEnabled(True)
            self.result_list.setUpdatesEnabled(True)
            return 0 

        total_height = 0
        for item_data in results:
            l_item = QListWidgetItem()
            l_item.setData(Qt.UserRole, item_data)
            
            height = item_data.height
            total_height += height
            
            l_item.setSizeHint(QSize(self.result_list.width(), height))
            self.result_list.addItem(l_item)
            
            if item_data.widget_factory:
                widget = item_data.widget_factory()
                self.result_list.setItemWidget(l_item, widget)
        
        # Restore selection
        if current_row >= 0 and current_row < len(results):
            self.result_list.setCurrentRow(current_row)
        else:
            self.result_list.setCurrentRow(0)
            
        # Re-enable everything
        self.result_list.viewport().setUpdatesEnabled(True)
        self.result_list.setUpdatesEnabled(True)
        self.result_list.blockSignals(False)

        # Force a single selection event so the footer updates to the correct item
        if self.result_list.currentItem():
             self._on_change(self.result_list.currentItem(), None)
        # --- CHANGE END ---
            
        return total_height

    def show_custom_widget(self, widget):
        self.addWidget(widget)
        self.setCurrentIndex(1)
        
    def remove_custom_widget(self):
        if self.count() > 1:
            w = self.widget(1)
            self.removeWidget(w)
            w.deleteLater()
        self.setCurrentIndex(0)
        
    def get_custom_widget(self):
        if self.count() > 1:
            return self.widget(1)
        return None

    def navigate(self, direction):
        if self.currentIndex() != 0: return
        count = self.result_list.count()
        if count == 0: return
        
        curr = self.result_list.currentRow()
        new_idx = max(0, min(curr + direction, count - 1))
        self.result_list.setCurrentRow(new_idx)

    def get_current_data(self):
        item = self.result_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def _on_activate(self, item):
        data = item.data(Qt.UserRole)
        self.item_activated.emit(data)

    def _on_change(self, current, previous):
        if current:
            data = current.data(Qt.UserRole)
            self.selection_changed.emit(data)