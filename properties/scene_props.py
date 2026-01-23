
import bpy


# =====================================================
# ASSET ITEM (SINGLE ASSET DATA)
# =====================================================

class AssetItem(bpy.types.PropertyGroup):
    """
    Single asset data structure.
    Represents one asset in the scene collection.
    """
    # Database ID
    id: bpy.props.IntProperty(
        name="ID",
        description="Database ID",
        default=0
    )
    
    uuid: bpy.props.StringProperty(
        name="UUID",
        description="Unique identifier",
        default=""
    )
    
    # Metadata
    name: bpy.props.StringProperty(
        name="Name",
        description="Asset name",
        default=""
    )
    
    category: bpy.props.StringProperty(
        name="Category",
        description="Asset category",
        default="model"
    )
    
    description: bpy.props.StringProperty(
        name="Description",
        description="Asset description",
        default=""
    )
    
    # File information
    file_path: bpy.props.StringProperty(
        name="File Path",
        description="Path to asset file",
        default="",
        subtype='FILE_PATH'
    )
    
    file_size: bpy.props.IntProperty(
        name="File Size",
        description="File size in bytes",
        default=0,
        subtype='UNSIGNED'
    )
    
    # Geometry statistics
    poly_count: bpy.props.IntProperty(
        name="Polygon Count",
        description="Number of polygons",
        default=0,
        subtype='UNSIGNED'
    )
    
    vertices: bpy.props.IntProperty(
        name="Vertices",
        description="Number of vertices",
        default=0,
        subtype='UNSIGNED'
    )
    
    faces: bpy.props.IntProperty(
        name="Faces",
        description="Number of faces",
        default=0,
        subtype='UNSIGNED'
    )
    
    # Timestamps
    created_at: bpy.props.StringProperty(
        name="Created At",
        description="Creation timestamp",
        default=""
    )
    
    updated_at: bpy.props.StringProperty(
        name="Updated At",
        description="Last update timestamp",
        default=""
    )
    
    # Preview
    preview_icon: bpy.props.StringProperty(
        name="Preview Icon",
        description="Preview collection key",
        default=""
    )


# =====================================================
# SCENE PROPERTIES INITIALIZATION
# =====================================================

def init_scene_properties():
    """
    Initialize all scene-level properties.
    Called on addon registration.
    """
    # Asset collection
    bpy.types.Scene.asset_items = bpy.props.CollectionProperty(
        type=AssetItem,
        name="Assets",
        description="Collection of assets in library"
    )
    
    # Selection index
    bpy.types.Scene.asset_index = bpy.props.IntProperty(
        name="Selected Asset",
        description="Currently selected asset index",
        default=0,
        min=0
    )
    
    # Search & Filter
    bpy.types.Scene.asset_search = bpy.props.StringProperty(
        name="Search",
        description="Search assets by name or description",
        default="",
        update=lambda self, context: on_search_update(context)
    )
    
    bpy.types.Scene.asset_category = bpy.props.EnumProperty(
        name="Category",
        description="Filter by category",
        items=[
            ('ALL', "All Categories", "Show all assets"),
            ('model', "Model", "3D models"),
            ('character', "Character", "Characters and creatures"),
            ('environment', "Environment", "Environment pieces"),
            ('props', "Props", "Prop objects"),
        ],
        default='ALL',
        update=lambda self, context: on_filter_update(context)
    )
    
    # Advanced filters
    bpy.types.Scene.filter_min_size = bpy.props.IntProperty(
        name="Min Size (KB)",
        description="Minimum file size in kilobytes",
        default=0,
        min=0,
        soft_max=10000
    )
    
    bpy.types.Scene.filter_max_size = bpy.props.IntProperty(
        name="Max Size (KB)",
        description="Maximum file size in kilobytes (0 = no limit)",
        default=0,
        min=0,
        soft_max=100000
    )
    
    bpy.types.Scene.filter_min_poly = bpy.props.IntProperty(
        name="Min Polygons",
        description="Minimum polygon count",
        default=0,
        min=0,
        soft_max=100000
    )
    
    bpy.types.Scene.filter_max_poly = bpy.props.IntProperty(
        name="Max Polygons",
        description="Maximum polygon count (0 = no limit)",
        default=0,
        min=0,
        soft_max=10000000
    )
    
    # Pagination
    bpy.types.Scene.asset_total_count = bpy.props.IntProperty(
        name="Total Assets",
        description="Total number of assets matching filters",
        default=0
    )
    
    bpy.types.Scene.asset_current_page = bpy.props.IntProperty(
        name="Current Page",
        description="Current page number (0-indexed)",
        default=0,
        min=0
    )
    
    bpy.types.Scene.asset_page_size = bpy.props.IntProperty(
        name="Page Size",
        description="Number of assets per page",
        default=50,
        min=10,
        max=200
    )
    
    bpy.types.Scene.asset_total_pages = bpy.props.IntProperty(
        name="Total Pages",
        description="Total number of pages",
        default=0,
        min=0
    )
    
    # Sorting
    bpy.types.Scene.asset_sort_by = bpy.props.StringProperty(
        name="Sort By",
        description="Column to sort by",
        default='created_at'
    )
    
    bpy.types.Scene.asset_sort_order = bpy.props.StringProperty(
        name="Sort Order",
        description="Sort order (ASC or DESC)",
        default='DESC'
    )
    
    # Display options
    bpy.types.Scene.show_thumbnail = bpy.props.BoolProperty(
        name="Show Thumbnails",
        description="Display asset thumbnails in preview panel",
        default=True
    )


# =====================================================
# UPDATE CALLBACKS
# =====================================================

def on_search_update(context):
    """Called when search text changes."""
    # Trigger filter update with small delay to avoid lag during typing
    # In production, consider debouncing this
    from ..core.scene_assets import on_filter_changed
    on_filter_changed(context)


def on_filter_update(context):
    """Called when filter changes."""
    from ..core.scene_assets import on_filter_changed
    on_filter_changed(context)


# =====================================================
# CLEANUP
# =====================================================

def clear_scene_properties():
    """
    Remove all scene properties.
    Called on addon unregistration.
    """
    props = [
        # Collections
        "asset_items",
        
        # Selection
        "asset_index",
        
        # Search & Filter
        "asset_search",
        "asset_category",
        "filter_min_size",
        "filter_max_size",
        "filter_min_poly",
        "filter_max_poly",
        
        # Pagination
        "asset_total_count",
        "asset_current_page",
        "asset_page_size",
        "asset_total_pages",
        
        # Sorting
        "asset_sort_by",
        "asset_sort_order",
        
        # Display
        "show_thumbnail",
    ]
    
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            try:
                delattr(bpy.types.Scene, prop)
            except Exception as e:
                print(f"[AssetManager] Failed to delete property {prop}: {e}")


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def get_selected_asset(context):
    """
    Get currently selected asset data.
    
    Args:
        context: Blender context
    
    Returns:
        AssetItem or None: Selected asset or None
    """
    scene = context.scene
    
    if not hasattr(scene, 'asset_items') or not hasattr(scene, 'asset_index'):
        return None
    
    idx = scene.asset_index
    
    if 0 <= idx < len(scene.asset_items):
        return scene.asset_items[idx]
    
    return None


def get_asset_count(context):
    """
    Get number of assets currently loaded.
    
    Args:
        context: Blender context
    
    Returns:
        int: Number of assets
    """
    scene = context.scene
    
    if hasattr(scene, 'asset_items'):
        return len(scene.asset_items)
    
    return 0