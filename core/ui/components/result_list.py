# core/ui/components/result_list.py
from PySide6.QtWidgets import (QStackedWidget, QListWidget, QListWidgetItem, 
                               QStyledItemDelegate, QStyle, QFileIconProvider, 
                               QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt, QSize, QRect, QFileInfo, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen

from ..theme import THEME

class ResultDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_provider = QFileIconProvider()
        self.h_margin = 12
        self.v_margin = 6
        self.row_height = 64
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

        if item_data.widget_factory:
            painter.restore()
            return

        # Icon
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

class ResultListContainer(QStackedWidget):
    item_activated = Signal(object) # Emits the item data object
    selection_changed = Signal(object) # Emits the item data object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_list()
        self.setup_style()
        
    def setup_list(self):
        self.result_list = QListWidget()
        self.result_list.setItemDelegate(ResultDelegate(self.result_list))
        self.result_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.result_list.setUniformItemSizes(False)
        self.result_list.setFocusPolicy(Qt.NoFocus)
        self.result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        self.result_list.itemActivated.connect(self._on_activate)
        self.result_list.currentItemChanged.connect(self._on_change)
        
        self.addWidget(self.result_list)
        
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
        self.remove_custom_widget() # Ensure we are in list mode
        
        current_row = self.result_list.currentRow()
        self.result_list.clear()
        
        if not results:
            return 0 # height

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