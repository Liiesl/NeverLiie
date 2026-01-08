# extensions/calculator/__init__.py
import math
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QClipboard, QGuiApplication

from api.extension import Extension
from api.types import ResultItem, Action

# --- MATH LOGIC ---
class MathEngine:
    def __init__(self):
        # Create a safe dictionary of allowed math functions
        self.allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        self.allowed_names.update({
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow
        })

    def evaluate(self, expression):
        # 1. Pre-process convenient syntax
        # Allow "2^3" for power instead of bitwise XOR
        expr = expression.replace("^", "**")
        # Allow "x" for multiplication (e.g. 5x5), but be careful not to break hex or functions like 'max'
        # Simple heuristic: if 'x' is surrounded by digits or spaces
        expr = expr.replace("×", "*") 
        
        try:
            # 2. Safety: Only evaluate within the allowed namespace.
            # "__builtins__": None prevents access to dangerous functions like open() or import
            result = eval(expr, {"__builtins__": None}, self.allowed_names)
            return result
        except Exception:
            return None

# --- CUSTOM WIDGET ---
class CalculatorWidget(QWidget):
    def __init__(self, expression, result_str, is_error=False):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(15)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        
        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(0, 5, 0, 5)
        inner_layout.setSpacing(2)
        
        # Top: The Expression (Gray, smaller)
        lbl_expr = QLabel(f"{expression} =")
        lbl_expr.setStyleSheet("color: #a6adc8; font-weight: 500;")
        lbl_expr.setFont(QFont("Segoe UI", 12))
        lbl_expr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Bottom: The Result (White/Accent, Huge)
        lbl_res = QLabel(result_str)
        if is_error:
            lbl_res.setStyleSheet("color: #f38ba8; font-weight: bold;") # Red error color
        else:
            lbl_res.setStyleSheet("color: #ffffff; font-weight: bold;")
            
        lbl_res.setFont(QFont("Segoe UI", 26))
        lbl_res.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        inner_layout.addWidget(lbl_expr)
        inner_layout.addWidget(lbl_res)
        
        # Spacer to push text to right (standard calculator alignment)
        layout.addStretch() 
        layout.addWidget(self.container)

class CalculatorExtension(Extension):
    def __init__(self, core_app):
        super().__init__(core_app)
        self.engine = MathEngine()

    def on_input(self, text):
        text = text.strip()
        if not text:
            return []

        # Heuristic: Is this likely a math request?
        # Check for operators, digits, or known math functions
        math_chars = set("0123456789+-*/%^.() ")
        has_operator = any(c in "+-*/%^" for c in text)
        is_function = any(func in text for func in ["sqrt", "sin", "cos", "tan", "log", "pi", "e"])
        
        # If it's just a clean integer (e.g. "2023"), don't show calculator unless it has an operator
        # This allows file search to take precedence for simple numbers.
        if text.isdigit() and len(text) < 4: 
            return []

        # Try to calculate
        val = self.engine.evaluate(text)
        
        if val is not None:
            # Format Result
            if isinstance(val, (int, float)):
                # Handle large numbers or float precision
                if abs(val) > 1e10 or (abs(val) < 1e-6 and val != 0):
                    res_str = f"{val:.6e}" # Scientific notation
                else:
                    # nicely formatted string with comma separators, max 6 decimal places
                    res_str = f"{val:,.6f}".rstrip('0').rstrip('.')
            else:
                res_str = str(val)

            # --- ACTIONS ---
            def copy_result():
                QGuiApplication.clipboard().setText(res_str)

            def copy_equation():
                QGuiApplication.clipboard().setText(f"{text} = {res_str}")

            # --- FACTORY ---
            def make_widget():
                return CalculatorWidget(text, res_str)

            return [ResultItem(
                id="calc_result",
                name=res_str,
                description=f"Result of {text}",
                action=Action("Copy Result", copy_result),
                score=1000, # High score ensures it stays at top if valid
                widget_factory=make_widget,
                height=80
        )]

Extension = CalculatorExtension