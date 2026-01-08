# markdown_engine/renderers/header.py
from .text import TextRenderer
from PySide6.QtGui import QColor, QFontMetrics
from ..data_types import FormatType
import time
from ..benchmark import get_global_benchmark

class HeaderRenderer(TextRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        # Use accent color for headers
        painter.setPen(QColor(theme["accent"]))
        
        for line in block.layout_lines:
            draw_y = msg_y + line.rect.y() + line.fm.ascent()
            base_x = line.rect.x()

            # Ensure cache is populated (inherited from TextRenderer)
            if line.render_cache is None:
                self.precalculate_line(line, block)
            
            # Fallback if cache is empty
            if not line.render_cache:
                font = styles.get_font(block.type, level=block.level)
                painter.setFont(font)
                painter.drawText(base_x, draw_y, line.text)
                continue

            current_x = base_x
            for text, fmt_type, data in line.render_cache:
                # --- PASS block.level TO GET CORRECT FONT SIZE ---
                font = styles.get_font(block.type, level=block.level, format_type=fmt_type)
                painter.setFont(font)

                if fmt_type == FormatType.CODE:
                    # Optional: Draw code background in header
                    self._draw_inline_code_bg(painter, text, font, current_x, draw_y, line.fm, theme)
                
                painter.drawText(current_x, draw_y, text)
                current_x += QFontMetrics(font).horizontalAdvance(text)