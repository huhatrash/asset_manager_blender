import sqlite3
from .paths import DB_PATH

def get_connection():
    # isolation_level=None kalo mau autocommit;
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table_if_not_exists():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'model',
        description TEXT,
        file_path TEXT,
        thumbnail_path TEXT,
        file_size INTEGER DEFAULT 0,
        poly_count INTEGER DEFAULT 0,
        vertices INTEGER DEFAULT 0,
        faces INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cur.close()
    conn.close()

def db_insert_or_update_by_uuid(
    asset_uuid, name, category, description,
    file_path, thumbnail_path,
    poly_count, vertices, faces, file_size
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM assets WHERE uuid=?", (asset_uuid,))
    row = cur.fetchone()

    if row:
        cur.execute("""
            UPDATE assets
            SET name=?, category=?, description=?,
                file_path=?, thumbnail_path=?,
                poly_count=?, vertices=?, faces=?, file_size=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE uuid=?
        """, (
            name, category, description,
            file_path, thumbnail_path,
            poly_count, vertices, faces, file_size,
            asset_uuid
        ))
        inserted = False
    else:
        cur.execute("""
            INSERT INTO assets
            (uuid, name, category, description, file_path, thumbnail_path,
             poly_count, vertices, faces, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asset_uuid, name, category, description,
            file_path, thumbnail_path,
            poly_count, vertices, faces, file_size
        ))
        inserted = True

    conn.commit()
    conn.close()
    return inserted

def db_get_all():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def db_get_by_id(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None

def db_delete_by_id(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    cur.close()
    conn.close()