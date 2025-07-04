import psycopg2
import os
import time

postgres_config = {
    "host": os.getenv("POSTGRES_HOST", "db"),
    "database": os.getenv("POSTGRES_DB", "mydb"),
    "user": os.getenv("POSTGRES_USER", "myuser"),
    "password": os.getenv("POSTGRES_PASSWORD", "mypassword"),
    "port": 5432
}

class PostgresManager:
    def __init__(self, config):
        self.config = config
        self.conn = None

    def __enter__(self):
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                self.conn = psycopg2.connect(**self.config)
                print(f"✅ Connected to Postgres on attempt {attempt}")
                return self
            except psycopg2.OperationalError as e:
                print(f"⚠️ Postgres not ready, attempt {attempt}/{max_attempts}. Retrying in 3s...")
                time.sleep(3)
        raise Exception("❌ Could not connect to Postgres after retries.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    size BIGINT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL
                );
            """)
            self.conn.commit()

    def add_file(self, name, original_name, size, type_):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO images (name, original_name, size, type)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (name, original_name, size, type_))
            self.conn.commit()
            return cur.fetchone()[0]

    def get_page_by_page_num(self, page, limit=10, is_print=False):
        offset = (page - 1) * limit
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images;")
            total = cur.fetchone()[0]
            cur.execute("""
                SELECT id, name, original_name, size, uploaded_at, type
                FROM images
                ORDER BY uploaded_at DESC
                LIMIT %s OFFSET %s;
            """, (limit, offset))
            rows = cur.fetchall()
            return total, rows

    def get_id_by_filename(self, image_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT name FROM images WHERE id = %s;", (image_id,))
            result = cur.fetchone()
            return result[0] if result else None

    def delete_by_id(self, image_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM images WHERE id = %s;", (image_id,))
            self.conn.commit()
