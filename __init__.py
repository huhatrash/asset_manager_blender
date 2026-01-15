bl_info = {
    "name": "3D Asset Manager",
    "author": "alfa haliza",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Asset Manager",
    "description": "Manage, preview, and export 3D assets using SQLite",
    "category": "3D View",
}

import bpy

from .core.paths import ensure_dirs
from .core.database import create_table

from .properties import scene_props
from .operators import load_asset
from .ui import panel

def register():
    ensure_dirs()
    create_table()

    scene_props.register()
    bpy.utils.register_class(load_asset.ASSETMANAGER_OT_load_assets)
    bpy.utils.register_class(panel.ASSETMANAGER_PT_panel)

def unregister():
    bpy.utils.unregister_class(panel.ASSETMANAGER_PT_panel)
    bpy.utils.unregister_class(load_asset.ASSETMANAGER_OT_load_assets)
    scene_props.unregister()
