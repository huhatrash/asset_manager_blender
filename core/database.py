import sqlite3
from .paths import DB_PATH

# =====================================================
# CONNECTION
# =====================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

# =====================================================
# INIT
# =====================================================

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT NOT NULL UNIQUE,

        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'model',
        description TEXT DEFAULT '',

        file_path TEXT NOT NULL,
        thumbnail_path TEXT,

        file_size INTEGER DEFAULT 0,
        poly_count INTEGER DEFAULT 0,
        vertices INTEGER DEFAULT 0,
        faces INTEGER DEFAULT 0,

        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

def create_table_if_not_exists():
    init_db()

# =====================================================
# WRITE
# =====================================================

def db_insert_or_update_by_uuid(
    uuid,
    name,
    category,
    description,
    file_path,
    thumbnail_path,
    file_size,
    poly_count,
    vertices,
    faces
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM assets WHERE uuid=?", (uuid,))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
        UPDATE assets SET
            name=?,
            category=?,
            description=?,
            file_path=?,
            thumbnail_path=?,
            file_size=?,
            poly_count=?,
            vertices=?,
            faces=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE uuid=?
        """, (
            name, category, description,
            file_path, thumbnail_path,
            file_size, poly_count, vertices, faces,
            uuid
        ))
        inserted = False
    else:
        cur.execute("""
        INSERT INTO assets (
            uuid, name, category, description,
            file_path, thumbnail_path,
            file_size, poly_count, vertices, faces
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uuid, name, category, description,
            file_path, thumbnail_path,
            file_size, poly_count, vertices, faces
        ))
        inserted = True

    conn.commit()
    cur.close()
    conn.close()
    return inserted

# =====================================================
# READ
# =====================================================

def db_get_all():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets ORDER BY created_at DESC")
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

def db_get_by_uuid(uuid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets WHERE uuid=?", (uuid,))
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
