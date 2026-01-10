# extensions/unit_converter/categories/length.py
from .base import BaseCategory

class LengthCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["m", "cm", "ft", "in"]
        
        # Key = Symbol (used in Widget)
        # display_name = Full name (used in Result Text)
        self.definitions = {
            "m": {
                "factor": 1.0,
                "display_name": "Meter",
                "aliases": ["meters"]
            },
            "cm": {
                "factor": 0.01,
                "display_name": "Centimeter",
                "aliases": ["centimeters"]
            },
            "mm": {
                "factor": 0.001,
                "display_name": "Millimeter",
                "aliases": ["millimeters"]
            },
            "km": {
                "factor": 1000.0,
                "display_name": "Kilometer",
                "aliases": ["kilometers"]
            },
            "in": {
                "factor": 0.0254,
                "display_name": "Inch",
                "aliases": ["inches"]
            },
            "ft": {
                "factor": 0.3048,
                "display_name": "Foot",
                "aliases": ["feet"]
            },
            "yd": {
                "factor": 0.9144,
                "display_name": "Yard",
                "aliases": ["yards"]
            },
            "mi": {
                "factor": 1609.34,
                "display_name": "Mile",
                "aliases": ["miles"]
            }
        }
        self._build_lookup()