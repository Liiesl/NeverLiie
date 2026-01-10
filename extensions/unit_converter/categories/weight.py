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
            },
            "carat": {
                "factor": 0.0002,
                "display_name": "Carat",
                "aliases": ["carats", "ct"]
            },
            "stone": {
                "factor": 6.35029,
                "display_name": "Stone",
                "aliases": ["stones", "st"]
            },
            "uston": {
                "factor": 907.185,
                "display_name": "Short Ton (US)",
                "aliases": ["shortton", "shortton", "ustons", "short tons", "us tons", "short ton", "us ton"]
            },
            "imperialton": {
                "factor": 1016.05,
                "display_name": "Long Ton (Imperial)",
                "aliases": ["longton", "longton", "imperialtons", "long tons", "imperial tons", "long ton", "imperial ton"]
            },
            "tonne": {
                "factor": 1000.0,
                "display_name": "Tonne",
                "aliases": ["tonnes", "ton", "metric ton", "metric tons"]
            },
            "grain": {
                "factor": 0.0000647989,
                "display_name": "Grain",
                "aliases": ["grains", "gr"]
            },
            "dram": {
                "factor": 0.00177185,
                "display_name": "Dram",
                "aliases": ["drams", "dr"]
            }
        }
        self._build_lookup()