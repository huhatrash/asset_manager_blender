import bpy

class AssetItem(bpy.types.PropertyGroup):
    id: bpy.props.IntProperty()
    name: bpy.props.StringProperty()
    category: bpy.props.StringProperty()
    description: bpy.props.StringProperty()
    file_path: bpy.props.StringProperty()
    preview_icon: bpy.props.StringProperty()

def register():
    bpy.utils.register_class(AssetItem)

    bpy.types.Scene.asset_items = bpy.props.CollectionProperty(type=AssetItem)
    bpy.types.Scene.asset_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.asset_search = bpy.props.StringProperty()

def unregister():
    del bpy.types.Scene.asset_items
    del bpy.types.Scene.asset_index
    del bpy.types.Scene.asset_search
    bpy.utils.unregister_class(AssetItem)
