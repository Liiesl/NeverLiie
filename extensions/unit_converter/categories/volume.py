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
            },
            "mm3": {
                "factor": 1e-9,
                "display_name": "Cubic Millimeter",
                "aliases": ["cubicmm", "mm^3", "mm³", "millimeter3"]
            },
            "cm3": {
                "factor": 0.001,
                "display_name": "Cubic Centimeter",
                "aliases": ["cc", "cubiccm", "cm^3", "cm³", "centimeter3"]
            },
            "dm3": {
                "factor": 1.0,
                "display_name": "Cubic Decimeter",
                "aliases": ["cubicdm", "dm^3", "dm³", "decimeter3"]
            },
            "µL": {
                "factor": 0.000001,
                "display_name": "Microliter",
                "aliases": ["ul", "microliter", "microliters", "mcl", "microlitre"]
            },
            "nL": {
                "factor": 1e-9,
                "display_name": "Nanoliter",
                "aliases": ["nl", "nanoliter", "nanoliters", "nanolitre"]
            },
            "minim": {
                "factor": 0.0000616115,
                "display_name": "Minim",
                "aliases": ["minim", "minims"]
            },
            "gill": {
                "factor": 0.118294,
                "display_name": "Gill (US)",
                "aliases": ["gill", "gills"]
            },
            "fldr": {
                "factor": 0.00369669,
                "display_name": "Fluid Dram",
                "aliases": ["fluiddram", "fluiddrams", "fl dram", "fl drams"]
            },
            "bu": {
                "factor": 35.2391,
                "display_name": "Bushel (US)",
                "aliases": ["bushel", "bushels"]
            },
            "pk": {
                "factor": 8.80977,
                "display_name": "Peck (US)",
                "aliases": ["peck", "pecks"]
            },
            "bbl": {
                "factor": 158.987,
                "display_name": "Barrel (Petroleum)",
                "aliases": ["barrel", "barrels", "oilbarrel"]
            }
        }
        self._build_lookup()