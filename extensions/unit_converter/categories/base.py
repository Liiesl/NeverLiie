# extensions/unit_converter/categories/base.py
from PySide6.QtGui import QGuiApplication
from api.types import ResultItem, Action
from .. import utils

class BaseCategory:
    def __init__(self):
        # Structure: 
        # { 
        #   "symbol": { 
        #       "factor": float, 
        #       "display_name": str, 
        #       "aliases": list[str] 
        #   } 
        # }
        self.definitions = {}
        
        # Internal optimized map: "alias/name" -> "symbol"
        self._lookup_map = {}
        self.default_targets = []

    def _build_lookup(self):
        """Generates the flat lookup map from the definitions matrix."""
        self._lookup_map = {}
        for symbol, data in self.definitions.items():
            # Map the symbol itself (e.g. "kg")
            self._lookup_map[symbol.lower()] = symbol
            
            # Map the display name (e.g. "kilogram")
            if "display_name" in data:
                self._lookup_map[data["display_name"].lower()] = symbol
            
            # Map all aliases
            for alias in data.get("aliases", []):
                self._lookup_map[alias.lower()] = symbol

    def can_handle(self, unit_str):
        return unit_str.lower() in self._lookup_map

    def get_canonical(self, unit_str):
        """Returns the symbol (Key) for a given alias."""
        return self._lookup_map.get(unit_str.lower())

    def get_details(self, unit_str):
        """Returns {factor, display_name, aliases, symbol}."""
        symbol = self.get_canonical(unit_str)
        if symbol:
            data = self.definitions.get(symbol).copy()
            data['symbol'] = symbol # Inject key into data for convenience
            return data
        return None

    def convert(self, val, src_unit_str, target_unit_str):
        src_data = self.get_details(src_unit_str)
        tgt_data = self.get_details(target_unit_str)
        
        if not src_data or not tgt_data: 
            return None
            
        src_f = src_data['factor']
        tgt_f = tgt_data['factor']
        
        return (val * src_f) / tgt_f

    def get_auto_results(self, val, src_unit_str):
        src_data = self.get_details(src_unit_str)
        if not src_data: return []
        
        src_factor = src_data['factor']
        src_symbol = src_data['symbol'] # e.g. "kg"
        src_name = src_data['display_name'] # e.g. "Kilogram"

        results_data = []

        # Iterate over default targets (keys)
        for t_symbol in self.default_targets:
            if t_symbol not in self.definitions: continue
            
            t_data = self.definitions[t_symbol]
            t_factor = t_data['factor']
            
            if abs(src_factor - t_factor) < 1e-9: continue
            
            res = (val * src_factor) / t_factor
            
            # Tuple: (Formatted Value, Symbol, Display Name)
            results_data.append((
                utils.format_short(res), 
                t_symbol, 
                t_data['display_name']
            ))
            
            if len(results_data) >= 3: break
        
        if not results_data: return []

        def factory():
            return utils.ConverterWidget(
                input_data=(utils.format_short(val), src_symbol, src_name),
                output_data_list=results_data
            )
        
        # When copying ALL, we use FULL precision for utility
        copy_str = " | ".join([f"{utils.format_full((val * src_factor) / self.definitions[r[1]]['factor'])} {r[1]}" for r in results_data])

        return [ResultItem(
            id=f"unit_auto_{src_symbol}",
            name=f"Convert {src_name}", 
            description=f"Standard conversion for {utils.format_short(val)} {src_symbol}",
            score=100,
            widget_factory=factory,
            height=100,
            action=Action("Copy All", lambda: QGuiApplication.clipboard().setText(copy_str))
        )]

    def get_specific_result(self, val, src_unit_str, target_unit_str):
        src_data = self.get_details(src_unit_str)
        tgt_data = self.get_details(target_unit_str)
        
        if not src_data or not tgt_data: return []

        res = self.convert(val, src_unit_str, target_unit_str)
        if res is None: return []

        # Use FULL format for specific results (commas and high precision)
        disp_val = utils.format_full(res)
        input_val_str = utils.format_full(val)
        
        title = f"{input_val_str} {src_data['display_name']} = {disp_val} {tgt_data['display_name']}"
        
        def factory():
            return utils.ConverterWidget(
                input_data=(
                    input_val_str, 
                    src_data['symbol'],
                    src_data['display_name']),
                output_data_list=[(
                    disp_val,
                    tgt_data['symbol'],
                    tgt_data['display_name'])]
            )

        return [ResultItem(
            id=f"unit_specific",
            name=title,
            description="Specific Conversion",
            score=1000,
            widget_factory=factory,
            height=100,
            # Copy action uses the clean full value (no commas for easier pasting into calculators)
            action=Action("Copy Result", lambda: QGuiApplication.clipboard().setText(str(round(res, 10)).rstrip('0').rstrip('.')))
        )]