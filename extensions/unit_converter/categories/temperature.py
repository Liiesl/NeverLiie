# extensions/unit_converter/categories/temperature.py
from PySide6.QtGui import QGuiApplication
from api.types import ResultItem, Action
from .base import BaseCategory
from .. import utils

class TemperatureCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["c", "f", "k", "r"]
        
        # We only use definitions for display names and aliases here.
        # Factors are ignored because we override the math logic.
        self.definitions = {
            "c": { "factor": 0, "display_name": "Celsius", "aliases": ["°c", "degc", "celsius"] },
            "f": { "factor": 0, "display_name": "Fahrenheit", "aliases": ["°f", "degf", "fahrenheit"] },
            "k": { "factor": 0, "display_name": "Kelvin", "aliases": ["kelvin"] },
            "r": { "factor": 0, "display_name": "Rankine", "aliases": ["°r", "degr", "rankine"] }
        }
        self._build_lookup()

    def _to_celsius(self, val, unit):
        if unit == 'c': return val
        if unit == 'f': return (val - 32) * 5/9
        if unit == 'k': return val - 273.15
        if unit == 'r': return (val - 491.67) * 5/9
        return val

    def _from_celsius(self, val_c, target_unit):
        if target_unit == 'c': return val_c
        if target_unit == 'f': return (val_c * 9/5) + 32
        if target_unit == 'k': return val_c + 273.15
        if target_unit == 'r': return (val_c * 9/5) + 491.67
        return val_c

    def convert(self, val, src_unit_str, target_unit_str):
        src_sym = self.get_canonical(src_unit_str)
        tgt_sym = self.get_canonical(target_unit_str)
        if not src_sym or not tgt_sym: return None
        
        val_c = self._to_celsius(val, src_sym)
        return self._from_celsius(val_c, tgt_sym)

    def get_auto_results(self, val, src_unit_str):
        src_data = self.get_details(src_unit_str)
        if not src_data: return []

        src_sym = src_data['symbol']
        results_data = []

        # Convert to Base (C) then to others
        val_c = self._to_celsius(val, src_sym)

        for t_sym in self.default_targets:
            if t_sym == src_sym: continue
            
            res = self._from_celsius(val_c, t_sym)
            t_data = self.definitions[t_sym]
            
            results_data.append((
                utils.format_short(res),
                t_sym.upper(), # Uppercase looks better for C/F/K
                t_data['display_name']
            ))

        if not results_data: return []

        def factory():
            return utils.ConverterWidget(
                input_data=(utils.format_short(val), src_sym.upper(), src_data['display_name']),
                output_data_list=results_data
            )
        
        # For copy string
        copy_parts = []
        for r in results_data:
            # Re-calculate for full precision copy
            raw_res = self._from_celsius(val_c, r[1].lower())
            copy_parts.append(f"{utils.format_full(raw_res)} {r[1]}")
        
        copy_str = " | ".join(copy_parts)

        return [ResultItem(
            id=f"unit_temp_{src_sym}",
            name=f"Convert {src_data['display_name']}",
            description=f"Temperature conversion for {utils.format_short(val)}",
            score=100,
            widget_factory=factory,
            height=100,
            action=Action("Copy All", lambda: QGuiApplication.clipboard().setText(copy_str))
        )]