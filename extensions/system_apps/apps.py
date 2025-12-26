import os
import json
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
                print(f"[System Apps] Loaded {len(self.alias_registry)} aliases.")
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

        # Add PATH
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
        
        print(f"[System Apps] Indexed {len(self.apps)} applications.")

    def search(self, query):
        if not query: return []
        results = []
        
        # Pre-calc aliases
        alias_targets = {}
        for alias_key, target_name in self.alias_registry.items():
            if alias_key.startswith(query):
                ratio = len(query) / len(alias_key)
                fuzzy_score = 110 + (ratio * 140)
                if target_name not in alias_targets or fuzzy_score > alias_targets[target_name]:
                    alias_targets[target_name] = fuzzy_score

        for app in self.apps:
            score = 0
            
            # Direct Match
            if query in app['lower_name']:
                score = 300 
                if app['lower_name'].startswith(query): score += 100
                if app['lower_name'] == query: score += 300
                if app['is_shortcut']: score += 50
            
            # Alias Match
            if score < 300:
                for target_part, alias_score in alias_targets.items():
                    if target_part in app['lower_name']:
                        if alias_score > score:
                            score = alias_score

            if score > 0:
                item = ResultItem(
                    id=app['path'],
                    name=app['name'],
                    description=app['path'],
                    icon_path=app['path'], 
                    action=Action(
                        name="Launch",
                        handler=lambda p=app['path']: self._launch(p),
                        close_on_action=True
                    ),
                    score=int(score)
                )
                results.append(item)
                
        return results

    def _launch(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            print(f"[Error] Launch failed: {e}")