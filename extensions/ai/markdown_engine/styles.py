# markdown_engine/styles.py
from PySide6.QtGui import QFont, QFontMetrics
from .data_types import BlockType, FormatType
import platform

class StyleManager:
    def __init__(self):
        # Determine OS to pick correct emoji font to avoid "Missing Font" scan delays
        sys_plat = platform.system()
        if sys_plat == "Windows":
            self.font_families = ["Segoe UI", "Segoe UI Emoji"]
        elif sys_plat == "Darwin": # macOS
            self.font_families = ["Helvetica Neue", "Apple Color Emoji"]
        else: # Linux
            self.font_families = ["Roboto", "Noto Color Emoji"]

        self.font_main = QFont()
        self.font_main.setFamilies(self.font_families)
        self.font_main.setPointSize(11)
        self.font_main.setStyleHint(QFont.SansSerif)

        self.font_code = QFont("Consolas")
        self.font_code.setStyleHint(QFont.Monospace)
        self.font_code.setPointSize(10)
        
        self._font_cache = {} 
        
        self.header_fonts = {}
        self.header_metrics = {}
        sizes = {1: 26, 2: 22, 3: 18, 4: 16, 5: 14, 6: 12}
        
        for level, size in sizes.items():
            font = QFont(self.font_main) # Clone to keep families
            font.setPointSize(size)
            font.setBold(True)
            self.header_fonts[level] = font
            self.header_metrics[level] = QFontMetrics(font)
        
        self.fm_main = QFontMetrics(self.font_main)
        self.fm_code = QFontMetrics(self.font_code)

    def get_font(self, block_type, level=1, format_type=FormatType.NORMAL):
        if block_type == BlockType.CODE:
            return self.font_code

        if block_type == BlockType.HEADER:
            return self.header_fonts.get(level, self.header_fonts[1])

        cache_key = (format_type)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = QFont(self.font_main)
        
        if format_type in (FormatType.BOLD, FormatType.BOLD_ITALIC):
            font.setBold(True)
        if format_type in (FormatType.ITALIC, FormatType.BOLD_ITALIC):
            font.setItalic(True)
        if format_type == FormatType.CODE:
            font = QFont("Consolas")
            font.setPointSize(10)
        if format_type == FormatType.STRIKETHROUGH:
            font.setStrikeOut(True)
        if format_type == FormatType.LINK:
            font.setUnderline(True)
        
        self._font_cache[cache_key] = font
        return font

    def get_metrics(self, block_type, level=1):
        if block_type == BlockType.CODE:
            return self.fm_code
        if block_type == BlockType.HEADER:
            return self.header_metrics.get(level, self.header_metrics[1])
        return self.fm_main