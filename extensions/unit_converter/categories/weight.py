# extensions/unit_converter/categories/weight.py
from .base import BaseCategory

class WeightCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["kg", "g", "lb", "oz"]
        
        self.definitions = {
            "kg": {
                "factor": 1.0,
                "display_name": "Kilogram",
                "aliases": ["kilograms", "kilo", "kilos"]
            },
            "g": {
                "factor": 0.001,
                "display_name": "Gram",
                "aliases": ["grams"]
            },
            "mg": {
                "factor": 0.000001,
                "display_name": "Milligram",
                "aliases": ["milligrams"]
            },
            "lb": {
                "factor": 0.453592,
                "display_name": "Pound",
                "aliases": ["lbs", "pounds"]
            },
            "oz": {
                "factor": 0.0283495,
                "display_name": "Ounce",
                "aliases": ["ounces"]
            }
        }
        self._build_lookup()