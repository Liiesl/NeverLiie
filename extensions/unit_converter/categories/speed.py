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
            },
            "cm/s": {
                "factor": 0.01,
                "display_name": "Centimeters/Sec",
                "aliases": ["cmps", "cmpersecond"]
            },
            "dm/s": {
                "factor": 0.1,
                "display_name": "Decimeters/Sec",
                "aliases": ["dmps", "dmpersecond"]
            },
            "mm/s": {
                "factor": 0.001,
                "display_name": "Millimeters/Sec",
                "aliases": ["mmps", "mmpersecond"]
            },
            "ft/min": {
                "factor": 0.00508,
                "display_name": "Feet/Min",
                "aliases": ["ftpm", "ftpmin", "ftpminute"]
            },
            "ft/h": {
                "factor": 0.0000846667,
                "display_name": "Feet/Hour",
                "aliases": ["ftph", "ftphour"]
            },
            "in/s": {
                "factor": 0.0254,
                "display_name": "Inches/Sec",
                "aliases": ["inps", "inpersecond"]
            },
            "in/min": {
                "factor": 0.000423333,
                "display_name": "Inches/Min",
                "aliases": ["inpm", "inpmin", "inpminute"]
            },
            "in/h": {
                "factor": 0.00000705556,
                "display_name": "Inches/Hour",
                "aliases": ["inph", "inphour"]
            },
            "km/s": {
                "factor": 1000.0,
                "display_name": "Km/Sec",
                "aliases": ["kmps", "kmpsec", "kmpersecond"]
            },
            "km/min": {
                "factor": 16.6667,
                "display_name": "Km/Min",
                "aliases": ["kmpm", "kmpmin", "kmpminute"]
            },
            "m/min": {
                "factor": 0.0166667,
                "display_name": "Meters/Min",
                "aliases": ["mpm", "mpmin", "mpminute", "meterperminute"]
            },
            "m/h": {
                "factor": 0.000277778,
                "display_name": "Meters/Hour",
                "aliases": ["mphm", "mhour", "meterperhour"]
            },
            "mi/s": {
                "factor": 1609.34,
                "display_name": "Miles/Sec",
                "aliases": ["mips", "mipsec", "mipersecond"]
            },
            "mi/min": {
                "factor": 26.8224,
                "display_name": "Miles/Min",
                "aliases": ["mipm", "mipmin", "mipminute"]
            },
            "yd/s": {
                "factor": 0.9144,
                "display_name": "Yards/Sec",
                "aliases": ["ydps", "ydpersecond"]
            },
            "yd/min": {
                "factor": 0.01524,
                "display_name": "Yards/Min",
                "aliases": ["ydpm", "ydpmin", "ydpminute"]
            },
            "yd/h": {
                "factor": 0.000254,
                "display_name": "Yards/Hour",
                "aliases": ["ydph", "ydphour"]
            }
        }
        self._build_lookup()