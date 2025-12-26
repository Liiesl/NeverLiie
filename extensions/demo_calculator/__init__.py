# extensions/demo_calculator/__init__.py
from api.extension import Extension
from api.types import ResultItem, Action

class CalculatorPlugin(Extension):
    def on_input(self, text):
        # Only trigger if it looks like math
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in text):
            return []
        
        try:
            res = str(eval(text))
            
            def copy_to_clipboard():
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                clipboard.setText(res)

            return [ResultItem(
                id="calc",
                name=f"= {res}",
                description="Action: Copy to clipboard",
                action=Action("Copy", copy_to_clipboard),
                score=999 # Always top if math works
            )]
        except:
            return []

Plugin = CalculatorPlugin