
import sqlite3
import os
from datetime import datetime
from .paths import DB_PATH


# =====================================================
# CONNECTION MANAGEMENT
# =====================================================

def get_connection():
    """
    Create and configure SQLite connection.
    
    Returns:
        sqlite3.Connection: Configured database connection
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    
    # Performance optimizations
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    
    return conn


# =====================================================
# INITIALIZATION
# =====================================================

def init_db():
    """
    Initialize database schema with indexes for performance.
    Creates tables and indexes if they don't exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Create main assets table
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

    # ✅ CREATE PERFORMANCE INDEXES
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_category 
        ON assets(category);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_name 
        ON assets(name COLLATE NOCASE);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_created 
        ON assets(created_at DESC);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_size 
        ON assets(file_size);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_poly_count 
        ON assets(poly_count);
    """)
    
    # Composite index for common queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_category_created 
        ON assets(category, created_at DESC);
    """)

    conn.commit()
    cur.close()
    conn.close()


def create_table_if_not_exists():
    """Alias for init_db() for backward compatibility."""
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
    
    Args:
        uuid (str): Unique identifier for the asset
        name (str): Asset name
        category (str): Asset category
        description (str): Asset description
        file_path (str): Path to asset file
        thumbnail_path (str): Path to thumbnail image
        file_size (int): File size in bytes
        poly_count (int): Polygon count
        vertices (int): Vertex count
        faces (int): Face count
    
    Returns:
        bool: True if inserted, False if updated
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM assets WHERE uuid=?", (uuid,))
    exists = cur.fetchone()

    if exists:
        # Update existing asset
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
        # Insert new asset
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


def db_update_asset(asset_id, **kwargs):
    """
    Update specific fields of an asset.
    
    Args:
        asset_id (int): Asset ID to update
        **kwargs: Fields to update (name, category, description, etc.)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not kwargs:
        return False
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Build UPDATE query dynamically
    fields = []
    values = []
    
    for key, value in kwargs.items():
        if key in ['name', 'category', 'description', 'file_path', 
                   'thumbnail_path', 'file_size', 'poly_count', 
                   'vertices', 'faces']:
            fields.append(f"{key}=?")
            values.append(value)
    
    if not fields:
        cur.close()
        conn.close()
        return False
    
    # Always update timestamp
    fields.append("updated_at=CURRENT_TIMESTAMP")
    
    query = f"UPDATE assets SET {', '.join(fields)} WHERE id=?"
    values.append(asset_id)
    
    cur.execute(query, values)
    success = cur.rowcount > 0
    
    conn.commit()
    cur.close()
    conn.close()
    
    return success


def db_delete_by_id(asset_id):
    """
    Delete asset by ID.
    
    Args:
        asset_id (int): Asset ID to delete
    
    Returns:
        bool: True if deleted, False if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    deleted = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()
    
    return deleted


def db_delete_by_uuid(uuid):
    """
    Delete asset by UUID.
    
    Args:
        uuid (str): Asset UUID to delete
    
    Returns:
        bool: True if deleted, False if not found
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM assets WHERE uuid=?", (uuid,))
    deleted = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()
    
    return deleted


# =====================================================
# READ OPERATIONS (OPTIMIZED)
# =====================================================

def db_get_all():
    """
    Get all assets (DEPRECATED - use db_get_paginated instead).
    
    Warning: This loads all assets at once. Not recommended for 1000+ assets.
    Use db_get_paginated() for better performance.
    
    Returns:
        list: List of asset dictionaries
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def db_get_paginated(page=0, page_size=50, category='ALL', search='', 
                     sort_by='created_at', sort_order='DESC'):
    """
    Get assets with pagination and filtering (RECOMMENDED).
    
    Args:
        page (int): Page number (0-indexed)
        page_size (int): Number of items per page
        category (str): Filter by category ('ALL' for no filter)
        search (str): Search term for name/description
        sort_by (str): Column to sort by
        sort_order (str): 'ASC' or 'DESC'
    
    Returns:
        tuple: (assets_list, total_count)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Build WHERE clause
    where_clauses = []
    params = []
    
    if category and category != 'ALL':
        where_clauses.append("category = ?")
        params.append(category)
    
    if search and search.strip():
        where_clauses.append("(name LIKE ? OR description LIKE ?)")
        search_term = f"%{search.strip()}%"
        params.extend([search_term, search_term])
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Get total count
    cur.execute(f"SELECT COUNT(*) FROM assets WHERE {where_sql}", params)
    total = cur.fetchone()[0]
    
    # Validate sort parameters
    valid_sort_columns = ['created_at', 'name', 'category', 'file_size', 
                          'poly_count', 'updated_at']
    if sort_by not in valid_sort_columns:
        sort_by = 'created_at'
    
    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order = 'DESC'
    
    # Get paginated results
    offset = page * page_size
    cur.execute(f"""
        SELECT * FROM assets 
        WHERE {where_sql}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])
    
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    return rows, total


def db_search_assets(search_term='', category='ALL', min_size=0, max_size=0, 
                     min_poly=0, max_poly=0, limit=100):
    """
    Advanced search with multiple filters.
    
    Args:
        search_term (str): Search in name/description
        category (str): Filter by category
        min_size (int): Minimum file size in KB
        max_size (int): Maximum file size in KB
        min_poly (int): Minimum polygon count
        max_poly (int): Maximum polygon count
        limit (int): Maximum results to return
    
    Returns:
        list: List of matching asset dictionaries
    """
    conn = get_connection()
    cur = conn.cursor()
    
    where = []
    params = []
    
    # Category filter
    if category and category != 'ALL':
        where.append("category = ?")
        params.append(category)
    
    # Text search
    if search_term and search_term.strip():
        where.append("(name LIKE ? OR description LIKE ?)")
        term = f"%{search_term.strip()}%"
        params.extend([term, term])
    
    # File size filters
    if min_size > 0:
        where.append("file_size >= ?")
        params.append(min_size * 1024)  # Convert KB to bytes
    
    if max_size > 0:
        where.append("file_size <= ?")
        params.append(max_size * 1024)
    
    # Polygon count filters
    if min_poly > 0:
        where.append("poly_count >= ?")
        params.append(min_poly)
    
    if max_poly > 0:
        where.append("poly_count <= ?")
        params.append(max_poly)
    
    where_sql = " AND ".join(where) if where else "1=1"
    
    cur.execute(f"""
        SELECT * FROM assets 
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ?
    """, params + [limit])
    
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    return rows


def db_get_by_id(asset_id):
    """
    Get single asset by ID.
    
    Args:
        asset_id (int): Asset ID
    
    Returns:
        dict or None: Asset data dictionary or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def db_get_by_uuid(uuid):
    """
    Get single asset by UUID.
    
    Args:
        uuid (str): Asset UUID
    
    Returns:
        dict or None: Asset data dictionary or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets WHERE uuid=?", (uuid,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def db_get_multiple_by_ids(asset_ids):
    """
    Get multiple assets by IDs in a single query.
    
    Args:
        asset_ids (list): List of asset IDs
    
    Returns:
        list: List of asset dictionaries
    """
    if not asset_ids:
        return []
    
    conn = get_connection()
    cur = conn.cursor()
    
    placeholders = ','.join('?' * len(asset_ids))
    cur.execute(f"SELECT * FROM assets WHERE id IN ({placeholders})", asset_ids)
    
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    return rows


# =====================================================
# STATISTICS & ANALYTICS
# =====================================================

def db_get_statistics():
    """
    Get database statistics.
    
    Returns:
        dict: Statistics including total count, categories, sizes, etc.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    stats = {}
    
    # Total count
    cur.execute("SELECT COUNT(*) FROM assets")
    stats['total_assets'] = cur.fetchone()[0]
    
    # By category
    cur.execute("""
        SELECT category, COUNT(*) as count 
        FROM assets 
        GROUP BY category
        ORDER BY count DESC
    """)
    stats['by_category'] = {row['category']: row['count'] for row in cur.fetchall()}
    
    # Size statistics
    cur.execute("""
        SELECT 
            SUM(file_size) as total_size,
            AVG(file_size) as avg_size,
            MIN(file_size) as min_size,
            MAX(file_size) as max_size
        FROM assets
    """)
    size_row = cur.fetchone()
    stats['size'] = {
        'total_bytes': size_row['total_size'] or 0,
        'avg_bytes': size_row['avg_size'] or 0,
        'min_bytes': size_row['min_size'] or 0,
        'max_bytes': size_row['max_size'] or 0,
    }
    
    # Polygon statistics
    cur.execute("""
        SELECT 
            SUM(poly_count) as total_polys,
            AVG(poly_count) as avg_polys,
            MIN(poly_count) as min_polys,
            MAX(poly_count) as max_polys
        FROM assets
    """)
    poly_row = cur.fetchone()
    stats['polygons'] = {
        'total': poly_row['total_polys'] or 0,
        'average': poly_row['avg_polys'] or 0,
        'min': poly_row['min_polys'] or 0,
        'max': poly_row['max_polys'] or 0,
    }
    
    cur.close()
    conn.close()
    
    return stats


def db_get_categories():
    """
    Get list of all unique categories in database.
    
    Returns:
        list: List of category names
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT category FROM assets ORDER BY category")
    categories = [row['category'] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return categories


# =====================================================
# MAINTENANCE & UTILITIES
# =====================================================

def db_optimize():
    """
    Optimize database performance.
    Runs VACUUM and ANALYZE to optimize storage and query planning.
    """
    conn = get_connection()
    
    # VACUUM reclaims unused space
    conn.execute("VACUUM")
    
    # ANALYZE updates query planner statistics
    conn.execute("ANALYZE")
    
    conn.close()


def db_backup(backup_path):
    """
    Create a backup of the database.
    
    Args:
        backup_path (str): Path where backup will be saved
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        return True
    except Exception as e:
        print(f"[AssetManager] Backup failed: {e}")
        return False


def db_check_integrity():
    """
    Check database integrity.
    
    Returns:
        bool: True if integrity check passes, False otherwise
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("PRAGMA integrity_check")
    result = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return result == "ok"


def db_get_size():
    """
    Get database file size.
    
    Returns:
        int: Database size in bytes
    """
    if os.path.exists(DB_PATH):
        return os.path.getsize(DB_PATH)
    return 0


def db_cleanup_orphaned_records():
    """
    Clean up records where files no longer exist.
    
    Returns:
        int: Number of records cleaned up
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT id, file_path FROM assets")
    all_assets = cur.fetchall()
    
    orphaned_ids = []
    for asset in all_assets:
        if not os.path.exists(asset['file_path']):
            orphaned_ids.append(asset['id'])
    
    if orphaned_ids:
        placeholders = ','.join('?' * len(orphaned_ids))
        cur.execute(f"DELETE FROM assets WHERE id IN ({placeholders})", orphaned_ids)
        conn.commit()
    
    count = len(orphaned_ids)
    cur.close()
    conn.close()
    
    return count


# =====================================================
# BATCH OPERATIONS
# =====================================================

def db_batch_insert(assets_data):
    """
    Insert multiple assets in a single transaction (faster).
    
    Args:
        assets_data (list): List of tuples with asset data
            Each tuple: (uuid, name, category, description, file_path, 
                        thumbnail_path, file_size, poly_count, vertices, faces)
    
    Returns:
        int: Number of assets inserted
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.executemany("""
        INSERT OR IGNORE INTO assets (
            uuid, name, category, description,
            file_path, thumbnail_path,
            file_size, poly_count, vertices, faces
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, assets_data)
    
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    return count


def db_batch_delete(asset_ids):
    """
    Delete multiple assets in a single transaction.
    
    Args:
        asset_ids (list): List of asset IDs to delete
    
    Returns:
        int: Number of assets deleted
    """
    if not asset_ids:
        return 0
    
    conn = get_connection()
    cur = conn.cursor()
    
    placeholders = ','.join('?' * len(asset_ids))
    cur.execute(f"DELETE FROM assets WHERE id IN ({placeholders})", asset_ids)
    
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    return count


# =====================================================
# MIGRATION UTILITIES
# =====================================================

def db_export_to_json(output_path):
    """
    Export all assets to JSON file.
    
    Args:
        output_path (str): Path to output JSON file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import json
        
        assets = db_get_all()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(assets, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[AssetManager] Export failed: {e}")
        return False


def db_import_from_json(input_path):
    """
    Import assets from JSON file.
    
    Args:
        input_path (str): Path to input JSON file
    
    Returns:
        int: Number of assets imported
    """
    try:
        import json
        
        with open(input_path, 'r', encoding='utf-8') as f:
            assets = json.load(f)
        
        conn = get_connection()
        cur = conn.cursor()
        
        count = 0
        for asset in assets:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO assets (
                        uuid, name, category, description,
                        file_path, thumbnail_path,
                        file_size, poly_count, vertices, faces,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    asset.get('uuid'),
                    asset.get('name'),
                    asset.get('category'),
                    asset.get('description'),
                    asset.get('file_path'),
                    asset.get('thumbnail_path'),
                    asset.get('file_size', 0),
                    asset.get('poly_count', 0),
                    asset.get('vertices', 0),
                    asset.get('faces', 0),
                    asset.get('created_at'),
                    asset.get('updated_at')
                ))
                if cur.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"[AssetManager] Failed to import asset {asset.get('name')}: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return count
        
    except Exception as e:
        print(f"[AssetManager] Import failed: {e}")
        return 0

# =====================================================
# FAVORITES OPERATIONS
# =====================================================

def db_get_favorites(page=0, page_size=20):
    """
    Get paginated favorite assets from database.
    
    Args:
        page (int): Page number (0-indexed)
        page_size (int): Number of items per page
        
    Returns:
        tuple: (list of favorite assets, total count)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get total count of favorites
        cur.execute("SELECT COUNT(*) FROM assets WHERE is_favorite = 1")
        total = cur.fetchone()[0]
        
        # Get paginated favorites
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
        print(f"[AssetManager] Error getting favorites: {e}")
        return [], 0
    finally:
        cur.close()
        conn.close()


def db_count_favorites():
    """
    Get total count of favorite assets.
    
    Returns:
        int: Number of favorite assets
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM assets WHERE is_favorite = 1")
        count = cur.fetchone()[0]
        return count
        
    except Exception as e:
        print(f"[AssetManager] Error counting favorites: {e}")
        return 0
    finally:
        cur.close()
        conn.close()


def db_toggle_favorite(asset_id):
    """
    Toggle favorite status of an asset.
    
    Args:
        asset_id (int): ID of the asset
        
    Returns:
        bool: New favorite status (True if now favorite, False if not)
        
    Raises:
        Exception: If asset not found or database error occurs
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get current status
        cur.execute("SELECT is_favorite FROM assets WHERE id = ?", (asset_id,))
        result = cur.fetchone()
        
        if not result:
            raise ValueError(f"Asset with id {asset_id} not found")
        
        current_status = result['is_favorite'] if result['is_favorite'] is not None else 0
        new_status = 0 if current_status else 1
        
        # Update status
        cur.execute("""
            UPDATE assets 
            SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, asset_id))
        
        conn.commit()
        return bool(new_status)
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to toggle favorite: {e}")
    finally:
        cur.close()
        conn.close()


def db_add_favorite_column_if_missing():
    """
    Add is_favorite column to assets table if it doesn't exist.
    This should be called during addon initialization.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if column exists
        cur.execute("PRAGMA table_info(assets)")
        columns = [column[1] for column in cur.fetchall()]
        
        if 'is_favorite' not in columns:
            cur.execute("ALTER TABLE assets ADD COLUMN is_favorite INTEGER DEFAULT 0")
            
            # Create index for performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_favorite 
                ON assets(is_favorite)
            """)
            
            conn.commit()
            print("[AssetManager] Added is_favorite column to assets table")
            
    except Exception as e:
        print(f"[AssetManager] Error adding is_favorite column: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()