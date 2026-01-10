# extensions/unit_converter/categories/storage.py
from .base import BaseCategory

class StorageCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["b", "kb", "mb", "gb"]
        
        # Base unit: Byte (B)
        # Using Binary prefixes (1024) which is standard for OS reporting
        self.definitions = {
            "b": {
                "factor": 1.0,
                "display_name": "Byte",
                "aliases": ["bytes"]
            },
            "bit": {
                "factor": 0.125, # 1 bit = 1/8 byte
                "display_name": "Bit",
                "aliases": ["bits"]
            },
            "kb": {
                "factor": 1024.0,
                "display_name": "Kilobyte",
                "aliases": ["kib", "kilobytes"]
            },
            "mb": {
                "factor": 1048576.0, # 1024^2
                "display_name": "Megabyte",
                "aliases": ["mib", "megabytes"]
            },
            "gb": {
                "factor": 1073741824.0, # 1024^3
                "display_name": "Gigabyte",
                "aliases": ["gib", "gigabytes"]
            },
            "tb": {
                "factor": 1099511627776.0, # 1024^4
                "display_name": "Terabyte",
                "aliases": ["tib", "terabytes"]
            },
            "pb": {
                "factor": 1125899906842624.0, # 1024^5
                "display_name": "Petabyte",
                "aliases": ["pib", "petabytes"]
            },
            "Kb": {
                "factor": 128.0, # 1024 bits / 8
                "display_name": "Kilobit",
                "aliases": ["kbit", "kilobit", "kilobits"]
            },
            "Mb": {
                "factor": 131072.0, # 1024^2 bits / 8
                "display_name": "Megabit",
                "aliases": ["mbit", "megabit", "megabits"]
            },
            "Gb": {
                "factor": 134217728.0, # 1024^3 bits / 8
                "display_name": "Gigabit",
                "aliases": ["gbit", "gigabit", "gigabits"]
            },
            "Tb": {
                "factor": 137438953472.0, # 1024^4 bits / 8
                "display_name": "Terabit",
                "aliases": ["tbit", "terabit", "terabits"]
            },
            "Pb": {
                "factor": 140737488355328.0, # 1024^5 bits / 8
                "display_name": "Petabit",
                "aliases": ["pbit", "petabit", "petabits"]
            },
            "eb": {
                "factor": 1152921504606846976.0, # 1024^6
                "display_name": "Exabyte",
                "aliases": ["eib", "eb", "exabyte", "exabytes"]
            },
            "zb": {
                "factor": 1180591620717411303424.0, # 1024^7
                "display_name": "Zettabyte",
                "aliases": ["zib", "zb", "zettabyte", "zettabytes"]
            },
            "yb": {
                "factor": 1208925819614629174706176.0, # 1024^8
                "display_name": "Yottabyte",
                "aliases": ["yib", "yb", "yottabyte", "yottabytes"]
            }
        }
        self._build_lookup()