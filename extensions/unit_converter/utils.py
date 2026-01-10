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

def format_currency(val):
    """
    Formats currency values with special rules:
    - Default to 2 decimal places
    - If value < 1 and first 2 decimals are 0.00, expand until first non-zero digit
    - If value >= 1, show up to 2 decimal places and remove trailing zeros
    """
    if val is None: return ""

    # Take absolute value for comparisons, but preserve sign for display
    is_negative = val < 0
    abs_val = abs(val)

    # Case 1: Value >= 1 - show up to 2 decimals, remove trailing zeros
    if abs_val >= 1:
        formatted = f"{abs_val:.2f}".rstrip('0').rstrip('.')
    else:
        # Case 2: Value < 1
        # Check if first 2 decimals are 0.00
        rounded_2dp = round(abs_val, 2)
        if rounded_2dp == 0:
            # Find first non-zero digit position
            str_val = f"{abs_val:.15f}"
            after_decimal = str_val.split('.')[1]
            first_non_zero = None
            for i, digit in enumerate(after_decimal):
                if digit != '0':
                    first_non_zero = i + 1
                    break

            if first_non_zero:
                formatted = f"{abs_val:.{first_non_zero}f}".rstrip('0').rstrip('.')
            else:
                formatted = "0"
        else:
            # Not all zeros, use up to 2 decimals, remove trailing zeros
            formatted = f"{abs_val:.2f}".rstrip('0').rstrip('.')

    # Add sign back if negative
    if is_negative:
        formatted = f"-{formatted}"

    # Add comma separators for thousands
    try:
        if '.' in formatted:
            int_part, dec_part = formatted.split('.')
            if int_part and int_part != '0':
                formatted_int = f"{int(int_part):,}"
                formatted = f"{formatted_int}.{dec_part}"
            else:
                # Keep leading zero for values < 1
                formatted = f"{int_part}.{dec_part}"
        else:
            if formatted and formatted != '0':
                formatted = f"{int(float(formatted)):,}"
    except:
        pass

    return formatted

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
        