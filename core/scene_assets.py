
import bpy
from .database import db_get_paginated, db_get_by_id, db_search_assets
from .preview import load_preview_for_single_asset, unload_preview


# =====================================================
# MAIN LOADING FUNCTION (PAGINATED)
# =====================================================

def load_assets_to_scene(context, page=0, page_size=10, force_reload=False):
    """
    Load assets to scene with pagination support.
    
    Args:
        context: Blender context
        page (int): Page number (0-indexed)
        page_size (int): Items per page
        force_reload (bool): Force reload even if same page
    
    Returns:
        int: Number of assets loaded
    """
    scene = context.scene
    
    if not hasattr(scene, "asset_items"):
        return 0
    
    # Check if we need to reload
    current_page = getattr(scene, "asset_current_page", -1)
    if not force_reload and current_page == page and len(scene.asset_items) > 0:
        return len(scene.asset_items)  # Already loaded this page
    
    # Get filter parameters from scene
    category = getattr(scene, "asset_category", 'ALL')
    search = getattr(scene, "asset_search", "")
    filter_favorites = getattr(scene, "filter_favorites", False)
    sort_by = getattr(scene, "asset_sort_by", 'created_at')
    sort_order = getattr(scene, "asset_sort_order", 'DESC')
    
    # Get advanced filter parameters
    min_size = getattr(scene, "filter_min_size", 0)
    max_size = getattr(scene, "filter_max_size", 0)
    min_poly = getattr(scene, "filter_min_poly", 0)
    max_poly = getattr(scene, "filter_max_poly", 0)
    min_vert = getattr(scene, "filter_min_vert", 0)
    max_vert = getattr(scene, "filter_max_vert", 0)
    days_old = int(getattr(scene, "filter_days_old", '0'))
    
    # Clear existing items
    scene.asset_items.clear()
    
    # Get paginated data from database
    assets, total = db_get_paginated(
        page=page,
        page_size=page_size,
        category=category,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        min_size=min_size,
        max_size=max_size,
        min_poly=min_poly,
        max_poly=max_poly,
        min_vert=min_vert,
        max_vert=max_vert,
        days_old=days_old,
        filter_favorites=filter_favorites
    )
    
    # Store pagination state in scene
    scene.asset_total_count = total
    scene.asset_current_page = page
    scene.asset_page_size = page_size
    scene.asset_total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    # Load assets to scene collection
    # Load assets to scene collection
    for a in assets:
        item = scene.asset_items.add()
        
        item.id = a["id"]
        item.uuid = a["uuid"]
        
        item.name = a.get("name") or ""
        item.category = a.get("category") or ""
        item.description = a.get("description") or ""
        
        item.file_path = a.get("file_path") or ""
        item.file_size = a.get("file_size") or 0
        
        item.poly_count = a.get("poly_count") or 0
        item.vertices = a.get("vertices") or 0
        item.faces = a.get("faces") or 0
        
        item.created_at = a.get("created_at") or ""
        item.updated_at = a.get("updated_at") or ""
        item.is_favorite = bool(a.get("is_favorite"))
        
        # PERBAIKI INI: Simpan thumbnail_path dari database, bukan key
        item.preview_icon = a.get("thumbnail_path") or ""  # Path thumbnail dari DB
    
    # Reset selection to first item
    if len(scene.asset_items) > 0:
        scene.asset_index = 0

    # PRE-LOAD previews untuk assets yang baru dimuat
    from .preview import load_previews_for_assets
    load_previews_for_assets(assets)  # assets sudah berisi data dari db_get_paginated

    return len(scene.asset_items)

# =====================================================
# SINGLE ASSET OPERATIONS (EFFICIENT)
# =====================================================

def update_single_asset_in_scene(context, asset_id):
    """
    Update a single asset in scene without reloading all.
    Much faster than load_assets_to_scene() for single updates.
    
    Args:
        context: Blender context
        asset_id (int): Asset ID to update
    
    Returns:
        bool: True if found and updated, False otherwise
    """
    scene = context.scene
    
    # Get updated data from database
    updated = db_get_by_id(asset_id)
    if not updated:
        return False
    
    # Find and update in scene
    found = False
    for item in scene.asset_items:
        if item.id == asset_id:
            # Update all fields
            item.uuid = updated.get("uuid") or ""
            item.name = updated.get("name") or ""
            item.category = updated.get("category") or ""
            item.description = updated.get("description") or ""
            item.file_path = updated.get("file_path") or ""
            item.file_size = updated.get("file_size") or 0
            item.poly_count = updated.get("poly_count") or 0
            item.vertices = updated.get("vertices") or 0
            item.faces = updated.get("faces") or 0
            item.updated_at = updated.get("updated_at") or ""
            item.is_favorite = bool(updated.get("is_favorite"))
            item.preview_icon = updated.get("thumbnail_path") or "" 
            
            # Increment version to force thumbnail refresh
            item.preview_version += 1
            
            found = True
            break
    
    return found


def add_single_asset_to_scene(context, asset_id):
    """
    Add a newly registered asset to the scene.
    Adds to beginning of list (most recent first).
    
    Args:
        context: Blender context
        asset_id (int): Asset ID to add
    
    Returns:
        bool: True if added, False otherwise
    """
    scene = context.scene
    asset = db_get_by_id(asset_id)
    
    if not asset:
        return False
    
    # Insert at beginning (most recent first)
    # Note: Blender doesn't support insert at index, so we reload
    # For production, consider maintaining sort order in UI
    item = scene.asset_items.add()
    
    item.id = asset["id"]
    item.uuid = asset["uuid"]
    item.name = asset.get("name") or ""
    item.category = asset.get("category") or ""
    item.description = asset.get("description") or ""
    item.file_path = asset.get("file_path") or ""
    item.file_size = asset.get("file_size") or 0
    item.poly_count = asset.get("poly_count") or 0
    item.vertices = asset.get("vertices") or 0
    item.faces = asset.get("faces") or 0
    item.created_at = asset.get("created_at") or ""
    item.updated_at = asset.get("updated_at") or ""
    item.is_favorite = bool(asset.get("is_favorite"))
    item.preview_icon = asset.get("thumbnail_path") or ""
    
    # Move to top (most recent)
    # Since we can't reorder, just reload the page
    load_assets_to_scene(context, page=0, force_reload=True)
    
    return True


def remove_single_asset_from_scene(context, asset_id):
    """
    Remove a single asset from scene collection.
    
    Args:
        context: Blender context
        asset_id (int): Asset ID to remove
    
    Returns:
        bool: True if removed, False if not found
    """
    scene = context.scene
    
    # Find index
    index_to_remove = -1
    for i, item in enumerate(scene.asset_items):
        if item.id == asset_id:
            index_to_remove = i
            break
    
    if index_to_remove >= 0:
        scene.asset_items.remove(index_to_remove)
        
        # Adjust selection
        if scene.asset_index >= len(scene.asset_items):
            scene.asset_index = max(0, len(scene.asset_items) - 1)
        
        # Update count
        scene.asset_total_count = getattr(scene, "asset_total_count", 0) - 1
        
        return True
    
    return False


# =====================================================
# PAGINATION HELPERS
# =====================================================

def go_to_page(context, page):
    """
    Navigate to specific page.
    
    Args:
        context: Blender context
        page (int): Target page number
    
    Returns:
        bool: True if successful
    """
    scene = context.scene
    total_pages = getattr(scene, "asset_total_pages", 0)
    
    # Validate page number
    if page < 0 or (total_pages > 0 and page >= total_pages):
        return False
    
    page_size = getattr(scene, "asset_page_size", 10)
    load_assets_to_scene(context, page=page, page_size=page_size, force_reload=True)
    
    return True


def next_page(context):
    """Go to next page."""
    scene = context.scene
    current = getattr(scene, "asset_current_page", 0)
    total_pages = getattr(scene, "asset_total_pages", 0)
    
    if current < total_pages - 1:
        return go_to_page(context, current + 1)
    
    return False


def previous_page(context):
    """Go to previous page."""
    scene = context.scene
    current = getattr(scene, "asset_current_page", 0)
    
    if current > 0:
        return go_to_page(context, current - 1)
    
    return False


def first_page(context):
    """Go to first page."""
    return go_to_page(context, 0)


def last_page(context):
    """Go to last page."""
    scene = context.scene
    total_pages = getattr(scene, "asset_total_pages", 0)
    
    if total_pages > 0:
        return go_to_page(context, total_pages - 1)
    
    return False


# =====================================================
# REFRESH & RELOAD
# =====================================================

def refresh_current_page(context):
    """
    Refresh current page (reload from database).
    Useful after external changes to database.
    """
    scene = context.scene
    current_page = getattr(scene, "asset_current_page", 0)
    page_size = getattr(scene, "asset_page_size", 10)
    
    load_assets_to_scene(context, page=current_page, page_size=page_size, force_reload=True)


def clear_scene_assets(context):
    """
    Clear all assets from scene.
    """
    scene = context.scene
    
    if hasattr(scene, "asset_items"):
        scene.asset_items.clear()
        scene.asset_index = 0
        scene.asset_total_count = 0
        scene.asset_current_page = 0
        scene.asset_total_pages = 0


# =====================================================
# FILTER CHANGE HANDLERS
# =====================================================

def on_filter_changed(context):
    """
    Called when user changes search/filter parameters.
    Reloads from page 0 with new filters.
    """
    scene = context.scene
    
    # Advanced filters are now perfectly supported by paginated loader
    page_size = getattr(scene, "asset_page_size", 10)
    load_assets_to_scene(context, page=0, page_size=page_size, force_reload=True)



# =====================================================
# PREVIEW MANAGEMENT
# =====================================================

def load_preview_for_current_selection(context):
    """
    Load preview only for currently selected asset (lazy loading).
    """
    scene = context.scene
    idx = scene.asset_index
    
    if idx < 0 or idx >= len(scene.asset_items):
        return None
    
    item = scene.asset_items[idx]
    asset = db_get_by_id(item.id)
    
    if asset:
        return load_preview_for_single_asset(asset)
    
    return None


def preload_visible_previews(context, start_idx=0, count=10):
    """
    Preload previews for visible items in UIList.
    
    Args:
        context: Blender context
        start_idx (int): Start index
        count (int): Number of previews to preload
    """
    scene = context.scene
    end_idx = min(start_idx + count, len(scene.asset_items))
    
    for i in range(start_idx, end_idx):
        item = scene.asset_items[i]
        asset = db_get_by_id(item.id)
        if asset:
            load_preview_for_single_asset(asset)


def cleanup_unused_previews(context):
    """
    Unload previews that are not in current page.
    Frees memory for large asset libraries.
    """
    scene = context.scene
    
    # Get UUIDs of current page
    current_uuids = {item.uuid for item in scene.asset_items}
    
    # This would require access to preview collection
    # Implementation depends on preview.py structure
    # For now, this is a placeholder
    pass


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def get_asset_by_index(context, index):
    """
    Get asset data by index in current scene list.
    
    Args:
        context: Blender context
        index (int): Index in asset_items
    
    Returns:
        dict or None: Asset data from database
    """
    scene = context.scene
    
    if index < 0 or index >= len(scene.asset_items):
        return None
    
    item = scene.asset_items[index]
    return db_get_by_id(item.id)


def get_selected_asset(context):
    """
    Get currently selected asset data.
    
    Returns:
        dict or None: Asset data from database
    """
    scene = context.scene
    return get_asset_by_index(context, scene.asset_index)


def count_assets_in_scene(context):
    """
    Get number of assets currently loaded in scene.
    
    Returns:
        int: Number of loaded assets
    """
    scene = context.scene
    return len(scene.asset_items) if hasattr(scene, "asset_items") else 0


def get_pagination_info(context):
    """
    Get current pagination information.
    
    Returns:
        dict: Pagination info (current_page, total_pages, etc.)
    """
    scene = context.scene
    
    return {
        'current_page': getattr(scene, "asset_current_page", 0),
        'total_pages': getattr(scene, "asset_total_pages", 0),
        'page_size': getattr(scene, "asset_page_size", 10),
        'total_count': getattr(scene, "asset_total_count", 0),
        'loaded_count': len(scene.asset_items) if hasattr(scene, "asset_items") else 0,
    }