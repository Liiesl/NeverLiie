# extensions/unit_converter/__init__.py
import os
import re
from api.extension import Extension
from . import categories

class UnitConverterExtension(Extension):
    def __init__(self, context):
        super().__init__(context)
        
        # 1. Ensure the data directory exists on disk
        if not os.path.exists(context.data_path):
            os.makedirs(context.data_path, exist_ok=True)
            
        # 2. Initialize categories with the path
        categories.initialize_storage(context.data_path)

        # Regex setup
        # Value group: (\d+(?:\.\d+)?)
        # Unit group: ([a-zA-Z$€£¥°%/²³^]+[23]?) 
        #   - Allows standard letters and currency symbols
        #   - Allows ° (degrees), % (percent), / (per), ²³ (superscripts), ^ (caret)
        #   - Allows trailing 2 or 3 for m2/m3 styles
        unit_regex = r"([a-zA-Z$€£¥°%/²³^]+[23]?)"
        
        self.regex_single = re.compile(rf"^(\d+(?:\.\d+)?)\s*{unit_regex}$")
        self.regex_to = re.compile(rf"^(\d+(?:\.\d+)?)\s*{unit_regex}\s+to\s+{unit_regex}$", re.IGNORECASE)

    def on_input(self, text):
        text = text.strip()
        if not text: return []

        # Check "X unit to Y unit"
        match_to = self.regex_to.match(text)
        if match_to:
            val = float(match_to.group(1))
            src = match_to.group(2)
            tgt = match_to.group(3)
            cat = categories.identify_category(src)
            if cat and cat.can_handle(tgt):
                return cat.get_specific_result(val, src, tgt)
            return []

        # Check "X unit" (Auto convert)
        match_single = self.regex_single.match(text)
        if match_single:
            val = float(match_single.group(1))
            src = match_single.group(2)
            cat = categories.identify_category(src)
            if cat:
                return cat.get_auto_results(val, src)

        return []

# Export
Extension = UnitConverterExtension