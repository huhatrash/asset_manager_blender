import bpy


# =====================================================
# DATA MODEL (SINGLE SOURCE OF TRUTH UNTUK UI)
# =====================================================

class AssetItem(bpy.types.PropertyGroup):
    id: bpy.props.IntProperty()
    uuid: bpy.props.StringProperty()   # ⬅️ TAMBAH INI

    name: bpy.props.StringProperty()
    category: bpy.props.StringProperty()
    description: bpy.props.StringProperty()

    file_path: bpy.props.StringProperty()
    file_size: bpy.props.IntProperty()

    poly_count: bpy.props.IntProperty()
    vertices: bpy.props.IntProperty()
    faces: bpy.props.IntProperty()

    created_at: bpy.props.StringProperty()
    updated_at: bpy.props.StringProperty()

    preview_icon: bpy.props.StringProperty()  # SIMPAN KEY, BUKAN icon_id


# =====================================================
# SCENE PROPERTIES
# =====================================================

def init_scene_properties():

    bpy.types.Scene.asset_items = bpy.props.CollectionProperty(
        type=AssetItem
    )

    bpy.types.Scene.asset_index = bpy.props.IntProperty(
        default=0
    )

    bpy.types.Scene.asset_search = bpy.props.StringProperty(
        name="Search",
        description="Search asset by name",
        default=""
    )

    bpy.types.Scene.asset_category = bpy.props.EnumProperty(
        name="Category",
        items=[
            ('ALL', "All", ""),
            ('model', "Model", ""),
            ('character', "Character", ""),
            ('environment', "Environment", ""),
            ('props', "Props", ""),
        ],
        default='ALL'
    )

    bpy.types.Scene.filter_min_size = bpy.props.IntProperty(
        name="Min Size (KB)",
        default=0
    )

    bpy.types.Scene.filter_max_size = bpy.props.IntProperty(
        name="Max Size (KB)",
        default=0
    )

    bpy.types.Scene.filter_min_poly = bpy.props.IntProperty(
        name="Min Poly",
        default=0
    )

    bpy.types.Scene.filter_max_poly = bpy.props.IntProperty(
        name="Max Poly",
        default=0
    )

    bpy.types.Scene.show_thumbnail = bpy.props.BoolProperty(
        name="Show Thumbnail",
        description="Display asset thumbnail",
        default=True
    )


# =====================================================
# CLEANUP
# =====================================================

def clear_scene_properties():
    props = [
        "asset_items",
        "asset_index",
        "asset_search",
        "asset_category",
        "filter_min_size",
        "filter_max_size",
        "filter_min_poly",
        "filter_max_poly",
        "show_thumbnail",
    ]

    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)
