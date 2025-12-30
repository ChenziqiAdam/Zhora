import sqlite3
import sqlite_vec
import os
from ai_services import EMBEDDING_DIMENSION

DATABASE_URL = "storage/zhora.db"

def init_db():
    os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)
    conn = sqlite3.connect(DATABASE_URL)
    conn.enable_load_extension(True)
    
    try:
        conn.load_extension(sqlite_vec.loadable_path())
    except Exception as e:
        print(f"Failed to load sqlite-vec extension: {e}")
        conn.close()
        return
    
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content TEXT,
            embedding BLOB
        );
    """)
    
    # Create the virtual table for vector search
    try:
        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_vec USING vec0(
                embedding float[{EMBEDDING_DIMENSION}]
            );
        """)
    except sqlite3.OperationalError:
        # Fallback: create without virtual table if vec extension fails
        print("Warning: Could not create vector search table. Vector search will not be available.")
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.enable_load_extension(True)
    conn.load_extension(sqlite_vec.loadable_path())
    return conn

