import os
import json
import asyncio
import asyncpg
from datetime import timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def drop_table():
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    DROP TABLE IF EXISTS feed_entries;
                """)

async def create_tables():
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Create table for feed metadata
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feed_metadata (
                        url TEXT PRIMARY KEY,
                        etag TEXT,
                        content_length BIGINT,
                        last_modified TIMESTAMP WITH TIME ZONE,
                        expires TIMESTAMP WITH TIME ZONE,
                        last_checked TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feed_entries (
                        original_link TEXT PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        summary TEXT,
                        thumbnail TEXT,
                        video_id TEXT,
                        additional_info TEXT,
                        published_date TIMESTAMP WITH TIME ZONE,
                        etag TEXT,
                        url TEXT
                    )
                """)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False)

class DBManager:
    def __init__(self):
        self.engine = None
        self.session = None
        self.pool = None
    
    async def get_engine(self):
        return create_engine(DATABASE_URL)

    async def get_pool(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=1,
                max_size=100
            )
        return self.pool

    async def get_session(self):
        if self.session is None:
            engine = await self.get_pool()
            self.session = SessionLocal(bind=engine)
        return self.session

    async def commit_session(self):
        if self.session is not None:
            await self.session.commit()

    async def release_pool(self, connection):
        await connection.release()

    async def close_session(self):
        if self.session is not None:
            await self.session.close()
            await self.engine.close()
            await self.engine.wait_closed()

    async def insert_data(self, pool, table_name, data, on_conflict_action="DO NOTHING", conflict_target=None, update_columns=None):
        # Serialize any JSON fields if necessary
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in data.items()}

        # Prepare the columns and values for the INSERT statement
        columns = ', '.join(data.keys())
        values_placeholders = ', '.join(f"${i+1}" for i in range(len(data)))
        values = list(data.values())

        # If conflict_target is not provided, default to the first column
        if conflict_target is None:
            conflict_target = next(iter(data))

        # Determine update columns if not specified
        if update_columns is None:
            update_columns = [col for col in data if col != conflict_target]

        # Prepare the ON CONFLICT clause
        if on_conflict_action == "DO UPDATE":
            # Generate the SET clause for the specified update columns or all except the conflict target
            update_values = ', '.join(f"{col}=EXCLUDED.{col}" for col in update_columns)
            conflict_clause = f"ON CONFLICT ({conflict_target}) DO UPDATE SET {update_values}"
        else:
            conflict_clause = "ON CONFLICT DO NOTHING"

        # SQL template for inserting data
        sql = f"""
            INSERT INTO {table_name}({columns})
            VALUES({values_placeholders})
            {conflict_clause}
        """

        async with pool.acquire() as conn:
            async with conn.transaction():
                try:
                    await conn.execute(sql, *values)
                except Exception as e:
                    # Log the exception or re-raise if needed
                    print(f"An error occurred while inserting data into {table_name}: {e}")

async def setup_postgresql():
    try:
        # Create a connection pool
        pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        
        async with pool.acquire() as conn:
            # Check if the user exists
            user_exists = await conn.fetchrow(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}'")
            
            # Create the user if it doesn't exist
            if not user_exists:
                await conn.execute(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASS}'")
                print(f"User '{DB_USER}' created.")

            # Check if the database exists
            db_exists = await conn.fetchrow(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
            
            # Create the database if it doesn't exist
            if not db_exists:
                await conn.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")
                print(f"Database '{DB_NAME}' created.")

        #await drop_table()
        await create_tables()

        print("PostgreSQL setup completed.")

    except asyncpg.exceptions.PostgresError as e:
        print(f"PostgreSQL connection failed: {e}")

# Check if PostgreSQL connection is successful and perform setup
async def run_setup():  # Make the run_setup() function an async function
    await setup_postgresql()

asyncio.run(run_setup())  # Call the run_setup() function using asyncio.run()
