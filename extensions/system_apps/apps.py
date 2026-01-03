# extensions/system_apps/apps.py
import os
import json
import subprocess
import ctypes
from api.types import ResultItem, Action

class AppIndexer:
    def __init__(self):
        self.apps = []
        self.alias_registry = {}
        self.load_aliases()
        self.refresh_index()

    def load_aliases(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "aliases.json")
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                for category in data.values():
                    if isinstance(category, dict):
                        for alias, target in category.items():
                            self.alias_registry[alias.lower()] = target.lower()
        except Exception as e:
            print(f"[System Apps] Error loading aliases: {e}")

    def refresh_index(self):
        found_paths = set()
        self.apps = []
        
        search_dirs = [
            os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ["PROGRAMDATA"], r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ["LOCALAPPDATA"], r"Programs"),
        ]

        path_env = os.environ.get("PATH", "")
        for p in path_env.split(os.pathsep):
            if p and os.path.exists(p):
                search_dirs.append(p)

        valid_extensions = {".exe", ".lnk", ".bat", ".cmd"}
        ignore_names = {"uninstall", "readme", "help", "website", "update", "installer", "configuration", "setup"}

        for directory in search_dirs:
            if not os.path.exists(directory): continue
            
            should_recurse = "Start Menu" in directory or "Programs" in directory
            walker = os.walk(directory) if should_recurse else [(directory, [], os.listdir(directory))]

            for root, _, files in walker:
                for filename in files:
                    name, ext = os.path.splitext(filename)
                    lower_name = name.lower()

                    if ext.lower() not in valid_extensions: continue
                    if any(bad in lower_name for bad in ignore_names): continue
                    
                    clean_name = name.replace(" - Shortcut", "")
                    full_path = os.path.join(root, filename)

                    if full_path not in found_paths:
                        self.apps.append({
                            "name": clean_name,
                            "path": full_path,
                            "lower_name": clean_name.lower(),
                            "is_shortcut": ext.lower() == ".lnk"
                        })
                        found_paths.add(full_path)

    def search(self, query):
        if not query: return []
        results = []
        query_lower = query.lower()
        
        alias_targets = {}
        for alias_key, target_name in self.alias_registry.items():
            ratio = len(query) / len(alias_key)
            if alias_key.startswith(query_lower):
                fuzzy_score = 250 + (ratio * 150)
            elif query_lower in alias_key:
                fuzzy_score = 200 + (ratio * 100)
            else:
                continue
                
            if target_name not in alias_targets or fuzzy_score > alias_targets[target_name]:
                alias_targets[target_name] = fuzzy_score

        for app in self.apps:
            score = 0
            if query_lower in app['lower_name']:
                score = 300 
                if app['lower_name'].startswith(query_lower): score += 100
                if app['lower_name'] == query_lower: score += 300
                if app['is_shortcut']: score += 50
            
            if score < 300:
                for target_part, alias_score in alias_targets.items():
                    if target_part in app['lower_name']:
                        if alias_score > score:
                            score = alias_score
            
            if query_lower == app['lower_name']:
                score += 200
            
            for alias_key, target_name in self.alias_registry.items():
                if alias_key == query_lower and target_name in app['lower_name']:
                    score += 150

            if score > 0:
                launch_action = Action("Open Application", lambda p=app['path']: self._launch(p))
                
                context_actions = [
                    launch_action,
                    Action("Run as Administrator", lambda p=app['path']: self._launch_as_admin(p)),
                    Action("Show in Explorer", lambda p=app['path']: self._show_in_explorer(p))
                ]

                item = ResultItem(
                    id=app['path'],
                    name=app['name'],
                    description=app['path'],
                    icon_path=app['path'], 
                    action=launch_action,
                    context_actions=context_actions,
                    score=int(score)
                )
                results.append(item)
                
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _launch(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            print(f"[Error] Launch failed: {e}")

    def _launch_as_admin(self, path):
        try:
            # ShellExecuteW allows passing the "runas" verb which triggers the UAC prompt
            # parameters: hwnd, verb, file, parameters, directory, show_cmd (1=SW_NORMAL)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
        except Exception as e:
            print(f"[Error] Launch as admin failed: {e}")

    def _show_in_explorer(self, path):
        try:
            # Windows command to open explorer with file selected
            subprocess.run(['explorer', '/select,', path])
        except Exception as e:
            print(f"[Error] Show in explorer failed: {e}")