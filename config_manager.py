import os
from ruamel.yaml import YAML
from cachetools import TTLCache
from typing import Any, Dict, List, Optional

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.cache = TTLCache(maxsize=1000, ttl=3800)
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.config_data = self.load_config()

    def get(self, key_path: str, default: Optional[Any] = None) -> Any:
        """Fetches a single configuration value."""
        if key_path in self.cache:
            return self.cache[key_path]

        keys = key_path.split(".")
        value = self.config_data
        for key in keys:
            if key in value:
                value = value[key]
            else:
                self.cache[key_path] = default
                return default

        self.cache[key_path] = value
        return value

    def interpret_boolean(self, value: Any, default: Optional[bool] = None) -> bool:
        """Interprets various string formats as boolean values, returns default if not a boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ["true", "on", "yes"]:
                return True
            elif value_lower in ["false", "off", "no"]:
                return False
        return default

    def get_boolean(self, key_path: str, default: Optional[bool] = None) -> bool:
        """Fetches a configuration value and interprets it as a boolean."""
        value = self.get(key_path)
        return self.interpret_boolean(value, default)

    def get_batch(self, key_paths: List[str]) -> Dict[str, Any]:
        """Fetches multiple configuration values in a batch."""
        results = {}
        for key_path in key_paths:
            results[key_path] = self.get(key_path)
        return results

    def validate_config(self) -> bool:
        """Validates the loaded configuration data. Returns True if valid, otherwise False."""
        # Implement your validation logic here
        return True

    def get_cache_config(self) -> Dict[str, Any]:
        """Fetches the cache configuration."""
        return self.get("cache", {})

    def get_db_config(self) -> Dict[str, Any]:
        """Fetches the database configuration."""
        return self.get("database", {})

    def reload_config(self) -> None:
        """Reloads the configuration from the YAML file."""
        self.cache.clear()
        self.config_data = self.load_config()
        print("Reload completed!")

    def load_config(self) -> Dict[str, Any]:
        """Loads the configuration from the YAML file and returns the loaded data."""
        if not os.path.exists(self.config_path):
            print(f"Config file '{self.config_path}' not found. Creating new one.")
            return {}

        with open(self.config_path, 'r') as file:
            try:
                return self.yaml.load(file) or {}
            except Exception as e:
                print(f"Error loading config file: {e}")
                return {}

    def save_config(self) -> None:
        """Saves the entire configuration to the YAML file."""
        with open(self.config_path, 'w') as file:
            self.yaml.dump(self.config_data, file)
        print("Configuration saved!")

    def update_category_data(self, category, data: list) -> None:
        """Updates the specified category in the configuration."""
        if category not in self.config_data:
            self.config_data[category] = []

        existing_data = set(self.config_data[category])
        updated_data = existing_data.union(data)
        self.config_data[category] = list(updated_data)

        self.save_config()
    
    def overwrite_category_data(self, category, data: list) -> None:
        """Overwrites the specified category in the configuration with new data."""
        self.config_data[category] = data
        self.save_config()