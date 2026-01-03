# extensions/clipboard/__init__.py
import time
import os
from api.extension import Extension
from api.types import ResultItem, Action
from .monitor import ClipboardMonitor
from .input_sim import send_ctrl_v

# Global instance
_monitor = None
from .ui import ClipboardView

class ClipboardExtension(Extension):
    def __init__(self, context):
        super().__init__(context)
        global _monitor
        
        # --- START CHANGE: Use centralized path ---
        if _monitor is None:
            # context.data_path is now injected by PluginManager
            # e.g., C:\Users\User\AppData\Roaming\PyLauncher\extensions\clipboard
            
            db_path = os.path.join(self.context.data_path, 'clipboard.db')
            media_path = os.path.join(self.context.data_path, 'media')
            
            print(f"[Clipboard] Storing data in: {self.context.data_path}")
            _monitor = ClipboardMonitor(db_path=db_path, media_dir=media_path)
        # --- END CHANGE ---
            
        self.monitor = _monitor

    def on_input(self, text):
        query = text.strip().lower()
        
        # Keyword trigger: "cb" or "clip"
        is_keyword = query in ["cb", "clip"]
        
        # If not keyword and not searching specifically, return nothing
        # (Unless you want clipboard history to appear in global search always)
        if not is_keyword and not query.startswith("cb "):
            return []

        items = []
        # Pass query to monitor if you want DB level filtering
        search_term = query[3:].strip() if query.startswith("cb ") else ""
        history = self.monitor.get_history(search_term)
        
        for idx, row in enumerate(history):
            content = row.get('content_text') or ""
            
            # Simple fallback filtering if DB didn't do it
            if search_term and search_term not in content.lower():
                continue

            # Format the display (truncate long text)
            display_text = " ".join(content.split()) # Remove newlines for title
            if len(display_text) > 60:
                display_text = display_text[:60] + "..."

            # Determine description based on type
            item_type = row.get('type', 'text')
            if item_type == 'image':
                desc = "Image Capture"
            elif item_type == 'files':
                desc = "File Reference"
            else:
                desc = f"Chars: {len(content)}"

            items.append(ResultItem(
                id=f"clip_{idx}",
                name=display_text,
                description=f"{desc} | Copy to paste",
                icon_path=None, # You could add a 'copy.png' here
                score=100 if is_keyword else 50, # High score if typed 'cb'
                action=Action(
                    name="Paste",
                    # Capture 'row' in the lambda default arg so it doesn't change
                    handler=lambda r=row: self.paste_item(r),
                    close_on_action=True
                )
            ))
            
        return items

    def paste_item(self, item_data):
        # 1. Put back into clipboard (silently) based on type
        item_type = item_data.get('type', 'text')
        
        if item_type == 'files':
            self.monitor.set_files(item_data.get('file_path'))
        elif item_type == 'image':
            path = self.monitor.get_image_path(item_data.get('file_path'))
            if path:
                self.monitor.set_image(path)
        else:
            # Default to text
            self.monitor.set_text(item_data.get('content_text', ''))
        
        # 2. Give the OS focus back to the previous window
        # The core app hides the window, but we need a tiny delay 
        # to ensure the previous window is active before sending keys.
        time.sleep(0.15) 
        
        # 3. Simulate Ctrl+V
        send_ctrl_v()
        
    def get_extension_view(self, parent_window):
        # Return the Custom Raycast-like UI
        return ClipboardView(self.context, parent_window)

Plugin = ClipboardExtension