# extensions/system_apps/apps.py
import os
import json
import subprocess
import ctypes
from api.types import ResultItem, Action
from .lnk_parser import resolve_lnk

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
        target_map = {}  # exe_path.lower() -> app_data
        
        search_dirs = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs"),
        ]

        path_env = os.environ.get("PATH", "")
        for p in path_env.split(os.pathsep):
            if p and os.path.exists(p):
                search_dirs.append(p)

        valid_extensions = {".exe", ".lnk"}
        ignore_names = {"uninstall", "readme", "help", "website", "update", "installer", "setup"}

        for directory in search_dirs:
            if not directory or not os.path.exists(directory):
                continue
            
            try:
                is_start_menu = "Start Menu" in directory
                
                if is_start_menu:
                    walker = os.walk(directory)
                else:
                    try:
                        files = os.listdir(directory)
                        walker = [(directory, [], files)]
                    except PermissionError:
                        continue

                for root, _, files in walker:
                    for filename in files:
                        try:
                            name, ext = os.path.splitext(filename)
                            ext = ext.lower()
                            if ext not in valid_extensions:
                                continue
                            
                            lower_name = name.lower()
                            if any(bad in lower_name for bad in ignore_names):
                                continue
                            
                            full_path = os.path.normpath(os.path.join(root, filename))
                            clean_name = name.replace(" - Shortcut", "")
                            
                            # Resolve target for deduplication
                            if ext == ".lnk":
                                resolved = resolve_lnk(full_path)
                                target_path = resolved if resolved else full_path
                            else:
                                target_path = full_path
                            
                            target_key = target_path.lower()
                            
                            existing = target_map.get(target_key)
                            
                            # Prefer shortcuts (better display names)
                            should_add = (
                                existing is None or
                                (ext == ".lnk" and not existing["is_shortcut"])
                            )
                            
                            if should_add:
                                target_map[target_key] = {
                                    "name": clean_name,
                                    "path": full_path,      # Launch path (.lnk or .exe)
                                    "target": target_path,  # Actual .exe for icon/alias matching
                                    "lower_name": clean_name.lower(),
                                    "is_shortcut": ext == ".lnk"
                                }
                        except Exception:
                            continue
                            
            except Exception as e:
                print(f"[System Apps] Error scanning {directory}: {e}")
                continue

        self.apps = list(target_map.values())
        print(f"[System Apps] Indexed {len(self.apps)} applications")

    def search(self, query):
        if not query:
            return []
        
        results = []
        query_lower = query.lower()
        
        # Alias scoring
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
            
            # Match by name
            if query_lower in app['lower_name']:
                score = 300
                if app['lower_name'].startswith(query_lower):
                    score += 100
                if app['lower_name'] == query_lower:
                    score += 300
                if app['is_shortcut']:
                    score += 50
            
            # Match by alias (check both name and target exe)
            target_lower = app.get('target', '').lower()
            for target_part, alias_score in alias_targets.items():
                if target_part in app['lower_name'] or target_part in target_lower:
                    if alias_score > score:
                        score = alias_score
            
            if score > 0:
                launch_action = Action("Open Application", lambda p=app['path']: self._launch(p))
                
                results.append(ResultItem(
                    id=app.get('target', app['path']),
                    name=app['name'],
                    description=app.get('target', app['path']),
                    icon_path=app.get('target', app['path']),
                    action=launch_action,
                    context_actions=[
                        launch_action,
                        Action("Run as Administrator", lambda p=app['path']: self._launch_as_admin(p)),
                        Action("Open File Location", lambda p=app['path']: self._show_in_explorer(p))
                    ],
                    score=int(score)
                ))
                
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _launch(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            print(f"[Error] Launch failed: {e}")

    def _launch_as_admin(self, path):
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
        except Exception as e:
            print(f"[Error] Launch as admin failed: {e}")

    def _show_in_explorer(self, path):
        try:
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])
        except Exception as e:
            print(f"[Error] Show in explorer failed: {e}")