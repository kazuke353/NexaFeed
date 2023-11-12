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

async def drop_table(table_name=None):
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                if table_name:  # If a specific table name is provided
                    await conn.execute(f"""
                        DROP TABLE IF EXISTS {table_name};
                    """)
                else:  # If no table name is provided, drop all tables listed
                    await conn.execute("""
                                       DROP TABLE IF EXISTS feed_entries;
                                       """)
                    await conn.execute("""
                                       DROP TABLE IF EXISTS feed_metadata;
                                       """)
                    await conn.execute("""
                                       DROP TABLE IF EXISTS feeds;
                                       """)
                    await conn.execute("""
                                       DROP TABLE IF EXISTS categories;
                                       """)

async def create_tables():
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id SERIAL PRIMARY KEY,
                        name TEXT
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feeds (
                        id SERIAL PRIMARY KEY,
                        name TEXT,
                        url TEXT,
                        category_id INTEGER REFERENCES categories(id)
                    )
                """)

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
                        id BIGSERIAL PRIMARY KEY,
                        original_link TEXT UNIQUE,
                        category_id INTEGER REFERENCES categories(id),
                        title TEXT,
                        content TEXT,
                        summary TEXT,
                        thumbnail TEXT,
                        video_id TEXT,
                        additional_info JSONB,
                        published_date TIMESTAMP WITH TIME ZONE,
                        url TEXT
                    );
                """)

async def drop_columns_from_table(pool, table_name, columns_to_drop):
    # Create a single query to drop multiple columns
    alter_statements = ', '.join([f'DROP COLUMN IF EXISTS {column}' for column in columns_to_drop])
    drop_columns_query = f'ALTER TABLE {table_name} {alter_statements};'
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute(drop_columns_query)
                print(f"Columns {columns_to_drop} have been dropped from {table_name}")
            except Exception as e:
                print(f"An error occurred: {e}")

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

    async def select_data(self, table_name, condition=None):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                values = []
                order_clause = ""
                limit_clause = ""
                custom_where_clause = ""
                standard_where_clause = ""
                standard_where_parts = []

                if condition:
                    # Extract and handle special parameters from condition
                    limit = condition.pop('limit', None)
                    order_by = condition.pop('order_by', None)
                    custom_where = condition.pop('WHERE', None)
                    custom_values = condition.pop('VALUES', [])

                    # Process standard conditions
                    for key, value in condition.items():
                        if isinstance(value, list) and len(value) == 2:
                            # Handling conditions in the format {"column": ["operator", "value"]}
                            standard_where_parts.append(f"{key} {value[0]} ${len(values) + 1}")
                            values.append(value[1])
                        else:
                            # Handling simple equality conditions
                            standard_where_parts.append(f"{key} = ${len(values) + 1}")
                            values.append(value)

                    standard_where_clause = ' AND '.join(standard_where_parts)
                    if standard_where_clause:
                        standard_where_clause = f"WHERE {standard_where_clause}"

                    # Construct custom WHERE clause
                    if custom_where:
                        # Append custom WHERE clause, ensuring to add AND if standard conditions exist
                        custom_where_clause = f"{' AND' if 'WHERE' in standard_where_clause else ' WHERE'}{custom_where}"
                        values.extend(custom_values)

                    if order_by:
                        order_clause = f"ORDER BY {order_by}"

                    limit_clause = f"LIMIT {limit}" if limit is not False or limit is not None else ""

                query = f"""
                    SELECT json_agg(t) 
                    FROM (SELECT * FROM {table_name} 
                    {standard_where_clause}
                    {custom_where_clause}
                    {order_clause}
                    {limit_clause}) t
                """
                print(query)
                record = await conn.fetchval(query, *values)
                if record:
                    record = json.loads(str(record))

                return record

    async def delete_data(self, table_name, condition):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Build the WHERE clause with the provided condition
                where_clause = ' AND '.join(f"{k} = ${i+1}" for i, (k, v) in enumerate(condition.items()))
                query = f"DELETE FROM {table_name} WHERE {where_clause}"
                await conn.execute(query, *condition.values())

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
    
    async def insert_many(self, pool, table_name, data_list, on_conflict_action="DO NOTHING", conflict_target=None, update_columns=None):
        # Serialize any JSON fields if necessary, done once if all data rows are uniform
        if not data_list:
            return
        first_row = data_list[0]
        json_fields = {k for k, v in first_row.items() if isinstance(v, (dict, list))}

        # Prepare the columns for the INSERT statement from the first data row
        columns = ', '.join(first_row.keys())
        values_placeholders = ', '.join(f"${i+1}" for i in range(len(first_row)))

        # If conflict_target is not provided, default to the first column
        conflict_target = conflict_target or next(iter(first_row))

        # Determine update columns if not specified and not using 'DO NOTHING'
        if update_columns is None and on_conflict_action == "DO UPDATE":
            update_columns = [col for col in first_row if col != conflict_target]

        # Prepare the ON CONFLICT clause
        conflict_clause = "ON CONFLICT DO NOTHING"
        if on_conflict_action == "DO UPDATE":
            update_values = ', '.join(f"{col}=EXCLUDED.{col}" for col in update_columns)
            conflict_clause = f"ON CONFLICT ({conflict_target}) DO UPDATE SET {update_values}"

        # SQL template for inserting data
        sql = f"INSERT INTO {table_name}({columns}) VALUES({values_placeholders}) {conflict_clause}"

        # Use a prepared statement
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Prepare the statement once
                prepared_stmt = await conn.prepare(sql)
                
                # Execute the prepared statement with each set of data
                for row in data_list:
                    for field in json_fields:
                        row[field] = json.dumps(row[field])
                    await prepared_stmt.executemany([list(row.values())])

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
        #await drop_table("feeds")
        #await drop_table("categories")
        await create_tables()
        #await drop_columns_from_table(pool, "feed_entries", ['etag'])

        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_entries_published_date ON feed_entries(published_date DESC, id DESC);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_entries_creator ON feed_entries USING gin ((additional_info ->> 'creator') gin_trgm_ops);")

        print("PostgreSQL setup completed.")

    except asyncpg.exceptions.PostgresError as e:
        print(f"PostgreSQL connection failed: {e}")

# Check if PostgreSQL connection is successful and perform setup
async def run_setup():
    await setup_postgresql()

asyncio.run(run_setup())
