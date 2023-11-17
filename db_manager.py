import os
import json
import asyncio
import asyncpg

class DBManager:
    def __init__(self, dsn=None):
        self.pool = None
        self.dsn = dsn


    async def get_pool(self, dsn=None):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=dsn or self.dsn,
                min_size=1,
                max_size=100
            )
        return self.pool
    
    async def drop_table(self, table_name=None):
        pool = await self.get_pool()
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

    async def create_tables(self):
        pool = await self.get_pool()
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

    async def drop_columns_from_table(self, table_name, columns_to_drop):
        # Create a single query to drop multiple columns
        alter_statements = ', '.join([f'DROP COLUMN IF EXISTS {column}' for column in columns_to_drop])
        drop_columns_query = f'ALTER TABLE {table_name} {alter_statements};'
        
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                try:
                    await conn.execute(drop_columns_query)
                    print(f"Columns {columns_to_drop} have been dropped from {table_name}")
                except Exception as e:
                    print(f"An error occurred: {e}")

    async def select_data(self, table_name, query=None, params=None):
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # If a custom query is provided, use it directly
                if query:
                    final_query = f"SELECT json_agg(t) FROM (SELECT * FROM {table_name} {query}) t"
                else:
                    # If no custom query is provided, select all from the table
                    final_query = f"SELECT json_agg(t) FROM (SELECT * FROM {table_name}) t"
    
                print(final_query)
                if params:
                    print(*params)
                # Execute the query with the provided parameters and return the result
                record = await conn.fetchval(final_query, *params) if params else await conn.fetchval(final_query)
                return json.loads(record) if record else None

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

class QueryBuilder:
    def __init__(self):
        self.where_clauses = []
        self.params = []  # Store the parameters for prepared statements
        self.order_by_clause = None
        self.limit_clause = None

    def where(self, condition, *params):
        self.where_clauses.append(condition)
        self.params.extend(params)
        return self

    def orderBy(self, columns):
        self.order_by_clause = f"ORDER BY {columns}"
        return self

    def limit(self, limit):
        self.limit_clause = f"LIMIT {limit}"
        return self

    def build(self):
        final_where_clauses = []
        param_index = 1

        # Iterate through each clause and replace '%s' with unique '${i}'
        for clause in self.where_clauses:
            while '%s' in clause:
                clause = clause.replace('%s', f"${param_index}", 1)
                param_index += 1
            final_where_clauses.append(clause)

        # Build the query
        query_parts = [
            "WHERE " + " AND ".join(final_where_clauses) if final_where_clauses else "",
            self.order_by_clause or "",
            self.limit_clause or ""
        ]

        # Join the query parts and return
        return " ".join(filter(None, query_parts)).strip(), self.params
