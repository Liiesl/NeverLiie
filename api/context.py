# api/context.py
from typing import Any, Optional

class ExtensionContext:
    """
    A restricted interface for Extensions to interact with the host application.
    Prevents extensions from accessing global state or other extensions' data.
    """
    def __init__(self, core_app, ext_id: str):
        self._core = core_app
        self._ext_id = ext_id

    # --- Secure Settings Access ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting specifically for this extension ID."""
        return self._core.settings.get_ext_setting(self._ext_id, key, default)

    def set_setting(self, key: str, value: Any):
        """Set a setting specifically for this extension ID."""
        self._core.settings.set_ext_setting(self._ext_id, key, value)

    # --- Window Control (Exposed safely) ---
    def hide_window(self):
        self._core.hide_window()

    def show_window(self):
        self._core.show_window()

    def refresh_ui(self):
        """Trigger a UI repaint if necessary."""
        # Useful if settings changed extension appearance
        pass