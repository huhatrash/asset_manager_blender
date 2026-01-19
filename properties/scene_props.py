import bpy
from ..operators.load_asset import load_assets_to_scene

class AssetItem(bpy.types.PropertyGroup):
    id: bpy.props.IntProperty()
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
    preview_icon: bpy.props.StringProperty()

def init_scene_properties():
    bpy.types.Scene.asset_items = bpy.props.CollectionProperty(type=AssetItem)
    bpy.types.Scene.asset_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.show_thumbnail = bpy.props.BoolProperty(
    name="Show Thumbnail",
    default=True,
    update=lambda self, ctx: ctx.area.tag_redraw() if ctx.area else None
    )
    bpy.types.Scene.asset_index = bpy.props.IntProperty(
    default=0,
    update=lambda self, ctx: ctx.area.tag_redraw() if ctx.area else None
    )
    bpy.types.Scene.filter_min_size = bpy.props.IntProperty(
    name="Min Size (KB)",
    default=0,
    update=lambda self, ctx: load_assets_to_scene(ctx)
    )
    bpy.types.Scene.filter_max_size = bpy.props.IntProperty(
        name="Max Size (KB)",
        default=0,
        update=lambda self, ctx: load_assets_to_scene(ctx)
    )
    bpy.types.Scene.filter_min_poly = bpy.props.IntProperty(
        name="Min Poly",
        default=0,
        update=lambda self, ctx: load_assets_to_scene(ctx)
    )
    bpy.types.Scene.filter_max_poly = bpy.props.IntProperty(
        name="Max Poly",
        default=0,
        update=lambda self, ctx: load_assets_to_scene(ctx)
    )
    bpy.types.Scene.asset_search = bpy.props.StringProperty(
    name="Search",
    description="Cari asset berdasarkan nama",
    default="",
    update=lambda self, ctx: load_assets_to_scene(ctx)
    )

    bpy.types.Scene.asset_category = bpy.props.EnumProperty(
        name="Category",
        items=[
            ('ALL', "All", ""),
            ('model', "Model", ""),
            ('characters', "Characters", ""),
            ('environment', "Environment", ""),
            ('props', "Props", ""),
            ('default model', "Default Model", ""),
        ],
        default='ALL',
        update=lambda self, ctx: load_assets_to_scene(ctx)
    )
    bpy.types.Scene.show_thumbnail = bpy.props.BoolProperty(
        name="Show Thumbnail", description="Tampilkan thumbnail preview asset", default=True
    )

def clear_scene_properties():
    try:
        del bpy.types.Scene.asset_search
        del bpy.types.Scene.asset_category
        del bpy.types.Scene.show_thumbnail
    except Exception:
        pass