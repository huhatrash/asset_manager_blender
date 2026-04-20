
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
    
    preview_version: bpy.props.IntProperty(
        name="Preview Version",
        description="Incremental version to force thumbnail refresh",
        default=0
    )
    
    # State tracking
    is_favorite: bpy.props.BoolProperty(
        name="Favorite",
        description="Is this asset marked as a favorite",
        default=False
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
    bpy.types.WindowManager.asset_items = bpy.props.CollectionProperty(
        type=AssetItem,
        name="Assets",
        description="Collection of assets in library"
    )
    
    # Selection index
    bpy.types.WindowManager.asset_index = bpy.props.IntProperty(
        name="Selected Asset",
        description="Currently selected asset index",
        default=0,
        min=0
    )
    
    # Search & Filter
    bpy.types.WindowManager.asset_search = bpy.props.StringProperty(
        name="Search",
        description="Search assets by name or description",
        default="",
        update=lambda self, context: on_search_update(context)
    )
    
    bpy.types.WindowManager.asset_category = bpy.props.EnumProperty(
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
    
    bpy.types.WindowManager.show_advanced_filters = bpy.props.BoolProperty(
        name="Show Advanced Filters",
        description="Toggle advanced filter options",
        default=False  
    )
    
    bpy.types.WindowManager.filter_favorites = bpy.props.BoolProperty(
        name="Favorites Only",
        description="Show only favorite assets",
        default=False,
        update=lambda self, context: on_filter_update(context)
    )
    
    # Advanced filters
    bpy.types.WindowManager.filter_min_size = bpy.props.IntProperty(
        name="Min Size (KB)",
        description="Minimum file size in kilobytes",
        default=0,
        min=0,
        soft_max=10000
    )
    
    bpy.types.WindowManager.filter_max_size = bpy.props.IntProperty(
        name="Max Size (KB)",
        description="Maximum file size in kilobytes (0 = no limit)",
        default=0,
        min=0,
        soft_max=100000
    )
    
    bpy.types.WindowManager.filter_min_poly = bpy.props.IntProperty(
        name="Min Polygons",
        description="Minimum polygon count",
        default=0,
        min=0,
        soft_max=100000
    )
    
    bpy.types.WindowManager.filter_max_poly = bpy.props.IntProperty(
        name="Max Polygons",
        description="Maximum polygon count (0 = no limit)",
        default=0,
        min=0,
        soft_max=10000000
    )
    
    bpy.types.WindowManager.filter_min_vert = bpy.props.IntProperty(
        name="Min Verts",
        description="Minimum vertex count",
        default=0,
        min=0,
        soft_max=100000
    )
    
    bpy.types.WindowManager.filter_max_vert = bpy.props.IntProperty(
        name="Max Verts",
        description="Maximum vertex count (0 = no limit)",
        default=0,
        min=0,
        soft_max=10000000
    )
    
    bpy.types.WindowManager.filter_days_old = bpy.props.EnumProperty(
        name="Added Last",
        description="Filter by asset creation time",
        items=[
            ('0', 'Any Time', 'Show all assets'),
            ('1', 'Today', 'Added in the last 24 hours'),
            ('7', 'Last 7 Days', 'Added in the last week'),
            ('30', 'Last 30 Days', 'Added in the last month'),
        ],
        default='0',
        update=lambda self, context: on_filter_update(context)
    )
    
    # Pagination
    bpy.types.WindowManager.asset_total_count = bpy.props.IntProperty(
        name="Total Assets",
        description="Total number of assets matching filters",
        default=0
    )
    
    bpy.types.WindowManager.asset_current_page = bpy.props.IntProperty(
        name="Current Page",
        description="Current page number (0-indexed)",
        default=0,
        min=0
    )
    
    bpy.types.WindowManager.asset_page_size = bpy.props.IntProperty(
        name="Page Size",
        description="Number of assets per page",
        default=10,
        min=10,
        max=200
    )
    
    bpy.types.WindowManager.asset_total_pages = bpy.props.IntProperty(
        name="Total Pages",
        description="Total number of pages",
        default=0,
        min=0
    )
    
    # Sorting
    bpy.types.WindowManager.asset_sort_by = bpy.props.EnumProperty(
        name="Sort By",
        description="Attribute to sort assets by",
        items=[
            ('created_at', 'Date Created', 'Sort by creation date'),
            ('updated_at', 'Date Modified', 'Sort by last update'),
            ('name', 'Name', 'Sort alphabetically'),
            ('popularity', 'Most Popular', 'Sort by usage frequency'),
            ('file_size', 'File Size', 'Sort by weight'),
            ('poly_count', 'Polygons', 'Sort by complexity'),
            ('vertices', 'Vertices', 'Sort by vertex count'),
        ],
        default='created_at',
        update=lambda self, context: on_filter_update(context)
    )
    
    bpy.types.WindowManager.asset_sort_order = bpy.props.EnumProperty(
        name="Sort Order",
        description="Direction of sorting",
        items=[
            ('ASC', 'Ascending', 'Smallest/Oldest first'),
            ('DESC', 'Descending', 'Largest/Newest first'),
        ],
        default='DESC',
        update=lambda self, context: on_filter_update(context)
    )
    
    # Display options
    bpy.types.WindowManager.show_thumbnail = bpy.props.BoolProperty(
        name="Show Thumbnails",
        description="Display asset thumbnails in preview panel",
        default=True
    )

    bpy.types.WindowManager.show_pagination_info = bpy.props.BoolProperty(
        name="Show Pagination Info",
        description="Display pagination information",
        default=True
    )


# =====================================================
# UPDATE CALLBACKS
# =====================================================

def on_search_update(context):
    """Callback when search string changes"""
    from ..core.scene_assets import load_assets_to_scene
    wm = context.window_manager
    load_assets_to_scene(context, page=0, force_reload=True)

def on_filter_update(context):
    """Callback when filters change"""
    from ..core.scene_assets import load_assets_to_scene
    wm = context.window_manager
    # Reset to page 0 when filters change
    wm.asset_current_page = 0
    load_assets_to_scene(context, page=0, force_reload=True)


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
        "show_advanced_filters",
        "filter_favorites",
        "filter_min_size",
        "filter_max_size",
        "filter_min_poly",
        "filter_max_poly",
        "filter_min_vert",
        "filter_max_vert",
        "filter_days_old",

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
        "show_pagination_info",
    ]
    
    for prop in props:
        if hasattr(bpy.types.WindowManager, prop):
            try:
                delattr(bpy.types.WindowManager, prop)
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
    wm = context.window_manager
    
    if not hasattr(wm, 'asset_items') or not hasattr(wm, 'asset_index'):
        return None
    
    idx = wm.asset_index
    
    if 0 <= idx < len(wm.asset_items):
        return wm.asset_items[idx]
    
    return None


def get_asset_count(context):
    """
    Get number of assets currently loaded.

    Args:
        context: Blender context

    Returns:
        int: Number of assets
    """
    wm = context.window_manager

    if hasattr(wm, 'asset_items'):
        return len(wm.asset_items)

    return 0