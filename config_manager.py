import yaml
from cachetools import TTLCache
from typing import Any, Dict, List, Optional

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.cache = TTLCache(maxsize=100, ttl=900)  # Cache with a Time-To-Live of 300 seconds
        self.config_data: Dict[str, Any] = {}
        self.reload_config()

    def reload_config(self) -> None:
        """Reloads the configuration from the YAML file."""
        with open(self.config_path, 'r') as file:
            self.config_data = yaml.safe_load(file)
        
        self.cache.clear()
        print("Reload completed!")

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