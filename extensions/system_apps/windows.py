import ctypes
import ctypes.wintypes
import sys
from typing import List, Optional
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
    def __init__(self):
        self.ignored_classes = {"Progman", "Button", "Shell_TrayWnd", "WorkerW"}

    def search(self, query: str) -> List[ResultItem]:
        if not query: return []
        
        query_lower = query.lower()
        results = []

        stats = {
            "scanned": 0,
            "visible": 0,
            "is_top_level": 0,
            "not_toolwindow": 0,
            "has_title": 0,
            "matches": 0
        }

        def enum_callback(hwnd, lParam):
            stats["scanned"] += 1
            
            # 1. Basic Visibility
            if not Win32.user32.IsWindowVisible(hwnd): 
                return True
            stats["visible"] += 1

            # 2. Owner Check (Top Level)
            # FIX: ctypes returns NULL handles as None, not 0.
            owner = Win32.user32.GetWindow(hwnd, Win32.GW_OWNER)
            if owner is not None: 
                return True
            stats["is_top_level"] += 1

            # 3. Style Check (Filter out tooltips/tray helpers)
            ex_style = Win32.user32.GetWindowLongW(hwnd, Win32.GWL_EXSTYLE)
            is_tool_window = ex_style & Win32.WS_EX_TOOLWINDOW
            is_app_window = ex_style & Win32.WS_EX_APPWINDOW
            if is_tool_window and not is_app_window:
                return True
            stats["not_toolwindow"] += 1

            # 4. Cloak check (UWP apps that are minimized/suspended)
            if Win32.is_window_cloaked(hwnd):
                return True

            # 5. Title Match
            title = Win32.get_window_text(hwnd)
            if not title:
                return True
            stats["has_title"] += 1

            if query_lower not in title.lower():
                return True
            stats["matches"] += 1

            # 6. Class Filter
            cls_name = Win32.get_window_class(hwnd)
            if cls_name in self.ignored_classes:
                return True

            # Passed all filters!
            exe_path = Win32.get_process_path(hwnd)
            
            # --- UPDATED SCORING LOGIC ---
            # We use a base score of 1000 to ensure windows 
            # always beat App Indexer results (which max out around 700)
            score = 1000 
            
            # Bonus if the title starts with the query
            if title.lower().startswith(query_lower): 
                score += 200
                
            # Extra bonus for exact matches
            if title.lower() == query_lower:
                score += 500
            
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
                score=score
            ))
            return True

        win_proc = Win32.WNDENUMPROC(enum_callback)
        Win32.user32.EnumWindows(win_proc, 0)
        
        return results

    def _switch_to_window(self, hwnd):
        try:
            # Check if minimized
            # Note: IsIconic is standard Win32 for 'is minimized'
            if Win32.user32.IsIconic(hwnd):
                Win32.user32.ShowWindow(hwnd, Win32.SW_RESTORE)
            else:
                Win32.user32.ShowWindow(hwnd, Win32.SW_SHOW)
            
            Win32.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"[WinWalker: Switch failed: {e}")