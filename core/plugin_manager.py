# core/plugin_manager.py
import os
import importlib.util
import sys
import concurrent.futures
import time  # <--- Added time
from api.extension import Extension
from api.context import ExtensionContext

class PluginManager:
    def __init__(self, core_app):
        self.extensions = []
        self.core = core_app
        self.settings = core_app.settings
        
        # Thread pool
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="ExtWorker")

    def load_extensions(self, extensions_dir):
        if not os.path.exists(extensions_dir):
            os.makedirs(extensions_dir)
            
        for folder in os.listdir(extensions_dir):
            path = os.path.join(extensions_dir, folder)
            if os.path.isdir(path):
                init_file = os.path.join(path, "__init__.py")
                if os.path.exists(init_file):
                    self._load_module(folder, init_file)

    def _load_module(self, folder_name, path):
        try:
            spec = importlib.util.spec_from_file_location(f"ext_{folder_name}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"ext_{folder_name}"] = module
            spec.loader.exec_module(module)
            
            loaded_classes = set()

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if isinstance(attr, type) and issubclass(attr, Extension) and attr is not Extension:
                    if attr not in loaded_classes:
                        print(f"[Core] Loading Extension: {folder_name}")
                        context = ExtensionContext(self.core, ext_id=folder_name)
                        instance = attr(context)
                        self.extensions.append(instance)
                        loaded_classes.add(attr)
                        
        except Exception as e:
            print(f"[Error] Failed to load {folder_name}: {e}")

    def _safe_query(self, ext, text):
        """
        Runs inside the thread. 
        Measures execution time.
        """
        start_time = time.perf_counter()
        results = []
        
        try:
            results = ext.on_input(text)
        except Exception as e:
            print(f"[Error] Extension '{ext.id}' crashed: {e}")
            results = []
        finally:
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            
            # Print execution time for EVERY extension
            print(f"[{ext.id}] {elapsed_ms:.2f} ms")
            
            # Highlight extremely slow ones (e.g., > 500ms)
            if elapsed_ms > 500:
                print(f"⚠️ SLOW: {ext.id} took {elapsed_ms:.2f} ms")

        return results

    def query_all(self, text):
        results = []
        futures = {}

        # 1. Submit tasks
        for ext in self.extensions:
            if self.settings.is_extension_enabled(ext.id):
                future = self.executor.submit(self._safe_query, ext, text)
                futures[future] = ext.id

        # 2. Gather results with timeout
        try:
            for future in concurrent.futures.as_completed(futures, timeout=2.0):
                try:
                    items = future.result()
                    if items:
                        results.extend(items)
                except Exception as e:
                    print(f"[Core] Thread error: {e}")

        except concurrent.futures.TimeoutError:
            # 3. Identify who caused the timeout
            slow_plugins = []
            for f, ext_id in futures.items():
                if not f.done():
                    slow_plugins.append(ext_id)
            
            print(f"❌ TIMEOUT caused by: {', '.join(slow_plugins)}")

        results.sort(key=lambda x: x.score, reverse=True)
        return results
        
    def shutdown(self):
        self.executor.shutdown(wait=False)