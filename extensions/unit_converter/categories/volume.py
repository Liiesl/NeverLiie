# extensions/unit_converter/categories/volume.py
from .base import BaseCategory

class VolumeCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["l", "gal", "fl oz", "m3"]
        
        # Base unit: Liter (l)
        self.definitions = {
            "l": {
                "factor": 1.0,
                "display_name": "Liter",
                "aliases": ["liters", "litre", "litres"]
            },
            "ml": {
                "factor": 0.001,
                "display_name": "Milliliter",
                "aliases": ["milliliters", "millilitre"]
            },
            "gal": {
                "factor": 3.78541,
                "display_name": "Gallon (US)",
                "aliases": ["gallon", "gallons"]
            },
            "qt": {
                "factor": 0.946353,
                "display_name": "Quart (US)",
                "aliases": ["quart", "quarts"]
            },
            "pt": {
                "factor": 0.473176,
                "display_name": "Pint (US)",
                "aliases": ["pint", "pints"]
            },
            "cup": {
                "factor": 0.24, # Metric cup approx
                "display_name": "Cup",
                "aliases": ["cups"]
            },
            "fl oz": {
                "factor": 0.0295735,
                "display_name": "Fluid Ounce",
                "aliases": ["floz", "oz", "ounce", "ounces"]
            },
            "tbsp": {
                "factor": 0.0147868,
                "display_name": "Tablespoon",
                "aliases": ["tablespoon", "tablespoons"]
            },
            "tsp": {
                "factor": 0.00492892,
                "display_name": "Teaspoon",
                "aliases": ["teaspoon", "teaspoons"]
            },
            "m3": {
                "factor": 1000.0,
                "display_name": "Cubic Meter",
                "aliases": ["cubicmeter", "m^3", "m³"]
            },
             "ft3": {
                "factor": 28.3168,
                "display_name": "Cubic Foot",
                "aliases": ["cubicfoot", "ft^3", "ft³"]
            }
        }
        self._build_lookup()