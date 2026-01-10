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
            },
            "µm": {
                "factor": 0.000001,
                "display_name": "Micrometer",
                "aliases": ["micrometer", "micrometers", "um", "microns", "micron"]
            },
            "nm": {
                "factor": 1e-9,
                "display_name": "Nanometer",
                "aliases": ["nanometer", "nanometers"]
            },
            "dm": {
                "factor": 0.1,
                "display_name": "Decimeter",
                "aliases": ["decimeter", "decimeters"]
            },
            "dam": {
                "factor": 10.0,
                "display_name": "Decameter",
                "aliases": ["decameter", "decameters", "dekameter", "dekameters"]
            },
            "hm": {
                "factor": 100.0,
                "display_name": "Hectometer",
                "aliases": ["hectometer", "hectometers"]
            },
            "nmi": {
                "factor": 1852.0,
                "display_name": "Nautical Mile",
                "aliases": ["nmiles", "nauticalmiles"]
            },
            "fur": {
                "factor": 201.168,
                "display_name": "Furlong",
                "aliases": ["furlong", "furlongs"]
            },
            "ch": {
                "factor": 20.1168,
                "display_name": "Chain",
                "aliases": ["chain", "chains"]
            },
            "rd": {
                "factor": 5.0292,
                "display_name": "Rod",
                "aliases": ["rod", "rods", "pole", "perch"]
            },
            "fath": {
                "factor": 1.8288,
                "display_name": "Fathom",
                "aliases": ["fathom", "fathoms"]
            },
            "hand": {
                "factor": 0.1016,
                "display_name": "Hand",
                "aliases": ["hands"]
            },
            "cable": {
                "factor": 185.2,
                "display_name": "Cable",
                "aliases": ["cables"]
            },
            "Å": {
                "factor": 1e-10,
                "display_name": "Angstrom",
                "aliases": ["angstrom", "angstroms"]
            },
            "au": {
                "factor": 149597870700.0,
                "display_name": "Astronomical Unit",
                "aliases": ["au", "astronomicalunit"]
            },
            "ly": {
                "factor": 9.4607304725808e15,
                "display_name": "Light Year",
                "aliases": ["lightyear", "lightyears"]
            },
            "pc": {
                "factor": 3.0856775814913673e16,
                "display_name": "Parsec",
                "aliases": ["parsec", "parsecs"]
            }
        }
        self._build_lookup()