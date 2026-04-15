"""
Database Module — Asset Manager
Production-grade SQLite layer with migration-safe schema management.

Author: alfa haliza
Version: 3.0 (Audited & Hardened)
"""

import sqlite3
import os
from datetime import datetime


# =====================================================
# CONNECTION MANAGEMENT
# =====================================================

def get_connection():
    """
    Create a fresh SQLite connection each call.
    DB_PATH is resolved at call-time (not module load-time)
    so it always points to the correct Blender user config dir.

    Returns:
        sqlite3.Connection: Configured database connection
    """
    # Import here so bpy is guaranteed to be ready
    from .paths import get_database_path
    db_path = get_database_path()

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row

    # WAL mode for concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL;")
    # NORMAL is safe with WAL and much faster than FULL
    conn.execute("PRAGMA synchronous=NORMAL;")
    # Enforce FK constraints
    conn.execute("PRAGMA foreign_keys=ON;")
    # 64 MB page cache
    conn.execute("PRAGMA cache_size=-65536;")
    conn.execute("PRAGMA page_size=4096;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    # 256 MB memory-mapped IO
    conn.execute("PRAGMA mmap_size=268435456;")
    conn.execute("PRAGMA locking_mode=NORMAL;")
    conn.execute("PRAGMA auto_vacuum=INCREMENTAL;")

    return conn


# =====================================================
# SCHEMA MIGRATION
# =====================================================

# Core columns that MUST exist — never removed
_REQUIRED_COLUMNS = {
    "id":              "INTEGER PRIMARY KEY AUTOINCREMENT",
    "uuid":            "TEXT NOT NULL",  # UNIQUE enforced via index
    "name":            "TEXT NOT NULL",
    "category":        "TEXT NOT NULL DEFAULT 'model'",
    "description":     "TEXT DEFAULT ''",
    "file_path":       "TEXT NOT NULL",
    "thumbnail_path":  "TEXT",
    "file_size":       "INTEGER DEFAULT 0",
    "poly_count":      "INTEGER DEFAULT 0",
    "vertices":        "INTEGER DEFAULT 0",
    "faces":           "INTEGER DEFAULT 0",
    "created_at":      "TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))",
    "updated_at":      "TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))",
    "is_favorite":     "INTEGER NOT NULL DEFAULT 0",
}

# Optional columns added in v2+ — preserved if already present, created if missing
_OPTIONAL_COLUMNS = {
    "tags":         "TEXT DEFAULT ''",
    "rating":       "INTEGER DEFAULT 0",
    "usage_count":  "INTEGER DEFAULT 0",
    "last_used_at": "TEXT",
}


def _get_existing_columns(cur, table="assets"):
    """Return set of column names currently in the table."""
    cur.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cur.fetchall()}


def _migrate_schema(conn, cur):
    """
    Non-destructive schema migration.
    Adds any missing columns; never drops existing ones.
    Safe to call on both fresh and existing databases.
    """
    existing = _get_existing_columns(cur)

    all_needed = {**_REQUIRED_COLUMNS, **_OPTIONAL_COLUMNS}
    for col_name, col_def in all_needed.items():
        if col_name == "id":
            continue  # PRIMARY KEY cannot be ALTER TABLE'd
        if col_name not in existing:
            try:
                cur.execute(f"ALTER TABLE assets ADD COLUMN {col_name} {col_def}")
                print(f"[AssetManager] Migrated: added column '{col_name}'")
            except sqlite3.OperationalError as e:
                print(f"[AssetManager] Migration warning for '{col_name}': {e}")


# =====================================================
# INITIALIZATION
# =====================================================

def init_db():
    """
    Initialize database schema.
    - Creates table if it does not exist.
    - Runs non-destructive migration to add missing columns.
    - Rebuilds a clean, minimal set of indexes.

    Safe to call multiple times (idempotent).
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ── Create table if first run ─────────────────────────────────────────
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid            TEXT NOT NULL UNIQUE,

            name            TEXT NOT NULL,
            category        TEXT NOT NULL DEFAULT 'model',
            description     TEXT DEFAULT '',

            file_path       TEXT NOT NULL,
            thumbnail_path  TEXT,

            file_size       INTEGER DEFAULT 0,
            poly_count      INTEGER DEFAULT 0,
            vertices        INTEGER DEFAULT 0,
            faces           INTEGER DEFAULT 0,

            created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),

            is_favorite     INTEGER NOT NULL DEFAULT 0,
            tags            TEXT DEFAULT '',
            rating          INTEGER DEFAULT 0,
            usage_count     INTEGER DEFAULT 0,
            last_used_at    TEXT
        );
        """)

        # ── Auxiliary tables ──────────────────────────────────────────────────
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name   TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS asset_tags (
            asset_id   INTEGER NOT NULL,
            tag_id     INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (asset_id, tag_id),
            FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id)   REFERENCES tags(id)   ON DELETE CASCADE
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            color       TEXT DEFAULT '#888888',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        """)

        # ── Run migration for existing databases ──────────────────────────────
        _migrate_schema(conn, cur)

        # ── Rebuild indexes (CREATE IF NOT EXISTS = safe) ─────────────────────
        _ensure_indexes(cur)

        conn.commit()
        print("[AssetManager] Database initialized successfully")

    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] Database init error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def _ensure_indexes(cur):
    """
    Create the minimal, non-redundant index set.
    Drops known duplicate indexes from older versions first.
    """
    # ── Remove known duplicates from previous versions ────────────────────────
    duplicates = [
        "idx_created",        # duplicate of idx_created_desc
        "idx_name",           # duplicate of idx_name_nocase
        "idx_is_favorite",    # superseded by idx_favorite_updated
        "idx_favorite_usage", # inconsistent naming
        "idx_usage_recent",   # superseded by idx_usage_count
        "idx_last_used",      # rarely used standalone
    ]
    for idx in duplicates:
        try:
            cur.execute(f"DROP INDEX IF EXISTS {idx}")
        except Exception:
            pass

    # ── Canonical indexes ─────────────────────────────────────────────────────

    # Single-column lookups (most critical)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uuid       ON assets(uuid);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_category          ON assets(category);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name_nocase       ON assets(name COLLATE NOCASE);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_is_favorite       ON assets(is_favorite);")

    # Sorting (DESC indexes are hints only; SQLite can scan both ways)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_created_desc      ON assets(created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_updated_desc      ON assets(updated_at DESC);")

    # Composite indexes for the common query patterns in db_get_paginated()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_category_created  ON assets(category, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_category_updated  ON assets(category, updated_at DESC);")

    # Range filter indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_file_size         ON assets(file_size);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_poly_count        ON assets(poly_count);")

    # FTS-style composite for search
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name_search       ON assets(name COLLATE NOCASE, description COLLATE NOCASE);")

    # Favorites ordered list
    cur.execute("CREATE INDEX IF NOT EXISTS idx_favorite_updated  ON assets(is_favorite, updated_at DESC);")

    # Tags junction table
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_asset        ON asset_tags(asset_id);")


def create_table_if_not_exists():
    """Backward-compatibility alias for init_db()."""
    init_db()


# =====================================================
# WRITE OPERATIONS
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
    """
    Insert new asset or update existing one by UUID.

    Returns:
        bool: True if inserted (new), False if updated (existing)
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM assets WHERE uuid = ?", (uuid,))
        existing = cur.fetchone()

        if existing:
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
                    updated_at=datetime('now', 'localtime')
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
                    file_size, poly_count, vertices, faces,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    datetime('now', 'localtime'),
                    datetime('now', 'localtime')
                )
            """, (
                uuid, name, category, description,
                file_path, thumbnail_path,
                file_size, poly_count, vertices, faces
            ))
            inserted = True

        conn.commit()
        return inserted

    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] db_insert_or_update_by_uuid error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def db_batch_insert_optimized(assets_data):
    """
    Batch insert with single transaction.
    Skips duplicates via INSERT OR IGNORE.

    Args:
        assets_data: list of tuples
            (uuid, name, category, description, file_path, thumbnail_path,
             file_size, poly_count, vertices, faces)

    Returns:
        int: Number of rows actually inserted
    """
    if not assets_data:
        return 0

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.executemany("""
            INSERT OR IGNORE INTO assets (
                uuid, name, category, description,
                file_path, thumbnail_path,
                file_size, poly_count, vertices, faces,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                datetime('now', 'localtime'),
                datetime('now', 'localtime')
            )
        """, assets_data)

        count = cur.rowcount
        conn.commit()
        print(f"[AssetManager] Batch inserted {count} assets")
        return count

    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] Batch insert failed: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


# =====================================================
# READ OPERATIONS
# =====================================================

# Whitelist for sort columns (prevents SQL injection)
_VALID_SORT_COLUMNS = {
    'created_at':  'created_at',
    'updated_at':  'updated_at',
    'name':        'name COLLATE NOCASE',
    'category':    'category',
    'file_size':   'file_size',
    'poly_count':  'poly_count',
    'rating':      'rating',
    'usage_count': 'usage_count',
}


def db_get_paginated(page=0, page_size=10, category='ALL', search='',
                     sort_by='created_at', sort_order='DESC',
                     min_size=0, max_size=0, min_poly=0, max_poly=0,
                     filter_favorites=False):
    """
    Paginated query with filter and sort support.

    Returns:
        tuple: (list[dict], int total_count)
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        where_clauses = []
        params = []

        if category and category != 'ALL':
            where_clauses.append("category = ?")
            params.append(category)

        if search and search.strip():
            where_clauses.append("(name LIKE ? OR description LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term])
            
        if filter_favorites:
            where_clauses.append("is_favorite = 1")

        if min_size > 0:
            where_clauses.append("file_size >= ?")
            params.append(min_size * 1024)

        if max_size > 0:
            where_clauses.append("file_size <= ?")
            params.append(max_size * 1024)

        if min_poly > 0:
            where_clauses.append("poly_count >= ?")
            params.append(min_poly)

        if max_poly > 0:
            where_clauses.append("poly_count <= ?")
            params.append(max_poly)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Count
        cur.execute(f"SELECT COUNT(*) FROM assets WHERE {where_sql}", params)
        total = cur.fetchone()[0]

        # Sort
        sort_col = _VALID_SORT_COLUMNS.get(sort_by, 'created_at')
        order = 'DESC' if sort_order.upper() == 'DESC' else 'ASC'
        offset = page * page_size

        cur.execute(f"""
            SELECT * FROM assets
            WHERE {where_sql}
            ORDER BY {sort_col} {order}
            LIMIT ? OFFSET ?
        """, params + [page_size, offset])

        rows = [dict(r) for r in cur.fetchall()]
        return rows, total

    finally:
        cur.close()
        conn.close()


def db_get_by_id(asset_id):
    """Fetch single asset by primary key."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM assets WHERE id = ? LIMIT 1", (asset_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def db_get_by_uuid(uuid):
    """Fetch single asset by UUID."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM assets WHERE uuid = ? LIMIT 1", (uuid,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def db_get_all():
    """
    Return all assets ordered by created_at DESC.

    .. deprecated::
        Prefer :func:`db_get_paginated` for large libraries.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM assets ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def db_search_assets(search_term='', category='ALL', min_size=0, max_size=0,
                     min_poly=0, max_poly=0, limit=100, filter_favorites=False):
    """
    Filtered asset search without pagination.

    .. deprecated::
        Prefer :func:`db_get_paginated` for consistent pagination.
    """
    rows, _ = db_get_paginated(
        page=0,
        page_size=limit,
        category=category,
        search=search_term,
        min_size=min_size,
        max_size=max_size,
        min_poly=min_poly,
        max_poly=max_poly,
        filter_favorites=filter_favorites,
    )
    return rows


# =====================================================
# UPDATE & DELETE OPERATIONS
# =====================================================

# Whitelist of fields that callers are allowed to update
_UPDATABLE_FIELDS = frozenset({
    'name', 'category', 'description', 'file_path',
    'thumbnail_path', 'file_size', 'poly_count',
    'vertices', 'faces', 'tags', 'rating',
})


def db_update_asset(asset_id, **kwargs):
    """
    Update specific fields of an asset by ID.

    Only fields in _UPDATABLE_FIELDS are accepted; all others are silently
    ignored, preventing accidental or malicious column injection.

    Returns:
        bool: True if a row was updated
    """
    safe_kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_FIELDS}
    if not safe_kwargs:
        return False

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clauses = [f"{k} = ?" for k in safe_kwargs]
        set_clauses.append("updated_at = datetime('now', 'localtime')")
        values = list(safe_kwargs.values()) + [asset_id]

        cur.execute(
            f"UPDATE assets SET {', '.join(set_clauses)} WHERE id = ?",
            values
        )
        success = cur.rowcount > 0
        conn.commit()
        return success

    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] db_update_asset error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def db_delete_by_id(asset_id):
    """Delete asset by primary key. Returns True if deleted."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] db_delete_by_id error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def db_delete_by_uuid(uuid):
    """Delete asset by UUID. Returns True if deleted."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM assets WHERE uuid = ?", (uuid,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] db_delete_by_uuid error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


# =====================================================
# FAVORITES OPERATIONS
# =====================================================

def db_get_favorites(page=0, page_size=20):
    """
    Get paginated list of favorite assets.

    Returns:
        tuple: (list[dict], int total)
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM assets WHERE is_favorite = 1")
        total = cur.fetchone()[0]

        offset = page * page_size
        cur.execute("""
            SELECT * FROM assets
            WHERE is_favorite = 1
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))

        rows = [dict(r) for r in cur.fetchall()]
        return rows, total

    except Exception as e:
        print(f"[AssetManager] db_get_favorites error: {e}")
        return [], 0
    finally:
        cur.close()
        conn.close()


def db_toggle_favorite(asset_id):
    """
    Toggle is_favorite flag for an asset.

    Returns:
        bool: New favorite state (True = now a favorite)

    Raises:
        ValueError: If asset not found
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_favorite FROM assets WHERE id = ?", (asset_id,))
        result = cur.fetchone()

        if result is None:
            raise ValueError(f"Asset id={asset_id} not found")

        new_status = 0 if result['is_favorite'] else 1
        cur.execute("""
            UPDATE assets
            SET is_favorite = ?,
                updated_at  = datetime('now', 'localtime')
            WHERE id = ?
        """, (new_status, asset_id))

        conn.commit()
        return bool(new_status)

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"db_toggle_favorite failed: {e}") from e
    finally:
        cur.close()
        conn.close()


# =====================================================
# STATISTICS & MAINTENANCE
# =====================================================

def db_get_statistics():
    """
    Return aggregate statistics about the asset library.

    Returns:
        dict: Keys 'total_assets', 'size', 'polygons', 'by_category'
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                COUNT(*)       AS total,
                SUM(file_size) AS total_size,
                AVG(file_size) AS avg_size,
                MIN(file_size) AS min_size,
                MAX(file_size) AS max_size,
                SUM(poly_count) AS total_polys,
                AVG(poly_count) AS avg_polys,
                MIN(poly_count) AS min_polys,
                MAX(poly_count) AS max_polys
            FROM assets
        """)
        row = cur.fetchone()

        stats = {
            'total_assets': row['total'],
            'size': {
                'total_bytes': row['total_size'] or 0,
                'avg_bytes':   row['avg_size']   or 0,
                'min_bytes':   row['min_size']   or 0,
                'max_bytes':   row['max_size']   or 0,
            },
            'polygons': {
                'total':   row['total_polys'] or 0,
                'average': row['avg_polys']   or 0,
                'min':     row['min_polys']   or 0,
                'max':     row['max_polys']   or 0,
            },
        }

        cur.execute("""
            SELECT category, COUNT(*) AS count
            FROM assets
            GROUP BY category
            ORDER BY count DESC
        """)
        stats['by_category'] = {r['category']: r['count'] for r in cur.fetchall()}

        return stats
    finally:
        cur.close()
        conn.close()


def db_check_integrity():
    """
    Run SQLite integrity check and return a status report.

    Returns:
        dict: {
            'ok': bool,
            'integrity': str,
            'foreign_keys': list,
            'orphaned_files': list,
            'total_assets': int,
        }
    """
    conn = get_connection()
    cur = conn.cursor()
    report = {}

    try:
        cur.execute("PRAGMA integrity_check")
        result = cur.fetchone()[0]
        report['integrity'] = result
        report['ok'] = (result == 'ok')

        cur.execute("PRAGMA foreign_key_check")
        report['foreign_keys'] = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) FROM assets")
        report['total_assets'] = cur.fetchone()[0]

        # Detect assets whose files are missing on disk
        cur.execute("SELECT id, uuid, name, file_path FROM assets")
        orphaned = []
        for r in cur.fetchall():
            if r['file_path'] and not os.path.exists(r['file_path']):
                orphaned.append({
                    'id':        r['id'],
                    'uuid':      r['uuid'],
                    'name':      r['name'],
                    'file_path': r['file_path'],
                })
        report['orphaned_files'] = orphaned

        return report

    finally:
        cur.close()
        conn.close()


def db_optimize():
    """
    Comprehensive database optimization.
    Should be run periodically (e.g. weekly / on demand).
    """
    conn = get_connection()
    print("[AssetManager] Starting database optimization...")
    try:
        conn.execute("REINDEX")
        print("[AssetManager] Indexes rebuilt")
        conn.execute("ANALYZE")
        print("[AssetManager] Statistics updated")
        # VACUUM cannot run inside a transaction; WAL mode is fine
        conn.execute("VACUUM")
        print("[AssetManager] VACUUM complete")
        conn.execute("PRAGMA incremental_vacuum")
        print("[AssetManager] Incremental vacuum complete")
        print("[AssetManager] Optimization finished")
    except Exception as e:
        print(f"[AssetManager] Optimization error: {e}")
    finally:
        conn.close()


def db_delete_orphaned_assets():
    """
    Remove database records whose export files no longer exist on disk.

    Returns:
        list[dict]: Records that were deleted
    """
    report = db_check_integrity()
    orphans = report.get('orphaned_files', [])

    if not orphans:
        print("[AssetManager] No orphaned assets found")
        return []

    conn = get_connection()
    cur = conn.cursor()
    try:
        ids = [o['id'] for o in orphans]
        placeholders = ','.join('?' for _ in ids)
        cur.execute(f"DELETE FROM assets WHERE id IN ({placeholders})", ids)
        conn.commit()
        print(f"[AssetManager] Deleted {len(orphans)} orphaned asset records")
        return orphans
    except Exception as e:
        conn.rollback()
        print(f"[AssetManager] db_delete_orphaned_assets error: {e}")
        return []
    finally:
        cur.close()
        conn.close()