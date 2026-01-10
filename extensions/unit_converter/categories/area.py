# extensions/unit_converter/categories/area.py
from .base import BaseCategory

class AreaCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["m2", "sqft", "ac", "ha"]
        
        # Base unit: Square Meter (m2)
        self.definitions = {
            "m2": {
                "factor": 1.0,
                "display_name": "Square Meter",
                "aliases": ["sqm", "m^2", "m²", "meter2"]
            },
            "sqft": {
                "factor": 0.092903,
                "display_name": "Square Foot",
                "aliases": ["ft2", "ft^2", "sqfeet", "sqfoot"]
            },
            "sqin": {
                "factor": 0.00064516,
                "display_name": "Square Inch",
                "aliases": ["in2", "in^2", "sqinch"]
            },
            "ac": {
                "factor": 4046.86,
                "display_name": "Acre",
                "aliases": ["acre", "acres"]
            },
            "ha": {
                "factor": 10000.0,
                "display_name": "Hectare",
                "aliases": ["hectare", "hectares"]
            },
            "km2": {
                "factor": 1000000.0,
                "display_name": "Square Km",
                "aliases": ["sqkm", "km^2", "km²"]
            },
            "sqmi": {
                "factor": 2589988.11,
                "display_name": "Square Mile",
                "aliases": ["mi2", "mi^2", "mile2"]
            }
        }
        self._build_lookup()