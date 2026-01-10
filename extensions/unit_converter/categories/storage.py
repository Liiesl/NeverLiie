# extensions/unit_converter/categories/storage.py
from .base import BaseCategory

class StorageCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["b", "kb", "mb", "gb", "tb"]
        
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
            }
        }
        self._build_lookup()