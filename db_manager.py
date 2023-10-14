import sqlite3
from contextlib import closing
from cache_manager import Cache
from config_manager import ConfigManager

class DBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)

            # Fetch database configurations
            config = ConfigManager()
            db_config = config.get_db_config()
            db_name = db_config.get("db_name", "default.db")

            cls._instance.conn = sqlite3.connect(db_name)
            cls._instance.cache = Cache.get()
        return cls._instance

    @staticmethod
    def get_connection():
        return DBManager()._instance.conn

    @staticmethod
    def create_tables():
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                summary TEXT,
                thumbnail TEXT,
                embed_code TEXT
            );
        """)
        conn.commit()

    @staticmethod
    def execute_query(query, params=()):
        cache_key = f"query:{query}:{params}"
        cache = DBManager()._instance.cache

        if cache_key in cache:
            return cache[cache_key]

        conn = DBManager.get_connection()
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, params)
            conn.commit()
            result = cursor.fetchall()
            cache[cache_key] = result
            return result

    @staticmethod
    def fetch_data(query, params=()):
        return DBManager.execute_query(query, params)
