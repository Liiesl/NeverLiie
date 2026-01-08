# extensions/file_search/__init__.py
import os
import sys
import ctypes
import re
from api.extension import Extension
from api.types import ResultItem, Action

def parse_gitignore_patterns(gitignore_path):
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    except:
        pass
    return patterns

def path_matches_pattern(path, patterns, base_path):
    for pattern in patterns:
        if pattern.startswith('!'):
            continue
        pattern = pattern.rstrip('/')
        regex_pattern = pattern
        if pattern.startswith('/'):
            regex_pattern = '^' + pattern[1:]
        elif pattern.endswith('/'):
            regex_pattern = '.*/' + pattern.rstrip('/') + '$'
        else:
            regex_pattern = '.*/' + pattern + '$'
        regex_pattern = regex_pattern.replace('.', '\\.').replace('*', '.*').replace('?', '.')
        if re.match(regex_pattern, path):
            return True
    return False

class EverythingExtension(Extension):
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

        search_text = text
        # Convert / to \ for Everything SDK compatibility
        search_text = search_text.replace('/', '\\')

        self.dll.Everything_SetSearchW(search_text)
        self.dll.Everything_QueryW(True)

        results = []
        num_results = self.dll.Everything_GetNumResults()

        # Directories to filter unless explicitly searched
        filter_dirs = ['.git', 'node_modules', 'venv', '__pycache__', '.venv', 'dist', 'build', '.next', 'out']
        is_explicit_filter_search = any(d in search_text.lower() for d in filter_dirs)

        for i in range(min(num_results, 20)):
            name = self.dll.Everything_GetResultFileNameW(i)
            folder = self.dll.Everything_GetResultPathW(i)
            full_path = os.path.join(folder, name)

            # Filter directories unless explicitly searched
            if not is_explicit_filter_search:
                normalized_full = full_path.replace('\\', '/').lower()
                skip = False
                for d in filter_dirs:
                    if f'/{d}/' in normalized_full or normalized_full.endswith(f'/{d}'):
                        skip = True
                        break
                if skip:
                    continue

                # Check .gitignore
                normalized_path = full_path.replace('\\', '/')
                gitignore_path = os.path.join(folder, '.gitignore') if not name else os.path.join(folder, '.gitignore')
                if os.path.exists(gitignore_path):
                    rel_path = os.path.relpath(normalized_path, folder).replace('\\', '/')
                    gitignore_patterns = parse_gitignore_patterns(gitignore_path)
                    if path_matches_pattern(rel_path, gitignore_patterns, folder):
                        continue

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
                icon_path=full_path,
                action=action,
                score=100
            ))

        return results

# Export the class as 'Extension' for the manager to find
Extension = EverythingExtension