# extensions/file_search/__init__.py
import os
import sys
import ctypes
from api.extension import Extension
from api.types import ResultItem, Action

class EverythingPlugin(Extension):
    def __init__(self, api):
        super().__init__(api)
        self.setup_dll()

    def setup_dll(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dll_name = "Everything64.dll" if sys.maxsize > 2**32 else "Everything32.dll"
        dll_path = os.path.join(script_dir, dll_name)
        
        self.available = False
        if os.path.exists(dll_path):
            try:
                self.dll = ctypes.WinDLL(dll_path)
                # Define argtypes/restypes here
                self.dll.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
                self.dll.Everything_GetResultFileNameW.restype = ctypes.c_wchar_p
                self.dll.Everything_GetResultPathW.restype = ctypes.c_wchar_p
                self.dll.Everything_GetNumResults.restype = ctypes.c_int
                self.dll.Everything_SetRequestFlags(0x00000001 | 0x00000002)
                self.available = True
            except Exception as e:
                print(f"DLL Error: {e}")

    def on_input(self, text):
        if not self.available or not text: return []
        
        self.dll.Everything_SetSearchW(text)
        self.dll.Everything_QueryW(True)
        
        results = []
        num_results = self.dll.Everything_GetNumResults()
        
        for i in range(min(num_results, 20)):
            name = self.dll.Everything_GetResultFileNameW(i)
            folder = self.dll.Everything_GetResultPathW(i)
            full_path = os.path.join(folder, name)
            
            # Create Action
            action = Action(
                name="Open",
                handler=lambda p=full_path: os.startfile(p),
                close_on_action=True
            )
            
            results.append(ResultItem(
                id=full_path,
                name=name,
                description=folder,
                icon_path=full_path, # <--- Added this to trigger UI icon generation
                action=action,
                score=100
            ))
            
        return results

# Export the class as 'Plugin' for the manager to find
Plugin = EverythingPlugin