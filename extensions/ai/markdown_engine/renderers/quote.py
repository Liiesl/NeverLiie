# markdown_engine/renderers/quote.py
from PySide6.QtGui import QColor
from PySide6.QtCore import QRect, Qt
from .text import TextRenderer
from ..constants import BLOCK_SPACING

class QuoteRenderer(TextRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        # 1. Draw the vertical quote bars
        bar_width = 4
        
        painter.save()
        painter.setPen(Qt.NoPen)
        
        if "quote_bar" in theme:
            bar_color = QColor(theme["quote_bar"])
        else:
            bar_color = QColor(theme["subtext"])
            
        bar_color.setAlpha(100)
        painter.setBrush(bar_color)

        # FIX: Calculate visual height to include the spacing AFTER the block.
        # This ensures the quote bar connects visually with the next block's bar.
        content_height = block.height + BLOCK_SPACING

        start_y = msg_y + block.y_pos
        
        for i in range(block.quote_level):
            # Level 1 is leftmost. Layout assumes ~20px per indentation level.
            level_indent = 20
            
            # Position bar relative to message bubble start
            bar_x = (msg_x + getattr(block, 'x_offset', 0)) + (i * level_indent) + 5 
            
            bar_rect = QRect(int(bar_x), int(start_y), int(bar_width), int(content_height))
            painter.drawRoundedRect(bar_rect, 2, 2)

        painter.restore()

        # 2. Draw the text content
        super().paint(painter, block, msg_x, msg_y, theme, styles)