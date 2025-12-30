import sqlite3
import sqlite_vec
import os

DATABASE_URL = "storage/zhora.db"

def init_db():
    os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)
    conn = sqlite3.connect(DATABASE_URL)
    conn.enable_load_extension(True) # Explicitly enable extension loading
    sqlite_vec.load(conn) # Load the sqlite-vec extension
    
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content TEXT,
            embedding BLOB
        );
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.enable_load_extension(True) # Explicitly enable extension loading
    sqlite_vec.load(conn)
    return conn

