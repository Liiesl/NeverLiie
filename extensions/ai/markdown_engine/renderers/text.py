# markdown_engine/renderers/text.py
from .base import BlockRenderer
from ..data_types import BlockType, FormatType
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtCore import Qt
import time
from ..benchmark import get_global_benchmark

class TextRenderer(BlockRenderer):
    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        bench = get_global_benchmark()
        painter.setPen(QColor(theme["text"]))
        
        for i, line in enumerate(block.layout_lines):
            draw_y = msg_y + line.rect.y() + line.fm.ascent()
            base_x = line.rect.x()

            # --- CHANGE: Use the public helper method ---
            if line.render_cache is None:
                self.precalculate_line(line, block)

            current_x = base_x
            for text, fmt_type, data in line.render_cache:
                font = styles.get_font(block.type, format_type=fmt_type)
                painter.setFont(font)

                if fmt_type == FormatType.CODE:
                    self._draw_inline_code_bg(painter, text, font, current_x, draw_y, line.fm, theme)
                    painter.setPen(QColor(theme["accent"]))
                elif fmt_type == FormatType.LINK:
                    painter.setPen(QColor(theme["accent"]))
                else:
                    painter.setPen(QColor(theme["text"]))

                painter.drawText(current_x, draw_y, text)
                current_x += QFontMetrics(font).horizontalAdvance(text)

    def _draw_inline_code_bg(self, painter, text, font, x, y, line_fm, theme):
        fm = QFontMetrics(font)
        bg_rect = fm.boundingRect(text)
        bg_rect.moveTo(int(x), int(y - line_fm.ascent()))
        bg_rect.setWidth(fm.horizontalAdvance(text))
        
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme["surface"]).lighter(120))
        painter.drawRoundedRect(bg_rect, 4, 4)
        painter.restore()

    # --- CHANGE: Renamed from _precalculate_line to precalculate_line (public) ---
    def precalculate_line(self, line, block):
        full_text = line.text
        line_start_idx = line.char_start
        
        # 1. Map chars to styles
        char_styles = [(FormatType.NORMAL, None)] * len(full_text)
        
        for fmt in block.formatting:
            f_end = fmt.start + fmt.length
            l_end = line_start_idx + len(full_text)
            intersect_start = max(fmt.start, line_start_idx)
            intersect_end = min(f_end, l_end)

            if intersect_start < intersect_end:
                local_s = intersect_start - line_start_idx
                local_e = intersect_end - line_start_idx
                
                for k in range(local_s, local_e):
                    current_type, _ = char_styles[k]
                    new_fmt = fmt.format_type
                    
                    final_fmt = new_fmt
                    if new_fmt == FormatType.CODE: final_fmt = FormatType.CODE
                    elif new_fmt == FormatType.LINK: final_fmt = FormatType.LINK
                    elif new_fmt == FormatType.STRIKETHROUGH: final_fmt = FormatType.STRIKETHROUGH
                    elif new_fmt == FormatType.BOLD:
                        final_fmt = FormatType.BOLD_ITALIC if current_type == FormatType.ITALIC else FormatType.BOLD
                    elif new_fmt == FormatType.ITALIC:
                        final_fmt = FormatType.BOLD_ITALIC if current_type == FormatType.BOLD else FormatType.ITALIC
                    
                    char_styles[k] = (final_fmt, fmt.data)

        # 2. Group into segments
        segments = []
        if not full_text: 
            line.render_cache = []
            return

        current_style, current_data = char_styles[0]
        current_seg_text = full_text[0]

        for k in range(1, len(full_text)):
            style, data = char_styles[k]
            if style == current_style and data == current_data:
                current_seg_text += full_text[k]
            else:
                segments.append((current_seg_text, current_style, current_data))
                current_style = style
                current_data = data
                current_seg_text = full_text[k]
        
        segments.append((current_seg_text, current_style, current_data))
        line.render_cache = segments