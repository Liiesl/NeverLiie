# api/extension.py
from typing import List
from .types import ResultItem

class Extension:
    def __init__(self, core_app):
        self.core = core_app # Access to core.show_notification, etc

    def on_input(self, text: str) -> List[ResultItem]:
        return []