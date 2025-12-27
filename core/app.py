# core/app.py
import sys
import os
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal, QTimer, QAbstractNativeEventFilter

from .ui import LauncherWindow, create_app_icon
from .settings_ui import SettingsWindow
from .settings import SettingsManager
from .plugin_manager import PluginManager
from .win32_utils import (
    WM_HOTKEY, MOD_ALT, VK_SPACE, MSG, 
    force_focus, get_foreground_window, user32
)

# --- HELPER CLASSES (Moved to Global Scope) ---
class SettingsAction:
    def __init__(self, handler):
        self.handler = handler
        self.close_on_action = True 

class SettingsItem:
    def __init__(self, action):
        self.name = "Settings"
        self.description = "Configure extensions and preferences"
        self.icon_path = None 
        self.widget_factory = None
        self.height = 64
        self.action = action
        # Duck-typing score for sorting
        self.score = 100 

# ... (GlobalShortcutFilter remains the same) ...
class GlobalShortcutFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def nativeEventFilter(self, eventType, message):
        if sys.platform == "win32":
            try:
                event_type_str = eventType if isinstance(eventType, str) else (eventType.decode('utf-8') if isinstance(eventType, bytes) else str(eventType))
            except:
                event_type_str = str(eventType)
            
            if "windows" in event_type_str.lower() or "win32" in event_type_str.lower():
                try:
                    msg_ptr = ctypes.cast(int(message), ctypes.POINTER(MSG))
                    msg = msg_ptr.contents
                    if msg.message == WM_HOTKEY:
                        self.callback()
                        return True, 0
                except:
                    pass
        return False, 0

class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        
        self.settings = SettingsManager()

        self.icon = create_app_icon()
        self.qapp.setWindowIcon(self.icon)
        self.active_extension = None
        self.window = LauncherWindow(self)
        self.window.center_on_screen = self.center_window
        
        self.pm = PluginManager(self)
        self.load_plugins()

        self.settings_window = SettingsWindow(self)

        self.hotkey_id = 1
        self.shortcut_filter = GlobalShortcutFilter(self.toggle_window)
        self.qapp.installNativeEventFilter(self.shortcut_filter)
        self.hwnd = int(self.window.winId())
        self.register_global_shortcut()

        self.watchdog = QTimer()
        self.watchdog.setInterval(200)
        self.watchdog.timeout.connect(self.check_os_focus)

        self.setup_tray()
        self.center_window()

    def load_plugins(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ext_path = os.path.join(base, "extensions")
        self.pm.load_extensions(ext_path)

    def register_global_shortcut(self):
        user32.UnregisterHotKey(self.hwnd, self.hotkey_id)
        user32.RegisterHotKey(self.hwnd, self.hotkey_id, MOD_ALT, VK_SPACE)

    def toggle_window(self):
        if self.window.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        self.center_window()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        force_focus(self.hwnd)
        self.window.search_input.setFocus()
        self.window.search_input.selectAll() 
        self.watchdog.start()

    def hide_window(self):
        self.watchdog.stop()
        self.window.hide()

    def check_os_focus(self):
        if not self.window.isVisible(): 
            self.watchdog.stop()
            return
        
        fg_hwnd = get_foreground_window()
        
        # Logic: If focus is lost AND the new focus is NOT the settings window
        # We want the launcher to stay open if the user clicks the Settings window?
        # Usually, if you click Settings, the Launcher should probably hide or stay.
        # But for now, let's keep the standard logic: close if not launcher.
        
        if fg_hwnd != self.hwnd:
            self.hide_window()

    def query(self, text):
        # 1. Scoped Mode
        if self.active_extension:
            ext = next((e for e in self.pm.extensions if e.id == self.active_extension), None)
            if ext:
                return ext.on_input(text) # Only query specific extension
            return []

        # 2. Root Mode
        # Query all plugins
        results = self.pm.query_all(text)
        
        # Inject "Open Extension" commands if text matches extension name
        for ext in self.pm.extensions:
            if ext.id.lower().startswith(text.lower()) or text.lower() in ext.id.lower():
                from api.types import ResultItem, Action
                item = ResultItem(
                    id=f"ext_open_{ext.id}",
                    name=ext.id.replace("_", " ").title(),
                    description="Open Extension",
                    score=200, # Show at top
                    action=Action(
                        name="Open",
                        handler=lambda e=ext: self.enter_extension_mode(e),
                        close_on_action=False
                    )
                )
                results.insert(0, item)
                
        return results

    def enter_extension_mode(self, extension):
        self.active_extension = extension.id
        
        # Check if extension has custom view
        custom_view = extension.get_extension_view(self.window)
        
        self.window.set_mode_extension(extension.id.replace("_", " ").title(), custom_view)

    def exit_extension_mode(self):
        self.active_extension = None
        self.window.set_mode_root()

    def center_window(self):
        screen = self.qapp.primaryScreen().geometry()
        x = (screen.width() - self.window.width()) // 2
        y = (screen.height() - self.window.height()) // 4
        self.window.move(x, y)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self.qapp)
        menu = QMenu()
        
        action_settings = QAction("Settings", self.qapp)
        action_settings.triggered.connect(self.show_settings)
        menu.addAction(action_settings)
        
        menu.addSeparator()
        
        menu.addAction(QAction("Show Launcher", self.qapp, triggered=self.show_window))
        menu.addAction(QAction("Quit", self.qapp, triggered=self.quit_app))
        self.tray.setContextMenu(menu)
        self.tray.show()

    def show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def quit_app(self):
        user32.UnregisterHotKey(self.hwnd, self.hotkey_id)
        self.qapp.quit()

    def run(self):
        sys.exit(self.qapp.exec())