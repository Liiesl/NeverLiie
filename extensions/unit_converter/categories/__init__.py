# extensions/unit_converter/categories/__init__.py
from .length import LengthCategory
from .weight import WeightCategory
from .time import TimeCategory
from .currency import CurrencyCategory
from .temperature import TemperatureCategory
from .volume import VolumeCategory
from .speed import SpeedCategory
from .area import AreaCategory
from .storage import StorageCategory

_CATS = [
    LengthCategory(),
    WeightCategory(),
    TimeCategory(),
    CurrencyCategory(),
    TemperatureCategory(),
    VolumeCategory(),
    SpeedCategory(),
    AreaCategory(),
    StorageCategory()
]

def initialize_storage(data_path):
    """Passes the data path to any category that needs it."""
    for cat in _CATS:
        if hasattr(cat, 'set_data_path'):
            cat.set_data_path(data_path)

def identify_category(unit_str):
    unit_str = unit_str.strip().lower()
    for cat in _CATS:
        if cat.can_handle(unit_str):
            return cat
    return None