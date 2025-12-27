# api/extension.py
from typing import List, Optional, Any
from PySide6.QtWidgets import QWidget
from .types import ResultItem

class Extension:
    def __init__(self, core_app):
        self.core = core_app
        self.id = "" # Assigned by plugin manager

    def on_input(self, text: str) -> List[ResultItem]:
        """Return search results for the root launcher."""
        return []

    def get_extension_view(self, parent_window: QWidget) -> Optional[QWidget]:
        """
        If this returns a QWidget, the launcher will switch to this view 
        when the extension is selected.
        If None, it performs a standard search scoped to this extension.
        """
        return None