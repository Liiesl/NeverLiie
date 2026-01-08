# extensions/system_apps/__init__.py
import sys
from api.extension import Extension

try:
    from .apps import AppIndexer
    from .windows import WindowIndexer
except ImportError as e:
    print(f"[SystemApps] CRITICAL IMPORT ERROR: {e}", flush=True)

class SystemAppsExtension(Extension):
    def __init__(self, core_app):
        super().__init__(core_app)
        try:
            self.window_indexer = WindowIndexer()
            self.app_indexer = AppIndexer()
        except Exception as e:
            print(f"[SystemApps] Error creating indexers: {e}", flush=True)

    def on_input(self, text):
        query = text.strip()
        if not query: 
            return []

        results = []
        
        # 1. Window Search
        try:
            results += self.window_indexer.search(query)
        except Exception as e:
            print(f"[SystemApps] Window search error: {e}", flush=True)

        # 2. App Search 
        try:
            app_results = self.app_indexer.search(query)
            results += app_results
        except Exception as e:
            print(f"[SystemApps] App Search error: {e}", flush=True)
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:15]

Extension = SystemAppsExtension