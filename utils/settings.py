import os
import json
from PyQt5.QtCore import QDir

class Settings:
    def __init__(self):
        self.app_data_dir = os.path.join(QDir.homePath(), ".videolibrary")
        self.settings_file = os.path.join(self.app_data_dir, "settings.json")
        
        self.default_settings = {
            "theme": "light",
            "start_folder": QDir.homePath(),
            "preview_length_seconds": 3,
            "default_volume": 70,
            "recent_folders": [],
            "window_size": (1024, 768)
        }
        
        self.settings = self._load_settings()
    
    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except Exception:
                return self.default_settings.copy()
        else:
            settings = self.default_settings.copy()
            self._save_settings(settings)
            return settings
    
    def _save_settings(self, settings):
        os.makedirs(self.app_data_dir, exist_ok=True)
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=4)
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value
        self._save_settings(self.settings)
    
    def add_recent_folder(self, folder_path):
        recent = self.settings.get("recent_folders", [])
        
        if folder_path in recent:
            recent.remove(folder_path)
            
        recent.insert(0, folder_path)
        
        if len(recent) > 10:
            recent = recent[:10]
            
        self.settings["recent_folders"] = recent
        self._save_settings(self.settings) 