# markdown_engine/layout.py
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFontMetrics, QTextLayout, QTextOption
from .constants import (BUBBLE_PADDING, LINE_SPACING, BLOCK_SPACING, 
                       BUBBLE_WIDTH_RATIO, PADDING_X, TABLE_CELL_PADDING)
from .data_types import LayoutLine, BlockType
import time
from .benchmark import get_global_benchmark

class LayoutEngine:
    def __init__(self, style_manager):
        self.styles = style_manager

    def calculate_message_layout(self, message, container_width, current_y):
        bench = get_global_benchmark()
        message.y_pos = current_y
        bubble_w = container_width * BUBBLE_WIDTH_RATIO
        message.x_pos = container_width - bubble_w - PADDING_X if message.is_user else PADDING_X
        text_area_width = int(bubble_w - (BUBBLE_PADDING * 2))
        current_block_y = BUBBLE_PADDING
        
        for block in message.blocks:
            block.layout_lines = []
            block.y_pos = current_block_y
            block.x_offset = 0 
            
            fm = self.styles.get_metrics(block.type, level=block.level)
            
            indent_pixels = 0
            if block.type == BlockType.LIST_ITEM:
                indent_pixels += block.indent_level * 25
            if block.quote_level > 0:
                quote_indent = block.quote_level * 20
                indent_pixels += quote_indent

            avail_width = text_area_width - indent_pixels
            if avail_width < 50: avail_width = 50

            # --- 1. DIVIDER ---
            if block.type == BlockType.DIVIDER:
                block.height = 20
                current_block_y += block.height + BLOCK_SPACING
                continue
                
            # --- 2. TABLES ---
            if block.type == BlockType.TABLE:
                if bench:
                    block_timer = bench.child("Layout: Table")
                    block_timer.set_context(type="TABLE", headers=len(block.table_headers))
                    start = time.perf_counter()
                
                col_count = len(block.table_headers)
                if col_count == 0: 
                    current_block_y += BLOCK_SPACING
                    continue

                col_widths = [0] * col_count
                for i, h in enumerate(block.table_headers):
                    if i < col_count:
                        w = fm.horizontalAdvance(h) + (TABLE_CELL_PADDING * 3)
                        col_widths[i] = max(col_widths[i], w)
                for row in block.table_rows:
                    for i, cell in enumerate(row):
                        if i < col_count:
                            w = fm.horizontalAdvance(cell) + (TABLE_CELL_PADDING * 3)
                            col_widths[i] = max(col_widths[i], w)

                total_desired = sum(col_widths)
                if total_desired > avail_width:
                    scale = avail_width / total_desired
                    col_widths = [int(w * scale) for w in col_widths]
                
                block.table_col_widths = col_widths 
                row_height = fm.height() + (TABLE_CELL_PADDING * 2)
                
                def process_row(cells, y_offset):
                    x_cursor = message.x_pos + BUBBLE_PADDING + indent_pixels
                    for c_idx, text in enumerate(cells):
                        if c_idx >= len(col_widths): break
                        cw = col_widths[c_idx]
                        align = 'left'
                        if c_idx < len(block.table_align): align = block.table_align[c_idx]
                        text_w = fm.horizontalAdvance(text)
                        text_x = x_cursor + TABLE_CELL_PADDING
                        if align == 'center': text_x = x_cursor + (cw - text_w) / 2
                        elif align == 'right': text_x = x_cursor + cw - TABLE_CELL_PADDING - text_w
                        if text_x < x_cursor: text_x = x_cursor
                        rect = QRect(int(text_x), int(y_offset + TABLE_CELL_PADDING), int(text_w), int(fm.height()))
                        block.layout_lines.append(LayoutLine(text, rect, fm, 0))
                        x_cursor += cw

                process_row(block.table_headers, current_block_y)
                current_block_y += row_height
                for row in block.table_rows:
                    process_row(row, current_block_y)
                    current_block_y += row_height

                block.height = (current_block_y - block.y_pos)
                current_block_y += BLOCK_SPACING
                if bench: block_timer.record_time((time.perf_counter() - start) * 1000)
                continue

            # --- 3. CODE BLOCKS ---
            if block.type == BlockType.CODE:
                if bench:
                    block_timer = bench.child("Layout: Code")
                    block_timer.set_context(type="CODE", lines=len(block.text.split('\n')))
                    start = time.perf_counter()
                
                lines = block.text.split('\n')
                char_cursor = 0 
                for line in lines:
                    if not line:
                        current_block_y += fm.height() + LINE_SPACING
                        char_cursor += 1 
                        continue
                    remaining_text = line
                    while remaining_text:
                        if fm.horizontalAdvance(remaining_text) <= avail_width:
                            rect = QRect(message.x_pos + BUBBLE_PADDING + indent_pixels, 
                                         current_block_y, 
                                         fm.horizontalAdvance(remaining_text), 
                                         fm.height())
                            block.layout_lines.append(LayoutLine(remaining_text, rect, fm, char_cursor))
                            current_block_y += fm.height() + LINE_SPACING
                            char_cursor += len(remaining_text)
                            remaining_text = ""
                        else:
                            split_idx = len(remaining_text)
                            while split_idx > 0 and fm.horizontalAdvance(remaining_text[:split_idx]) > avail_width:
                                split_idx -= 1
                            if split_idx == 0: split_idx = 1
                            chunk = remaining_text[:split_idx]
                            rect = QRect(message.x_pos + BUBBLE_PADDING + indent_pixels, 
                                         current_block_y, 
                                         fm.horizontalAdvance(chunk), 
                                         fm.height())
                            block.layout_lines.append(LayoutLine(chunk, rect, fm, char_cursor))
                            current_block_y += fm.height() + LINE_SPACING
                            char_cursor += len(chunk)
                            remaining_text = remaining_text[split_idx:]
                    char_cursor += 1
                
                current_block_y += BUBBLE_PADDING
                if bench: block_timer.record_time((time.perf_counter() - start) * 1000)

            # --- 4. STANDARD TEXT (Paragraphs, List Items, Quotes) ---
            else:
                if bench:
                    block_timer = bench.child(f"Layout: {block.type.name}")
                    block_timer.set_context(chars=len(block.text))
                    start = time.perf_counter()

                # --- FAST PATH ---
                text = block.text
                has_newline = '\n' in text
                
                fits = False
                if not has_newline:
                    full_width = fm.horizontalAdvance(text)
                    if full_width <= avail_width:
                        fits = True
                        rect = QRect(
                            int(message.x_pos + BUBBLE_PADDING + indent_pixels),
                            int(current_block_y),
                            int(full_width),
                            int(fm.height())
                        )
                        block.layout_lines.append(LayoutLine(text, rect, fm, 0))
                        current_block_y += fm.height() + LINE_SPACING

                if not fits:
                    # SLOW PATH: QTextLayout
                    font = self.styles.get_font(block.type, level=block.level)
                    text_layout = QTextLayout(text, font)
                    option = QTextOption()
                    option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
                    text_layout.setTextOption(option)
                    text_layout.beginLayout()
                    while True:
                        line = text_layout.createLine()
                        if not line.isValid():
                            break
                        line.setLineWidth(avail_width)
                        rect = QRect(
                            int(message.x_pos + BUBBLE_PADDING + indent_pixels + line.position().x()),
                            int(current_block_y),
                            int(line.naturalTextWidth()),
                            int(line.height())
                        )
                        start_idx = line.textStart()
                        length = line.textLength()
                        text_seg = text[start_idx : start_idx + length]
                        block.layout_lines.append(LayoutLine(text_seg, rect, fm, start_idx))
                        current_block_y += line.height() + LINE_SPACING
                    text_layout.endLayout()

                # --- FIX: Moved inside 'if bench' block ---
                if bench:
                    elapsed = (time.perf_counter() - start) * 1000
                    block_timer.record_time(elapsed)
                    
                    # --- DEBUG: Print blocks causing lag ---
                    if elapsed > 10.0:
                        print(f"SLOW BLOCK ({elapsed:.2f}ms): [{block.type.name}] '{text[:50]}...'")
             
            block.height = (current_block_y - block.y_pos)
            current_block_y += BLOCK_SPACING

        message.total_height = current_block_y - BLOCK_SPACING + BUBBLE_PADDING
        return message.total_height