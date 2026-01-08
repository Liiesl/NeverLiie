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
from .extension_manager import ExtensionManager
from .win32_utils import (
    WM_HOTKEY, MOD_ALT, VK_SPACE, MSG, 
    force_focus, get_foreground_window, user32
)

# --- HELPER CLASSES (Global) ---
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

class GlobalShortcutFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def nativeEventFilter(self, eventType, message):
        if sys.platform == "win32":
            try:
                event_type_str = eventType if isinstance(eventType, str) else str(eventType)
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
        
        self.pm = ExtensionManager(self)
        self.load_extensions()
        
        self.active_extension = None
        self.window = LauncherWindow(self)
        self.window.center_on_screen = self.center_window
        
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

    def load_extensions(self):
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
        self.window.search_bar.search_input.setFocus()
        self.window.search_bar.search_input.selectAll() 
        self.watchdog.start()

    def hide_window(self):
        self.watchdog.stop()
        self.window.hide()

    def check_os_focus(self):
        if not self.window.isVisible(): 
            self.watchdog.stop()
            return
        fg_hwnd = get_foreground_window()
        if fg_hwnd != self.hwnd:
            self.hide_window()

    def handle_reload(self, ext_id):
        """Wrapper to reload extension and give UI feedback"""
        success = self.pm.reload_extension(ext_id)
        if success:
            self.window.footer.set_text(f"Extension '{ext_id}' reloaded successfully.")
        else:
            self.window.footer.set_text(f"Failed to reload extension '{ext_id}'. Check console.")

    def query(self, text, callback):
        """
        Initiates an async query.
        callback: function(results: list, query_id: int)
        """
        # 1. Scoped Mode
        if self.active_extension:
            ext = next((e for e in self.pm.extensions if e.id == self.active_extension), None)
            if ext:
                results = ext.on_input(text)
                callback(results, -1) 
            return

        # 2. Root Mode - Calculate Static Results
        static_results = []
        for ext in self.pm.extensions:
            if ext.id.lower().startswith(text.lower()) or text.lower() in ext.id.lower():
                from api.types import ResultItem, Action
                
                ctx_actions = [
                    Action(
                        name="Open",
                        handler=lambda e=ext: self.enter_extension_mode(e),
                        close_on_action=False
                    ),
                    Action(
                        name=f"Reload {ext.id}",
                        handler=lambda e_id=ext.id: self.handle_reload(e_id),
                        close_on_action=False
                    )
                ]

                item = ResultItem(
                    id=f"ext_open_{ext.id}",
                    name=ext.id.replace("_", " ").title(),
                    description="Open Extension",
                    score=2000, 
                    action=Action(
                        name="Open",
                        handler=lambda e=ext: self.enter_extension_mode(e),
                        close_on_action=False
                    ),
                    context_actions=ctx_actions
                )
                static_results.append(item)
        
        # --- CHANGE START ---
        # REMOVED: immediate callback(static_results, -1). 
        # This prevents the UI from resizing to a small list and then immediately 
        # expanding to a large list (the "collapse/reopen" effect).
        # --- CHANGE END ---

        # 3. Call Async Manager
        def result_wrapper(async_results, qid):
            combined = static_results + async_results
            combined.sort(key=lambda x: x.score, reverse=True)
            callback(combined, qid)

        self.pm.search_async(text, result_wrapper)

    def enter_extension_mode(self, extension):
        # Always fetch the latest instance from ExtensionManager in case it was reloaded
        current_ext = next((e for e in self.pm.extensions if e.id == extension.id), None)
        if not current_ext:
            print(f"Error: Extension {extension.id} not found (maybe failed reload?)")
            return

        self.active_extension = current_ext.id
        custom_view = current_ext.get_extension_view(self.window)
        self.window.set_mode_extension(current_ext.id.replace("_", " ").title(), custom_view)

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
        self.pm.shutdown()
        self.qapp.quit()

    def run(self):
        sys.exit(self.qapp.exec())