import ctypes
import ctypes.wintypes
import sys
import os
from typing import List, Optional, Dict
from api.types import ResultItem, Action

class Win32:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    dwmapi = ctypes.windll.dwmapi

    HWND = ctypes.wintypes.HWND
    DWORD = ctypes.wintypes.DWORD
    BOOL = ctypes.wintypes.BOOL
    UINT = ctypes.wintypes.UINT
    LPARAM = ctypes.wintypes.LPARAM
    HANDLE = ctypes.wintypes.HANDLE
    LPWSTR = ctypes.wintypes.LPWSTR
    
    GW_OWNER = 4
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    SW_RESTORE = 9
    SW_SHOW = 5
    DWMWA_CLOAKED = 14
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000 
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

    # Function Signatures
    user32.EnumWindows.argtypes = [WNDENUMPROC, LPARAM]
    user32.EnumWindows.restype = BOOL
    
    user32.GetWindowTextLengthW.argtypes = [HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    
    user32.GetWindowTextW.argtypes = [HWND, LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    
    user32.GetClassNameW.argtypes = [HWND, LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int

    user32.IsWindowVisible.argtypes = [HWND]
    user32.IsWindowVisible.restype = BOOL
    
    user32.GetWindow.argtypes = [HWND, UINT]
    user32.GetWindow.restype = HWND
    
    user32.GetWindowLongW.argtypes = [HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long

    user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
    user32.GetWindowThreadProcessId.restype = DWORD
    
    kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
    kernel32.OpenProcess.restype = HANDLE
    
    kernel32.QueryFullProcessImageNameW.argtypes = [HANDLE, DWORD, LPWSTR, ctypes.POINTER(DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = BOOL
    
    dwmapi.DwmGetWindowAttribute.argtypes = [HWND, DWORD, ctypes.c_void_p, DWORD]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_int

    # ADD these missing signatures:
    kernel32.CloseHandle.argtypes = [HANDLE]
    kernel32.CloseHandle.restype = BOOL
    
    user32.IsIconic.argtypes = [HWND]
    user32.IsIconic.restype = BOOL
    
    user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
    user32.ShowWindow.restype = BOOL
    
    user32.SetForegroundWindow.argtypes = [HWND]
    user32.SetForegroundWindow.restype = BOOL

    @staticmethod
    def get_window_text(hwnd: HWND) -> str:
        length = Win32.user32.GetWindowTextLengthW(hwnd)
        if length == 0: return ""
        buff = ctypes.create_unicode_buffer(length + 1)
        Win32.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value

    @staticmethod
    def is_window_cloaked(hwnd: HWND) -> bool:
        try:
            is_cloaked = ctypes.c_int(0)
            hr = Win32.dwmapi.DwmGetWindowAttribute(
                hwnd, Win32.DWMWA_CLOAKED, ctypes.byref(is_cloaked), ctypes.sizeof(is_cloaked)
            )
            return hr == 0 and is_cloaked.value != 0
        except:
            return False

    @staticmethod
    def get_process_path(hwnd: HWND) -> Optional[str]:
        pid = Win32.DWORD()
        Win32.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h_process = Win32.kernel32.OpenProcess(Win32.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_process:
            try:
                buff_size = Win32.DWORD(1024)
                path_buff = ctypes.create_unicode_buffer(1024)
                if Win32.kernel32.QueryFullProcessImageNameW(h_process, 0, path_buff, ctypes.byref(buff_size)):
                    return path_buff.value
            finally:
                Win32.kernel32.CloseHandle(h_process)
        return None

    @staticmethod
    def get_window_class(hwnd: HWND) -> str:
        buff = ctypes.create_unicode_buffer(256)
        Win32.user32.GetClassNameW(hwnd, buff, 256)
        return buff.value

class WindowIndexer:
    def __init__(self, alias_registry: Dict[str, str] = None):
        self.ignored_classes = {"Progman", "Button", "Shell_TrayWnd", "WorkerW"}
        self.alias_registry = alias_registry or {}

    def search(self, query: str) -> List[ResultItem]:
        if not query: return []
        
        query_lower = query.lower()
        results = []

        # --- ALIAS CALCULATION START ---
        # Mirrors logic in apps.py to find what the user might be referring to
        alias_targets = {}
        for alias_key, target_name in self.alias_registry.items():
            ratio = len(query) / len(alias_key)
            fuzzy_score = 0
            
            if alias_key.startswith(query_lower):
                fuzzy_score = 250 + (ratio * 150)
            elif query_lower in alias_key:
                fuzzy_score = 200 + (ratio * 100)
            else:
                continue
                
            if target_name not in alias_targets or fuzzy_score > alias_targets[target_name]:
                alias_targets[target_name] = fuzzy_score
        # --- ALIAS CALCULATION END ---

        def enum_callback(hwnd, lParam):
            # 1. Basic Visibility
            if not Win32.user32.IsWindowVisible(hwnd): 
                return True

            # 2. Owner Check (Top Level)
            owner = Win32.user32.GetWindow(hwnd, Win32.GW_OWNER)
            if owner is not None: 
                return True

            # 3. Style Check
            ex_style = Win32.user32.GetWindowLongW(hwnd, Win32.GWL_EXSTYLE)
            is_tool_window = ex_style & Win32.WS_EX_TOOLWINDOW
            is_app_window = ex_style & Win32.WS_EX_APPWINDOW
            if is_tool_window and not is_app_window:
                return True

            # 4. Cloak check
            if Win32.is_window_cloaked(hwnd):
                return True

            # 5. Get Title and Path
            title = Win32.get_window_text(hwnd)
            if not title: return True
            title_lower = title.lower()

            exe_path = Win32.get_process_path(hwnd)
            exe_name_lower = ""
            if exe_path:
                # Extracts "code" from "C:\...\Code.exe"
                exe_name_lower = os.path.splitext(os.path.basename(exe_path))[0].lower()

            # --- MATCHING LOGIC ---
            
            is_match = False
            base_score = 1000 # Windows generally beat Apps (which cap around 700)
            boost_score = 0

            # A. Direct Title Match
            if query_lower in title_lower:
                is_match = True
                if title_lower.startswith(query_lower): boost_score += 200
                if title_lower == query_lower: boost_score += 500

            # B. Alias / Executable Match
            # We check if an alias target (e.g. "Visual Studio Code" or "winword") 
            # appears in the Window Title OR matches the Executable Name.
            for target_part, alias_score in alias_targets.items():
                target_part = target_part.lower()
                
                # Check 1: Target is in the window title?
                # e.g. target "code" in title "Project - Visual Studio Code" -> Hit
                if target_part in title_lower:
                    is_match = True
                    if alias_score > boost_score:
                        boost_score = alias_score

                # Check 2: Target is in the executable name?
                # e.g. target "winword" matches exe "winword" -> Hit
                if exe_name_lower and target_part in exe_name_lower:
                    is_match = True
                    # If we matched the binary name via alias, that's a strong signal
                    if alias_score > boost_score:
                        boost_score = alias_score + 100

            if not is_match:
                return True

            # 6. Class Filter
            cls_name = Win32.get_window_class(hwnd)
            if cls_name in self.ignored_classes:
                return True

            # Calculate Final Score
            final_score = base_score + boost_score
            
            # Extra boost for exact alias match
            for alias_key in self.alias_registry.keys():
                if alias_key == query_lower:
                    # If user typed exactly the alias, and we found a match, boost heavily
                    final_score += 150
                    break

            results.append(ResultItem(
                id=f"win_{hwnd}",
                name=title,
                description=f"Switch to {cls_name}",
                icon_path=exe_path,
                action=Action(
                    name="Switch To",
                    handler=lambda h=hwnd: self._switch_to_window(h),
                    close_on_action=True
                ),
                score=int(final_score)
            ))
            return True

        win_proc = Win32.WNDENUMPROC(enum_callback)
        Win32.user32.EnumWindows(win_proc, 0)
        
        return results

    def _switch_to_window(self, hwnd):
        try:
            if Win32.user32.IsIconic(hwnd):
                Win32.user32.ShowWindow(hwnd, Win32.SW_RESTORE)
            else:
                Win32.user32.ShowWindow(hwnd, Win32.SW_SHOW)
            
            Win32.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"[WinWalker: Switch failed: {e}")