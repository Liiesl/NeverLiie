# markdown_engine/parser.py
from markdown_it import MarkdownIt
from .data_types import TextBlock, BlockType, FormatType, FormatRange
import time
from .benchmark import get_global_benchmark

class MarkdownParser:
    def parse(self, text):
        bench = get_global_benchmark()
        
        # Disable 'lheading' to prevent dashes under text from becoming headers
        md = MarkdownIt("commonmark", {
            'breaks': True, 
            'html': False, 
            'linkify': True
        }).enable('table').disable('lheading') 
        
        tokens = md.parse(text)
        blocks = []
        
        list_stack = [] 
        quote_depth = 0
        pending_marker = None
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.type == 'blockquote_open': quote_depth += 1
            elif t.type == 'blockquote_close': quote_depth = max(0, quote_depth - 1)
            elif t.type == 'bullet_list_open': list_stack.append({'type': 'ul'})
            elif t.type == 'ordered_list_open':
                start = int(t.attrs.get('start', 1))
                list_stack.append({'type': 'ol', 'count': start})
            elif t.type in ('bullet_list_close', 'ordered_list_close'):
                if list_stack: list_stack.pop()
            elif t.type == 'list_item_open':
                if list_stack:
                    ctx = list_stack[-1]
                    if ctx['type'] == 'ul':
                        depth = len(list_stack)
                        if depth % 3 == 1: pending_marker = "•"
                        elif depth % 3 == 2: pending_marker = "◦"
                        else: pending_marker = "▪"
                    else:
                        pending_marker = f"{ctx['count']}."
                        ctx['count'] += 1
            
            # --- Catch Horizontal Rule ---
            elif t.type == 'hr':
                if bench:
                    block_timer = bench.child("Parse: Divider")
                    block_timer.set_context(type="DIVIDER")
                    start = time.perf_counter()
                b = TextBlock("", BlockType.DIVIDER)
                b.quote_level = quote_depth
                blocks.append(b)
                if bench:
                    block_timer.record_time((time.perf_counter() - start) * 1000)

            elif t.type == 'table_open':
                if bench:
                    block_timer = bench.child("Parse: Table")
                    block_timer.set_context(type="TABLE")
                    start = time.perf_counter()
                b = TextBlock("", BlockType.TABLE)
                b.quote_level = quote_depth
                i += 1
                in_thead = False
                current_row = []
                while i < len(tokens) and tokens[i].type != 'table_close':
                    tt = tokens[i]
                    if tt.type == 'thead_open': in_thead = True
                    elif tt.type == 'thead_close': in_thead = False
                    elif tt.type == 'tr_open': current_row = []
                    elif tt.type == 'tr_close':
                        if in_thead: b.table_headers = current_row
                        else: b.table_rows.append(current_row)
                    elif tt.type in ('th_open', 'td_open'):
                        align = tt.attrs.get('style', '')
                        align_type = 'left'
                        if 'center' in align: align_type = 'center'
                        elif 'right' in align: align_type = 'right'
                        if in_thead: b.table_align.append(align_type)
                    elif tt.type == 'inline':
                        content, _ = self._process_inline(tt)
                        current_row.append(content)
                    i += 1
                blocks.append(b)
                if bench:
                    block_timer.record_time((time.perf_counter() - start) * 1000)
            elif t.type == 'heading_open':
                if bench:
                    block_timer = bench.child("Parse: Header")
                    block_timer.set_context(type="HEADER")
                    start = time.perf_counter()
                try: level = int(t.tag[1])
                except: level = 1
                i += 1
                if i < len(tokens) and tokens[i].type == 'inline':
                    content, fmts = self._process_inline(tokens[i])
                    b = TextBlock(content, BlockType.HEADER, level=level)
                    b.formatting = fmts
                    b.quote_level = quote_depth 
                    blocks.append(b)
                if bench:
                    block_timer.record_time((time.perf_counter() - start) * 1000)
            elif t.type == 'paragraph_open':
                i += 1
                if i < len(tokens) and tokens[i].type == 'inline':
                    if bench:
                        block_timer = bench.child("Parse: Paragraph/Quote/List")
                        start = time.perf_counter()
                    content, fmts = self._process_inline(tokens[i])
                    if content.strip() or True: 
                        b_type = BlockType.PARAGRAPH
                        if quote_depth > 0: b_type = BlockType.QUOTE
                        if list_stack:
                            b_type = BlockType.LIST_ITEM
                            b = TextBlock(content, b_type)
                            b.indent_level = len(list_stack)
                            if pending_marker:
                                b.list_marker = pending_marker
                                pending_marker = None
                        else: b = TextBlock(content, b_type)
                        if bench:
                            block_timer.set_context(type=b_type.name, chars=len(content), quote_depth=quote_depth)
                        b.quote_level = quote_depth
                        b.formatting = fmts
                        blocks.append(b)
                    if bench:
                        block_timer.record_time((time.perf_counter() - start) * 1000)
            elif t.type in ('fence', 'code_block'):
                if bench:
                    block_timer = bench.child("Parse: Code")
                    block_timer.start_time = time.perf_counter()
                content = t.content.strip()
                b = TextBlock(content, BlockType.CODE)
                if bench:
                    block_timer.set_context(type="CODE", language=t.info or "None", chars=len(content))
                b.quote_level = quote_depth
                b.quote_level = quote_depth
                b.language = t.info.strip() if t.info else None
                blocks.append(b)
                if bench:
                    block_timer.record_time((time.perf_counter() - start) * 1000)
            i += 1
        return blocks

    def _process_inline(self, token):
        full_text = ""
        formats = []
        style_stack = [] 

        if not token.children:
            return token.content, []

        for child in token.children:
            if child.type == 'text':
                full_text += child.content
            elif child.type == 'link_open':
                href = child.attrs.get('href', '')
                title = child.attrs.get('title', None)
                link_data = {'url': href, 'title': title} 
                style_stack.append((FormatType.LINK, len(full_text), link_data))
            elif child.type == 'link_close':
                for s_i in range(len(style_stack)-1, -1, -1):
                    if style_stack[s_i][0] == FormatType.LINK:
                        fmt_type, start_idx, link_data = style_stack.pop(s_i)
                        length = len(full_text) - start_idx
                        formats.append(FormatRange(start_idx, length, fmt_type, link_data))
                        break
            
            # --- MODIFIED: REMOVED EMOJI HANDLING FOR BENCHMARK ---
            elif child.type == 'image':
                # Original logic was: full_text += f"🖼 {alt}"
                # New logic: Raw text output
                src = child.attrs.get('src', '')
                alt = child.content if child.content else ""
                full_text += f"![{alt}]({src})"

            elif child.type == 'code_inline':
                start = len(full_text)
                full_text += child.content
                formats.append(FormatRange(start, len(child.content), FormatType.CODE))
            elif child.type == 'softbreak': full_text += "\n"
            elif child.type == 'hardbreak': full_text += "\n"
            elif child.type == 'strong_open': style_stack.append((FormatType.BOLD, len(full_text), None))
            elif child.type == 'em_open': style_stack.append((FormatType.ITALIC, len(full_text), None))
            elif child.type == 's_open': style_stack.append((FormatType.STRIKETHROUGH, len(full_text), None))
            elif child.type in ('strong_close', 'em_close', 's_close'):
                target = FormatType.NORMAL
                if child.type == 'strong_close': target = FormatType.BOLD
                elif child.type == 'em_close': target = FormatType.ITALIC
                elif child.type == 's_close': target = FormatType.STRIKETHROUGH
                for s_i in range(len(style_stack)-1, -1, -1):
                    if style_stack[s_i][0] == target:
                        fmt_type, start_idx, _ = style_stack.pop(s_i)
                        length = len(full_text) - start_idx
                        formats.append(FormatRange(start_idx, length, fmt_type))
                        break

        return full_text, formats