# markdown_engine/renderers/divider.py
from .base import BlockRenderer
from PySide6.QtGui import QColor, QPen
from PySide6.QtCore import Qt
from ..constants import BUBBLE_PADDING, BUBBLE_WIDTH_RATIO

class DividerRenderer(BlockRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        # Calculate visual properties
        
        # Geometry: 
        # msg_x is the left-edge of the bubble
        # We need the width of the bubble to center/span the line correctly.
        # Based on widget.py and layout.py, bubble width is derived from BUBBLE_WIDTH_RATIO
        
        # Get container width from painter device
        container_width = painter.device().width()
        bubble_width = container_width * BUBBLE_WIDTH_RATIO
        
        # Line coordinates
        # Center vertically within the block's height
        line_y = msg_y + block.y_pos + (block.height / 2)
        
        # Span horizontally with some internal padding
        start_x = msg_x + BUBBLE_PADDING + 10 # Extra indentation
        end_x = msg_x + bubble_width - BUBBLE_PADDING - 10
        
        # Drawing
        painter.save()
        
        # Use theme border color, or subtext if border is too subtle
        line_color = QColor(theme.get("border", "#555"))
        
        # Create a pen: 2px wide, solid line
        pen = QPen(line_color, 2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        painter.drawLine(start_x, line_y, end_x, line_y)
        
        painter.restore()