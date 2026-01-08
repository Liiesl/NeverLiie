# markdown_engine/renderers/code.py
from .base import BlockRenderer
from PySide6.QtGui import QColor, QFontMetrics, QFont
from PySide6.QtCore import QRect, Qt
from ..constants import BUBBLE_PADDING

class CodeRenderer(BlockRenderer):
    def get_token_color(self, token_type, theme, Token):
        if token_type in Token.Keyword: return theme["token_keyword"]
        if token_type in Token.Name.Function: return theme["token_function"]
        if token_type in Token.Name.Class: return theme["token_class"]
        if token_type in Token.String: return theme["token_string"]
        if token_type in Token.Number: return theme["token_number"]
        if token_type in Token.Comment: return theme["token_comment"]
        if token_type in Token.Operator: return theme["token_operator"]
        return theme["token_generic"]

    def _ensure_block_cache(self, block, theme):
        if block.highlight_cache is not None:
            return

        text = block.text
        block.highlight_cache = []

        try:
            from pygments import lex
            from pygments.lexers import get_lexer_by_name, special
            from pygments.token import Token
        except ImportError:
            block.highlight_cache = [(0, len(text), QColor(theme["code_text"]), text)]
            return

        lang = getattr(block, 'language', None)
        
        lexer = None
        if lang and lang.strip():
            try:
                lexer = get_lexer_by_name(lang)
            except:
                pass 
        
        if lexer is None:
            lexer = special.TextLexer()

        tokens = lex(text, lexer)
        
        current_idx = 0
        for token_type, token_text in tokens:
            if not token_text: continue
            length = len(token_text)
            color_hex = self.get_token_color(token_type, theme, Token)
            color = QColor(color_hex)
            block.highlight_cache.append((current_idx, current_idx + length, color, token_text))
            current_idx += length

    def paint(self, painter, block, msg_x, msg_y, theme, styles):
        # 1. Background
        container_w = painter.device().width()
        bubble_w = container_w * 0.85 - 20 
        
        # Calculate code block rect
        code_rect = QRect(int(msg_x + BUBBLE_PADDING - 5), 
                          int(msg_y + block.y_pos - 5), 
                          int(bubble_w), 
                          int(block.height))

        painter.setBrush(QColor(theme["code_bg"]))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(code_rect, 6, 6)
        
        # --- DRAW COPY BUTTON ---
        # 1. Define dimensions
        btn_width = 50 if not getattr(block, 'show_copied_text', False) else 60
        btn_height = 20
        # Position relative to message, right aligned inside the code block
        rel_x = code_rect.right() - msg_x - btn_width - 5 
        rel_y = block.y_pos 
        
        # Store rect in block for hit testing in Widget (relative to message)
        block.copy_rect = QRect(int(rel_x), int(rel_y), btn_width, btn_height)
        
        # Draw Button Background
        # We need absolute coordinates for drawing
        draw_rect = QRect(int(msg_x + rel_x), int(msg_y + rel_y), btn_width, btn_height)
        
        bg_color = theme["copy_btn_hover"] if getattr(block, 'is_copy_hovered', False) else theme["copy_btn_bg"]
        painter.setBrush(QColor(bg_color))
        painter.drawRoundedRect(draw_rect, 4, 4)
        
        # Draw Button Text
        painter.setFont(QFont("Segoe UI", 8)) # Use a small clean font
        text_color = theme["copy_btn_success"] if getattr(block, 'show_copied_text', False) else theme["copy_btn_text"]
        painter.setPen(QColor(text_color))
        
        btn_text = "Copied!" if getattr(block, 'show_copied_text', False) else "Copy"
        painter.drawText(draw_rect, Qt.AlignCenter, btn_text)

        # 2. Setup Font for Code
        font = styles.get_font(block.type)
        painter.setFont(font)
        
        # 3. Generate Highlighting Data (Lazy)
        self._ensure_block_cache(block, theme)
        
        # 4. Draw Lines
        if not hasattr(block, 'highlight_cache') or not block.highlight_cache:
             return

        # Optimization: Don't draw text under the copy button if line is long?
        # For now, just draw text, button draws on top.
        
        for line in block.layout_lines:
            draw_y = msg_y + line.rect.y() + line.fm.ascent()
            base_x = line.rect.x()
            
            line_start = line.char_start
            line_end = line_start + len(line.text)
            
            current_draw_x = base_x
            
            for t_start, t_end, color, t_text in block.highlight_cache:
                if t_end > line_start and t_start < line_end:
                    intersect_start = max(line_start, t_start)
                    intersect_end = min(line_end, t_end)
                    
                    slice_start = intersect_start - t_start
                    slice_end = intersect_end - t_start
                    
                    text_segment = t_text[slice_start:slice_end]
                    
                    if text_segment:
                        painter.setPen(color)
                        painter.drawText(int(current_draw_x), int(draw_y), text_segment)
                        current_draw_x += line.fm.horizontalAdvance(text_segment)

                if t_start >= line_end:
                    break