from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt, QRect

class BlockRenderer:
    def paint(self, painter: QPainter, block, msg_x, msg_y, theme, styles):
        raise NotImplementedError
        
    def draw_selection(self, painter: QPainter, block, msg_y, theme, sel_start, sel_end, is_selected_fn):
        """Common selection drawing logic"""
        # Logic extracted from original paintEvent to handle selection highlights
        pass # Implemented in concrete classes or kept in widget for simplicity in PoC