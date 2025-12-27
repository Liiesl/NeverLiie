# api/extension.py
from typing import List, Optional, Any
from PySide6.QtWidgets import QWidget
from .types import ResultItem
# from .context import ExtensionContext (Implicit import for type hinting)

class Extension:
    def __init__(self, context):
        """
        :param context: An instance of api.context.ExtensionContext
        """
        self.context = context
        # ID is now managed by the context, but we can expose it if needed for UI labels
        self.id = context._ext_id 

    def on_input(self, text: str) -> List[ResultItem]:
        """Return search results for the root launcher."""
        return []

    def get_extension_view(self, parent_window: QWidget) -> Optional[QWidget]:
        """
        Return a QWidget (e.g., Chat View) to be displayed in the launcher.
        """
        return None

    def get_settings_widget(self) -> Optional[QWidget]:
        """
        Return a QWidget to be displayed in the Settings window.
        """
        return None

    # --- Convenience Wrappers ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.context.get_setting(key, default)

    def set_setting(self, key: str, value: Any):
        self.context.set_setting(key, value)