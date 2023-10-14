from cachetools import TTLCache
from config_manager import ConfigManager

class Cache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Cache, cls).__new__(cls)
            config = ConfigManager()
            cache_config = config.get_cache_config()
            cls._instance.cache = TTLCache(maxsize=cache_config.get("max_size", 100), ttl=cache_config.get("ttl", 300))
        return cls._instance

    @staticmethod
    def get():
        return Cache()._instance.cache