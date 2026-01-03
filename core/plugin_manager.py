# core/plugin_manager.py
import os
import importlib.util
import sys
import concurrent.futures
import time
import threading
from api.extension import Extension
from api.context import ExtensionContext

class PluginManager:
    def __init__(self, core_app):
        self.extensions = []
        self.core = core_app
        self.settings = core_app.settings
        
        # Thread pool
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="ExtWorker")
        
        # Async state management
        self._query_id = 0
        self._search_lock = threading.Lock()
        self._active_futures = []

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
        """
        start_time = time.perf_counter()
        results = []
        try:
            results = ext.on_input(text) or [] # Ensure list
        except Exception as e:
            print(f"[Error] Extension '{ext.id}' crashed: {e}")
            results = []
        finally:
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000
            # Optional: Log slow plugins
            if elapsed_ms > 200:
                print(f"[{ext.id}] Slow: {elapsed_ms:.2f} ms")

        return results

    def cancel_previous_queries(self):
        """
        Increment the query ID. Any thread running a task for an 
        older ID will effectively have its results ignored.
        """
        with self._search_lock:
            self._query_id += 1
            # We can't easily kill running threads in Python, 
            # but we can ignore their output.
            
    def search_async(self, text, callback_fn):
        """
        text: The search string
        callback_fn: function(results: list, query_id: int)
        """
        
        # 1. Invalidate previous searches
        self.cancel_previous_queries()
        
        current_qid = self._query_id
        
        # 2. Prepare result bucket
        current_results = []
        
        # 3. Define the completion handler (runs on worker thread)
        def on_task_done(future):
            # If query ID has changed, user typed something new. Abort.
            if self._query_id != current_qid:
                return

            try:
                new_items = future.result()
                if not new_items: 
                    return
                
                # Critical Section: Update the master list
                with self._search_lock:
                    # Double check ID inside lock just to be safe
                    if self._query_id != current_qid:
                        return
                        
                    current_results.extend(new_items)
                    # Sort immediately so the UI gets a ranked list
                    current_results.sort(key=lambda x: x.score, reverse=True)
                    
                    # Create a copy to pass to UI (prevent modification issues)
                    results_snapshot = list(current_results)
                
                # Send back to UI
                callback_fn(results_snapshot, current_qid)
                
            except Exception as e:
                print(f"Task error: {e}")

        # 4. Submit tasks
        for ext in self.extensions:
            if self.settings.is_extension_enabled(ext.id):
                future = self.executor.submit(self._safe_query, ext, text)
                future.add_done_callback(on_task_done)

    def shutdown(self):
        self.executor.shutdown(wait=False)