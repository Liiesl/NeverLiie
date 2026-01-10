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
            },
            "sqyd": {
                "factor": 0.836127,
                "display_name": "Square Yard",
                "aliases": ["yd2", "yd^2", "sqyard", "squareyard"]
            },
            "dm2": {
                "factor": 0.01,
                "display_name": "Square Decimeter",
                "aliases": ["sqdm", "dm^2", "dm²", "decimeter2"]
            },
            "cm2": {
                "factor": 0.0001,
                "display_name": "Square Centimeter",
                "aliases": ["sqcm", "cm^2", "cm²", "centimeter2"]
            },
            "mm2": {
                "factor": 0.000001,
                "display_name": "Square Millimeter",
                "aliases": ["sqmm", "mm^2", "mm²", "millimeter2"]
            },
            "a": {
                "factor": 100.0,
                "display_name": "Are",
                "aliases": ["are", "ares"]
            },
            "barn": {
                "factor": 1e-28,
                "display_name": "Barn",
                "aliases": ["barns"]
            }
        }
        self._build_lookup()