import sqlite3
from .paths import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE,
        name TEXT,
        category TEXT,
        description TEXT,
        file_path TEXT,
        thumbnail_path TEXT,
        file_size INTEGER,
        poly_count INTEGER,
        vertices INTEGER,
        faces INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def get_all():
    conn = get_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM assets ORDER BY id DESC")]
    conn.close()
    return rows

def get_by_id(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def delete(asset_id):
    conn = get_connection()
    conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    conn.close()
