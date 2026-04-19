# VeriSift/src/verisift/utils/config_manager.py
import json
import os
from pathlib import Path
from ..config import VerisiftConfig

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".verisift"
        self.config_file = self.config_dir / "config.json"
        self._ensure_dir()

    def _ensure_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_user_config(self):
        """Loads saved settings and merges them with VerisiftConfig defaults."""
        defaults = VerisiftConfig()
        if not self.config_file.exists():
            return defaults
        
        try:
            with open(self.config_file, 'r') as f:
                user_data = json.load(f)
                # Update default dataclass with saved user values
                for key, value in user_data.items():
                    if hasattr(defaults, key):
                        setattr(defaults, key, value)
            return defaults
        except Exception:
            return defaults

    def set_config(self, key, value):
        """Saves a specific setting permanently."""
        current_data = {}
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                current_data = json.load(f)
        
        # Simple type conversion for CLI inputs
        if isinstance(value, str):
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
        current_data[key] = value
        with open(self.config_file, 'w') as f:
            json.dump(current_data, f, indent=4)

    def reset_to_defaults(self):
        """Deletes the user config file to restore factory settings."""
        if self.config_file.exists():
            os.remove(self.config_file)
            return True
        return False