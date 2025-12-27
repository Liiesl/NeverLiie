# core/settings.py
import json
import os

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.data = {
            "disabled_extensions": [],
            "extension_settings": {} # New storage for specific extension data
        }
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    loaded = json.load(f)
                    # Merge loaded data carefully to preserve structure if keys represent new features
                    self.data.update(loaded)
                    if "extension_settings" not in self.data:
                        self.data["extension_settings"] = {}
            except Exception as e:
                print(f"[Settings] Error loading settings: {e}")
        else:
            self.save()

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[Settings] Error saving settings: {e}")

    # --- Global Extension Management ---
    def is_extension_enabled(self, extension_id):
        return extension_id not in self.data["disabled_extensions"]

    def set_extension_enabled(self, extension_id, enabled):
        disabled_list = self.data["disabled_extensions"]
        if enabled:
            if extension_id in disabled_list:
                disabled_list.remove(extension_id)
        else:
            if extension_id not in disabled_list:
                disabled_list.append(extension_id)
        self.save()

    # --- Per-Extension Storage ---
    def get_ext_setting(self, ext_id, key, default=None):
        """Retrieve a specific setting for a specific extension."""
        ext_data = self.data["extension_settings"].get(ext_id, {})
        return ext_data.get(key, default)

    def set_ext_setting(self, ext_id, key, value):
        """Save a specific setting for a specific extension."""
        if ext_id not in self.data["extension_settings"]:
            self.data["extension_settings"][ext_id] = {}
        
        self.data["extension_settings"][ext_id][key] = value
        self.save()