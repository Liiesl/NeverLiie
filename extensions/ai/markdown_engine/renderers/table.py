# markdown_engine/renderers/table.py
from .base import BlockRenderer
from PySide6.QtGui import QColor, QFontMetrics, QPen
from PySide6.QtCore import QRect, Qt
from ..constants import BUBBLE_PADDING, TABLE_CELL_PADDING

class TableRenderer(BlockRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        font = styles.get_font(block.type)
        painter.setFont(font)
        fm = QFontMetrics(font)

        if not block.table_col_widths: return

        # Geometry Setup
        start_x = msg_x + BUBBLE_PADDING # Note: Assumes indent handled in Layout
        start_y = msg_y + block.y_pos
        
        row_height = fm.height() + (TABLE_CELL_PADDING * 2)
        col_widths = block.table_col_widths
        
        border_color = QColor(theme["table_border"])
        
        # 1. DRAW BACKGROUNDS & GRID
        current_y = start_y
        total_width = sum(col_widths)
        
        # -- Header --
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QColor(theme["table_header_bg"]))
        painter.drawRect(start_x, current_y, total_width, row_height)
        
        # Header vertical lines
        vx = start_x
        for w in col_widths:
            vx += w
            painter.drawLine(vx, current_y, vx, current_y + row_height)
        
        current_y += row_height
        
        # -- Rows --
        for i, row in enumerate(block.table_rows):
            bg_key = "table_row_alt" if i % 2 == 0 else "table_row_bg"
            painter.setBrush(QColor(theme[bg_key]))
            painter.drawRect(start_x, current_y, total_width, row_height)
            
            vx = start_x
            for w in col_widths:
                vx += w
                painter.drawLine(vx, current_y, vx, current_y + row_height)
            
            current_y += row_height

        # 2. DRAW TEXT (using layout lines generated in LayoutEngine)
        # This ensures that what is drawn matches exactly what is selectable.
        painter.setPen(QColor(theme["text"]))
        
        # Optimization: We could use TextRenderer logic here, but direct draw is fine
        # since tables usually don't have bold/italic processing in this simple version
        for line in block.layout_lines:
            # line.rect.x() is absolute X relative to Message Bubble in LayoutEngine
            # But wait, LayoutEngine calculated rects based on message.x_pos.
            # So line.rect.y() is relative to message.y_pos.
            
            draw_x = line.rect.x() 
            draw_y = msg_y + line.rect.y() + line.fm.ascent()
            
            # Clip text if it overflows cell (Optional but good for safety)
            # For now, just draw
            painter.drawText(draw_x, draw_y, line.text)