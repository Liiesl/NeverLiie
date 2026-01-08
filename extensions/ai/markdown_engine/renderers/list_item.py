# markdown_engine/renderers/list_item.py
from .text import TextRenderer
from ..data_types import FormatType
from PySide6.QtGui import QColor, QFontMetrics
import time
from ..benchmark import get_global_benchmark

class ListItemRenderer(TextRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        painter.setPen(QColor(theme["text"]))
        
        for i, line in enumerate(block.layout_lines):
            draw_y = msg_y + line.rect.y() + line.fm.ascent()
            base_x = line.rect.x()
            
            # Draw list marker only on first line
            if i == 0:
                self._draw_marker(painter, block, base_x, draw_y, theme, styles)

            # --- FIX: Don't assign the result! The method updates in-place. ---
            if line.render_cache is None:
                bench = get_global_benchmark()
                if bench:
                    cache_timer = bench.child("Render Cache Precalculation")
                    cache_timer.set_context(type=block.type.name, line_chars=len(line.text), formats=len(block.formatting))
                    cache_start = time.perf_counter()
                
                # Call the method from the parent class (TextRenderer)
                self.precalculate_line(line, block)
                
                if bench:
                    cache_timer.record_time((time.perf_counter() - cache_start) * 1000)

            # Safety check: if cache is still empty or None, skip
            if not line.render_cache:
                continue

            current_x = base_x
            for text, fmt_type, data in line.render_cache:
                font = styles.get_font(block.type, format_type=fmt_type)
                painter.setFont(font)

                if fmt_type == FormatType.CODE:
                    # _draw_inline_code_bg is inherited from TextRenderer
                    self._draw_inline_code_bg(painter, text, font, current_x, draw_y, line.fm, theme)
                    painter.setPen(QColor(theme["accent"]))
                elif fmt_type == FormatType.LINK:
                    painter.setPen(QColor(theme["accent"]))
                else:
                    painter.setPen(QColor(theme["text"]))

                painter.drawText(current_x, draw_y, text)
                current_x += QFontMetrics(font).horizontalAdvance(text)

    def _draw_marker(self, painter, block, base_x, draw_y, theme, styles):
        painter.save()
        font = styles.get_font(block.type, format_type=FormatType.BOLD)
        painter.setFont(font)
        painter.setPen(QColor(theme["text"]))
        fm = painter.fontMetrics()
        
        # Handle cases where list_marker might be missing
        marker_text = block.list_marker if block.list_marker else "•"
        
        marker_w = fm.horizontalAdvance(marker_text)
        marker_x = base_x - marker_w - 8
        painter.drawText(int(marker_x), int(draw_y), marker_text)
        painter.restore()