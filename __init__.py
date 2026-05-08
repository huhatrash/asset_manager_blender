
bl_info = {
    "name": "Local Asset Manager",
    "author": "alfa haliza",
    "version": (1, 0, 0),
    "blender": (4, 5, 3),
    "description": "Professional asset management with support for thousands of assets (Blender 4.x - 5.x)",
    "category": "3D View",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.app.handlers import persistent


# =====================================================
# IMPORT MODULES
# =====================================================

# Core modules
from .core import database, paths
from .core.database import init_db, db_get_paginated
from .core.scene_assets import load_assets_to_scene
from .core.preview import load_preview_for_single_asset, clear_previews
from .core.paths import init_directories

# Properties
from .properties.scene_props import (
    AssetItem,
    init_scene_properties,
    clear_scene_properties,
)

# Operators
from .operators import (
    register_asset,
    edit_metadata,
    update_source,
    delete_asset,
    load_asset,
    import_local,
    show_catalog,
    pagination_operators,
    toggle_favorite,
    batch_operations,
    maintenance,
)

# UI
from .ui.panel import (
    ASSETMANAGER_PT_panel,
    ASSETMANAGER_PT_browse,
    ASSETMANAGER_PT_details,
    ASSETMANAGER_PT_filters,
    ASSETMANAGER_PT_management,
    ASSETMANAGER_PT_recently_used,
    ASSETMANAGER_PT_maintenance,
)
from .ui.ui_list import ASSETMANAGER_UL_list


# =====================================================
# CLASSES TO REGISTER
# =====================================================

classes = (
    # Properties
    AssetItem,
    
    # UI List
    ASSETMANAGER_UL_list,
    
    # Main Operators
    register_asset.ASSETMANAGER_OT_register,
    edit_metadata.ASSETMANAGER_OT_edit_metadata,
    update_source.ASSETMANAGER_OT_update_source,
    delete_asset.ASSETMANAGER_OT_delete,
    load_asset.ASSETMANAGER_OT_load_from_db,
    load_asset.ASSETMANAGER_OT_load_from_db_deferred,
    import_local.ASSETMANAGER_OT_import_local,
    show_catalog.ASSETMANAGER_OT_show_catalog,
    show_catalog.ASSETMANAGER_OT_catalog_refresh,
    show_catalog.ASSETMANAGER_OT_catalog_goto_page,
    show_catalog.ASSETMANAGER_OT_catalog_first_page,
    show_catalog.ASSETMANAGER_OT_catalog_prev_page,
    show_catalog.ASSETMANAGER_OT_catalog_next_page,
    show_catalog.ASSETMANAGER_OT_catalog_last_page,
    
    # Toggle Favorite
    toggle_favorite.ASSETMANAGER_OT_toggle_favorite,

    # Batch Operations
    batch_operations.ASSETMANAGER_OT_batch_toggle_select,
    batch_operations.ASSETMANAGER_OT_batch_select_all,
    batch_operations.ASSETMANAGER_OT_batch_clear_selection,
    batch_operations.ASSETMANAGER_OT_batch_load,
    batch_operations.ASSETMANAGER_OT_batch_export,
    batch_operations.ASSETMANAGER_OT_batch_delete,
    
    # Pagination Operators
    pagination_operators.ASSETMANAGER_OT_next_page,
    pagination_operators.ASSETMANAGER_OT_previous_page,
    pagination_operators.ASSETMANAGER_OT_first_page,
    pagination_operators.ASSETMANAGER_OT_last_page,
    pagination_operators.ASSETMANAGER_OT_go_to_page,
    pagination_operators.ASSETMANAGER_OT_apply_filters,
    pagination_operators.ASSETMANAGER_OT_clear_filters,
    pagination_operators.ASSETMANAGER_OT_refresh_assets,
    pagination_operators.ASSETMANAGER_OT_change_page_size,
    pagination_operators.ASSETMANAGER_OT_change_sort,
    pagination_operators.ASSETMANAGER_OT_show_statistics,
    
    # Maintenance
    maintenance.ASSETMANAGER_OT_trim_history,
    maintenance.ASSETMANAGER_OT_cleanup_orphans,
    maintenance.ASSETMANAGER_OT_optimize_db,
    
    # Panels
    ASSETMANAGER_PT_panel,
    ASSETMANAGER_PT_management,
    ASSETMANAGER_PT_browse,
    ASSETMANAGER_PT_details,
    ASSETMANAGER_PT_filters,
    ASSETMANAGER_PT_recently_used,
    ASSETMANAGER_PT_maintenance,
)


# =====================================================
# SCENE CHANGE DETECTION
# =====================================================

_last_scene = None

@persistent
def assetmanager_scene_update(scene, depsgraph=None):
    """Detect scene change and force UI refresh."""
    global _last_scene
    
    # We only care about the current window's scene
    current_scene = bpy.context.scene
    if current_scene != _last_scene:
        _last_scene = current_scene
        
        # Force a redraw of all 3D View areas to update the Asset Manager panel
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    
        # Optional: Reload assets if the list is empty (e.g. fresh startup/new scene)
        wm = bpy.context.window_manager
        if hasattr(wm, "asset_items") and len(wm.asset_items) == 0:
             bpy.app.timers.register(load_assets_delayed, first_interval=0.1)


# =====================================================
# STARTUP HANDLER
# =====================================================

@persistent
def assetmanager_on_load(dummy):
    """
    Handler called when Blender file is loaded.
    Loads assets into UI with pagination.
    """
    try:
        wm = getattr(bpy.context, "window_manager", None) or (bpy.data.window_managers[0] if hasattr(bpy.data, "window_managers") and bpy.data.window_managers else None)
        
        if not wm:
            return
        
        # Create dummy context
        class DummyContext:
            pass
        
        ctx = DummyContext()
        ctx.window_manager = wm
        ctx.scene = getattr(bpy.context, "scene", bpy.data.scenes[0] if bpy.data.scenes else None)
        
        # Get page size from global WM props
        page_size = getattr(wm, "asset_page_size", 10)
        
        # Load first page of assets
        load_assets_to_scene(ctx, page=0, page_size=page_size, force_reload=True)
        
    except Exception as e:
        print(f"[AssetManager] Startup load error: {e}")

def load_assets_delayed():
    """Delayed asset loading to ensure context is ready."""
    try:
        assetmanager_on_load(None)
    except Exception as e:
        print(f"[AssetManager] Delayed load error: {e}")
    return None  # Don't repeat timer


# =====================================================
# REGISTER
# =====================================================

def register():
    """Register addon classes and initialize."""
    print("[AssetManager] Registering addon...")
    
    # Register all classes
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[AssetManager] Failed to register {cls}: {e}")
    
    # Initialize directories (bpy is ready here — safe to call)
    init_directories()
    
    # Cleanup temp files now that bpy is ready
    try:
        from .core.paths import cleanup_temp_files
        cleanup_temp_files()
    except Exception as e:
        print(f"[AssetManager] Temp cleanup warning: {e}")
    
    # Initialize scene properties
    init_scene_properties()
    
    # Initialize database (migration-safe)
    init_db()
    
    # Quick integrity check on startup (prints warnings, does not block)
    try:
        from .core.database import db_check_integrity
        report = db_check_integrity()
        if not report.get('ok'):
            print(f"[AssetManager] ⚠️  DB integrity issue: {report.get('integrity')}")
        orphans = report.get('orphaned_files', [])
        if orphans:
            print(f"[AssetManager] ⚠️  {len(orphans)} assets have missing export files: "
                  f"{[o['name'] for o in orphans]}")
        print(f"[AssetManager] DB check: {report.get('total_assets', 0)} assets, integrity={report.get('integrity')}")
    except Exception as e:
        print(f"[AssetManager] DB check warning: {e}")
    
    # Register handler for file load
    if assetmanager_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(assetmanager_on_load)
    
    # Register handler for scene change / updates
    if assetmanager_scene_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(assetmanager_scene_update)
    
    # Load assets with delay to avoid context issues
    try:
        bpy.app.timers.register(load_assets_delayed, first_interval=0.1)
    except Exception as e:
        print(f"[AssetManager] Failed to schedule delayed load: {e}")
    
    print("[AssetManager] Addon registered successfully")


# =====================================================
# UNREGISTER
# =====================================================

def unregister():
    """Unregister addon and cleanup."""
    print("[AssetManager] Unregistering addon...")
    
    # Remove handlers
    if assetmanager_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(assetmanager_on_load)
    
    if assetmanager_scene_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(assetmanager_scene_update)
    
    # Clear preview cache
    clear_previews()
    
    # Clear scene properties
    clear_scene_properties()
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[AssetManager] Failed to unregister {cls}: {e}")
    
    print("[AssetManager] Addon unregistered successfully")


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    register()