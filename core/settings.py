# core/settings.py
import json
import os

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.data = {
            "disabled_extensions": []
        }
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
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