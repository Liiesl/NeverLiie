# core/plugin_manager.py
import os
import importlib.util
import sys
from api.extension import Extension

class PluginManager:
    def __init__(self, core_app):
        self.extensions = []
        self.core = core_app

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
            
            # --- FIX: Track loaded classes to prevent duplicates ---
            loaded_classes = set()

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it is a class, inherits Extension, and isn't the base class itself
                if isinstance(attr, type) and issubclass(attr, Extension) and attr is not Extension:
                    
                    # Check if we already loaded this exact class from this module
                    if attr not in loaded_classes:
                        print(f"[Core] Loaded Extension: {name}")
                        instance = attr(self.core)
                        self.extensions.append(instance)
                        loaded_classes.add(attr) # Mark as loaded
                        
        except Exception as e:
            print(f"[Error] Failed to load {name}: {e}")

    def query_all(self, text):
        results = []
        for ext in self.extensions:
            try:
                items = ext.on_input(text)
                results.extend(items)
            except Exception as e:
                print(f"Error in extension: {e}")
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results