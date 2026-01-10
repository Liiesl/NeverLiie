# extensions/unit_converter/categories/time.py
from PySide6.QtGui import QGuiApplication
from api.types import ResultItem, Action
from .base import BaseCategory
from .. import utils

class TimeCategory(BaseCategory):
    def __init__(self):
        super().__init__()
        self.default_targets = ["s", "min", "h", "y"]
        
        self.definitions = {
            "s": {
                "factor": 1.0,
                "display_name": "Second",
                "aliases": ["sec", "seconds"]
            },
            "min": {
                "factor": 60.0,
                "display_name": "Minute",
                "aliases": ["minutes"]
            },
            "h": {
                "factor": 3600.0,
                "display_name": "Hour",
                "aliases": ["hr", "hours"]
            },
            "d": {
                "factor": 86400.0,
                "display_name": "Day",
                "aliases": ["days"]
            },
            "w": {
                "factor": 604800.0,
                "display_name": "Week",
                "aliases": ["weeks"]
            },
            "mo": {
                "factor": 2628000.0,
                "display_name": "Month",
                "aliases": ["months"]
            },
            "y": {
                "factor": 31536000.0,
                "display_name": "Year",
                "aliases": ["yr", "years"]
            }
        }
        self._build_lookup()

    def get_auto_results(self, val, src_unit_str):
        src_data = self.get_details(src_unit_str)
        if not src_data: return []

        total_seconds = val * src_data['factor']
        simplified = self._simplify_seconds(total_seconds)

        if not simplified: return []

        def factory():
            return utils.ConverterWidget(
                input_data=(
                    utils.format_val(val), 
                    src_data['symbol'], 
                    src_data['display_name']
                ),
                output_data_list=[(simplified, "", "Duration")] 
            )

        return [ResultItem(
            id=f"unit_time_simplify",
            name=f"Time Duration",
            description=f"Simplified: {simplified}",
            score=100,
            widget_factory=factory,
            height=100,
            action=Action("Copy Result", lambda: QGuiApplication.clipboard().setText(simplified))
        )]

    def get_specific_result(self, val, src_unit_str, target_unit_str):
        res = self.convert(val, src_unit_str, target_unit_str)
        if res is None: return []

        src_data = self.get_details(src_unit_str)
        tgt_data = self.get_details(target_unit_str)

        # Fancy H:MM:SS logic
        display_str = self._format_complex(val, src_data, tgt_data)
        if not display_str:
            display_str = utils.format_val(res)

        title = f"{utils.format_val(val)} {src_data['display_name']} = {display_str} {tgt_data['display_name']}"

        def factory():
            return utils.ConverterWidget(
                input_data=(
                    utils.format_val(val), 
                    src_data['symbol'], 
                    src_data['display_name']
                ),
                output_data_list=[(
                    display_str, 
                    tgt_data['symbol'], 
                    tgt_data['display_name']
                )]
            )

        return [ResultItem(
            id="unit_time_spec",
            name=title,
            description="Time Conversion",
            score=1000,
            widget_factory=factory,
            height=100,
            action=Action("Copy Result", lambda: QGuiApplication.clipboard().setText(display_str))
        )]

    def _simplify_seconds(self, total_seconds):
        if total_seconds < 1: return f"{utils.format_val(total_seconds)}s"
        Y, MO, D, H, M = 31536000, 2628000, 86400, 3600, 60
        
        curr = total_seconds
        y = int(curr // Y); curr %= Y
        mo = int(curr // MO); curr %= MO
        d = int(curr // D); curr %= D
        h = int(curr // H); curr %= H
        m = int(curr // M)
        s = int(round(curr % M))

        parts = []
        if y > 0: parts.append(f"{y}y")
        if mo > 0: parts.append(f"{mo}mo")
        if d > 0: parts.append(f"{d}d")
        if y > 0: return " ".join(parts) 
        
        if h > 0: parts.append(f"{h}h")
        if m > 0: parts.append(f"{m}m")
        if s > 0: parts.append(f"{s}s")
        
        return " ".join(parts) if parts else "0s"

    def _format_complex(self, val, src_data, tgt_data):
        total_seconds = val * src_data['factor']
        t_id = tgt_data['symbol']
        
        if t_id == 'h':
            if abs(total_seconds % 3600) < 1: return None 
            h = int(total_seconds // 3600)
            m = int((total_seconds % 3600) // 60)
            s = int(total_seconds % 60)
            return f"{h}:{m:02}:{s:02}"
        return None