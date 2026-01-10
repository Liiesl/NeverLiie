# extensions/unit_converter/categories/speed.py
from .base import BaseCategory

class SpeedCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["km/h", "mph", "m/s", "kn"]
        
        # Base unit: meters per second (m/s)
        self.definitions = {
            "m/s": {
                "factor": 1.0,
                "display_name": "Meters/Sec",
                "aliases": ["mps", "meterpersecond"]
            },
            "km/h": {
                "factor": 0.277778,
                "display_name": "Km/Hour",
                "aliases": ["kph", "kmh", "kmph"]
            },
            "mph": {
                "factor": 0.44704,
                "display_name": "Miles/Hour",
                "aliases": ["mi/h", "mileperhour"]
            },
            "kn": {
                "factor": 0.514444,
                "display_name": "Knot",
                "aliases": ["knots", "knot", "kt"]
            },
            "ft/s": {
                "factor": 0.3048,
                "display_name": "Feet/Sec",
                "aliases": ["fps", "ftps"]
            },
            "mach": {
                "factor": 343.0, # Standard atmosphere at sea level
                "display_name": "Mach",
                "aliases": ["ma"]
            }
        }
        self._build_lookup()