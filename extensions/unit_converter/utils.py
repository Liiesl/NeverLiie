# extensions/unit_converter/utils.py
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QVBoxLayout, 
                               QFrame, QSizePolicy)
from PySide6.QtCore import Qt

def format_short(val):
    """Formats large numbers to k, m, b notation for quick reading."""
    if val is None: return ""
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f}".rstrip('0').rstrip('.') + "b"
    if abs_val >= 1_000_000:
        return f"{val / 1_000_000:.2f}".rstrip('0').rstrip('.') + "m"
    if abs_val >= 1_000:
        return f"{val / 1_000:.2f}".rstrip('0').rstrip('.') + "k"
    
    # For small numbers, show up to 4 decimals
    return f"{round(val, 4):g}"

def format_full(val):
    """Formats with commas and high precision, no length limit."""
    if val is None: return ""
    # Use , separator for thousands and up to 10 decimal places to avoid scientific notation
    # rstrip removes trailing zeros from decimals
    return "{:,.10f}".format(val).rstrip('0').rstrip('.')

def format_val(f):
    """Legacy wrapper for backward compatibility if needed."""
    return format_full(f)

class ConverterWidget(QWidget):
    def __init__(self, input_data, output_data_list):
        """
        Args:
            input_data: Tuple (value_str, symbol_str, display_name_str)
            output_data_list: List of Tuples (value_str, symbol_str, display_name_str)
        """
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # --- ORIGINAL STYLING PRESERVED ---
        self.setStyleSheet("""
            QFrame#Container {
                background-color: #3e4048; 
                border-radius: 10px;
            }
            QLabel { color: #e0e0e0; font-family: "Segoe UI"; }
            
            QLabel[role="value"] { 
                font-size: 20px; 
                font-weight: bold; 
                color: #ffffff;
            }
            
            QLabel[role="unit"] {
                background-color: #55575f;
                color: #dcdcdc;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel[role="unit_input"] {
                background-color: #4a5d85; 
                color: #ffffff;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            
            QFrame#Separator {
                background-color: #50525b;
                min-width: 1px;
                max-width: 1px;
            }
            
            QLabel#Arrow {
                color: #888888;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 24px; 
            }
        """)

        # Main Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(0)

        # Container
        self.container = QFrame()
        self.container.setObjectName("Container")
        
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 1. Input Column
        # Unpack tuple: (Value, Symbol, DisplayName)
        in_val, in_sym, in_name = input_data
        input_frame = self._create_column(in_val, in_sym, in_name, is_input=True)
        container_layout.addWidget(input_frame)

        # Arrow
        arrow = QLabel("→")
        arrow.setObjectName("Arrow")
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setFixedWidth(30)
        container_layout.addWidget(arrow)

        # 2. Output Columns
        for i, (out_val, out_sym, out_name) in enumerate(output_data_list):
            if i > 0:
                sep = QFrame()
                sep.setObjectName("Separator")
                container_layout.addWidget(sep)
            
            out_frame = self._create_column(out_val, out_sym, out_name, is_input=False)
            container_layout.addWidget(out_frame)
            
        if len(output_data_list) < 3:
            container_layout.addStretch()

        layout.addWidget(self.container)

    def _create_column(self, value, symbol, name, is_input):
        frame = QFrame()
        frame.setMinimumWidth(100)
        vbox = QVBoxLayout(frame)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(6)
        vbox.setContentsMargins(15, 15, 15, 15)

        # Top Label: "172 mg"
        # Combines Value and Symbol
        full_text = f"{value} {symbol}" if symbol else str(value)
        val_lbl = QLabel(full_text)
        val_lbl.setProperty("role", "value")
        val_lbl.setAlignment(Qt.AlignCenter)
        
        # Dynamic font scaling
        txt_len = len(full_text)
        if txt_len > 15:
             font = val_lbl.font()
             font.setPointSize(14)
             val_lbl.setFont(font)
        elif txt_len > 8:
             font = val_lbl.font()
             font.setPointSize(16)
             val_lbl.setFont(font)

        # Bottom Pill: "MILLIGRAM" (Display Name)
        unit_lbl = QLabel(str(name).upper())
        unit_lbl.setProperty("role", "unit_input" if is_input else "unit")
        unit_lbl.setAlignment(Qt.AlignCenter)
        unit_lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        vbox.addWidget(val_lbl)
        vbox.addWidget(unit_lbl, 0, Qt.AlignCenter) 
        return frame
        