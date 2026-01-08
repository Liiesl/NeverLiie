# markdown_engine/constants.py

THEME = {
    "bg": "#232324",
    "surface": "#38394B",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "accent": "#89b4fa",
    "code_bg": "#1e1e2e",
    "code_text": "#f5c2e7",
    "user_bg": "#45475a",
    "ai_bg": "#313244",
    "border": "#45475a",
    "selection": "#60d689fa",
    "quote_bar": "#a6adc8",
    
    # Table Colors
    "table_border": "#585b70",
    "table_header_bg": "#181825",
    "table_row_bg": "#1e1e2e",
    "table_row_alt": "#313244",

    # Copy Button Colors <--- NEW
    "copy_btn_bg": "#313244",
    "copy_btn_hover": "#45475a",
    "copy_btn_text": "#a6adc8",
    "copy_btn_success": "#a6e3a1" # Greenish for "Copied!"
}
# ... (rest of the file remains the same)
THEME.update({
    "token_keyword": "#ff79c6",
    "token_string": "#f1fa8c", 
    "token_comment": "#6272a4",
    "token_number": "#bd93f9",
    "token_operator": "#ffb86c",
    "token_class": "#8be9fd",
    "token_function": "#50fa7b",
    "token_generic": "#f8f8f2"
})

PADDING_X = 20
PADDING_Y = 20
BUBBLE_PADDING = 15
LINE_SPACING = 4
BLOCK_SPACING = 10
MSG_SPACING = 20
BUBBLE_WIDTH_RATIO = 0.85
TABLE_CELL_PADDING = 8