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

_CURRENCY_CAT = None

def initialize_storage(data_path):
    """Passes the data path to any category that needs it."""
    global _CURRENCY_CAT
    for cat in _CATS:
        if hasattr(cat, 'set_data_path'):
            cat.set_data_path(data_path)
        if isinstance(cat, CurrencyCategory):
            _CURRENCY_CAT = cat

def _is_currency_code(unit_str):
    """Check if the unit string is a valid currency code."""
    unit_str = unit_str.strip().lower()
    if _CURRENCY_CAT:
        return _CURRENCY_CAT.can_handle(unit_str)
    return False

def identify_category(unit_str, target_unit_str=None):
    """
    Identifies which category should handle the unit.
    If both source and target are currency codes, prioritize currency category
    to avoid conflicts with other units (e.g., 'k' for Kelvin).
    """
    unit_str = unit_str.strip().lower()
    target_str = target_unit_str.strip().lower() if target_unit_str else None

    # If both source and target are currency codes, prioritize currency
    if target_str and _is_currency_code(unit_str) and _is_currency_code(target_str):
        return _CURRENCY_CAT

    for cat in _CATS:
        if cat.can_handle(unit_str):
            return cat
    return None