from cachetools import TTLCache
from config_manager import ConfigManager

class Cache:
    _instances = {}

    def __new__(cls, config_manager=None):
        # If no specific instance for this config manager, create one
        if config_manager not in cls._instances:
            instance = super(Cache, cls).__new__(cls)
            cls._instances[config_manager] = instance
        return cls._instances[config_manager]

    def __init__(self, config_manager=None):
        # Initialize only once
        if not hasattr(self, 'is_initialized'):
            self.is_initialized = True
            if config_manager is None:
                config_manager = ConfigManager()
            cache_config = config_manager.get_cache_config()
            self.cache = TTLCache(maxsize=cache_config.get("max_size", 100), ttl=cache_config.get("ttl", 300))

    def get(self):
        return self.cache
