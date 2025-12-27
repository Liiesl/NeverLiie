# core/plugin_manager.py
import os
import importlib.util
import sys
from api.extension import Extension

class PluginManager:
    def __init__(self, core_app):
        self.extensions = []
        self.core = core_app
        # Shortcut to settings
        self.settings = core_app.settings

    def load_extensions(self, extensions_dir):
        if not os.path.exists(extensions_dir):
            os.makedirs(extensions_dir)
            
        for folder in os.listdir(extensions_dir):
            path = os.path.join(extensions_dir, folder)
            if os.path.isdir(path):
                init_file = os.path.join(path, "__init__.py")
                if os.path.exists(init_file):
                    self._load_module(folder, init_file)

    def _load_module(self, name, path):
        try:
            spec = importlib.util.spec_from_file_location(f"ext_{name}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"ext_{name}"] = module
            spec.loader.exec_module(module)
            
            loaded_classes = set()

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if isinstance(attr, type) and issubclass(attr, Extension) and attr is not Extension:
                    if attr not in loaded_classes:
                        print(f"[Core] Loaded Extension: {name}")
                        instance = attr(self.core)
                        
                        # ASSIGN ID: Use the folder name as the unique ID
                        instance.id = name 
                        
                        self.extensions.append(instance)
                        loaded_classes.add(attr)
                        
        except Exception as e:
            print(f"[Error] Failed to load {name}: {e}")

    def query_all(self, text):
        results = []
        for ext in self.extensions:
            # CHECK SETTINGS: Only query if enabled
            if self.settings.is_extension_enabled(ext.id):
                try:
                    items = ext.on_input(text)
                    results.extend(items)
                except Exception as e:
                    print(f"Error in extension {ext.id}: {e}")
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results