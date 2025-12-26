# core/app.py
import sys
import os
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal, QTimer, QAbstractNativeEventFilter

from .ui import LauncherWindow, create_app_icon
from .plugin_manager import PluginManager
from .win32_utils import (
    WM_HOTKEY, MOD_ALT, VK_SPACE, MSG, 
    force_focus, get_foreground_window, user32
)

# --- NATIVE EVENT FILTER (From Reference App) ---
class GlobalShortcutFilter(QAbstractNativeEventFilter):
    """Native event filter to catch global hotkey messages"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def nativeEventFilter(self, eventType, message):
        """Filter native events for hotkey messages"""
        if sys.platform == "win32":
            # Handle PySide6 version differences (bytes vs str)
            try:
                event_type_str = eventType if isinstance(eventType, str) else (eventType.decode('utf-8') if isinstance(eventType, bytes) else str(eventType))
            except:
                event_type_str = str(eventType)
            
            if "windows" in event_type_str.lower() or "win32" in event_type_str.lower():
                try:
                    # Convert VoidPtr to integer, then to ctypes pointer
                    msg_ptr = ctypes.cast(int(message), ctypes.POINTER(MSG))
                    msg = msg_ptr.contents
                    if msg.message == WM_HOTKEY:
                        self.callback()
                        return True, 0
                except (ValueError, TypeError, AttributeError, OverflowError):
                    pass
        return False, 0

class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        
        # 1. Setup UI
        self.icon = create_app_icon()
        self.qapp.setWindowIcon(self.icon)
        self.window = LauncherWindow(self)
        self.window.center_on_screen = self.center_window
        
        # 2. Setup Plugins
        self.pm = PluginManager(self)
        self.load_plugins()

        # 3. Setup Native Hotkey (Alt + Space)
        self.hotkey_id = 1
        self.shortcut_filter = GlobalShortcutFilter(self.toggle_window)
        self.qapp.installNativeEventFilter(self.shortcut_filter)
        
        # We need the HWND to register the hotkey. 
        # Calling winId() creates the handle if it doesn't exist.
        self.hwnd = int(self.window.winId())
        self.register_global_shortcut()

        # 4. Setup Watchdog (Focus Loss Detector)
        self.watchdog = QTimer()
        self.watchdog.setInterval(200) # Checked every 200ms
        self.watchdog.timeout.connect(self.check_os_focus)

        # 5. Setup Tray
        self.setup_tray()
        
        # Initial Center
        self.center_window()

    def load_plugins(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ext_path = os.path.join(base, "extensions")
        self.pm.load_extensions(ext_path)

    def register_global_shortcut(self):
        """Registers Alt+Space (MOD_ALT + VK_SPACE)"""
        # Unregister first just in case
        user32.UnregisterHotKey(self.hwnd, self.hotkey_id)
        
        # RegisterHotKey(hwnd, id, modifiers, vk)
        success = user32.RegisterHotKey(self.hwnd, self.hotkey_id, MOD_ALT, VK_SPACE)
        if not success:
            print("[Error] Failed to register Alt+Space hotkey. It might be in use.")
        else:
            print("[Core] Native Hotkey 'Alt+Space' registered.")

    def toggle_window(self):
        if self.window.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        # 1. Position the window
        self.center_window()

        # 2. Qt Methods to Show
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        
        # 3. Force Focus (Win32 fallback)
        force_focus(self.hwnd)
        
        # 4. Input Focus & Selection Logic
        # We DO NOT clear the text or the list. 
        # Instead, we focus the input and select all text.
        self.window.search_input.setFocus()
        self.window.search_input.selectAll() 
        
        # 5. Start Watchdog
        self.watchdog.start()

    def hide_window(self):
        self.watchdog.stop()
        self.window.hide()

    def check_os_focus(self):
        """
        If the user clicks away or presses Alt+Tab, this hides the window.
        """
        if not self.window.isVisible(): 
            self.watchdog.stop()
            return
        
        fg_hwnd = get_foreground_window()
        if fg_hwnd != self.hwnd:
            # print(f"[Debug] Focus lost to {fg_hwnd}, hiding.")
            self.hide_window()

    def query(self, text):
        return self.pm.query_all(text)

    def center_window(self):
        screen = self.qapp.primaryScreen().geometry()
        x = (screen.width() - self.window.width()) // 2
        y = (screen.height() - self.window.height()) // 4
        self.window.move(x, y)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self.qapp)
        menu = QMenu()
        menu.addAction(QAction("Show", self.qapp, triggered=self.show_window))
        menu.addAction(QAction("Quit", self.qapp, triggered=self.quit_app))
        self.tray.setContextMenu(menu)
        self.tray.show()

    def quit_app(self):
        user32.UnregisterHotKey(self.hwnd, self.hotkey_id)
        self.qapp.quit()

    def run(self):
        sys.exit(self.qapp.exec())