bl_info = {
    "name": "Local Asset Manager",
    "author": "alfa haliza",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "description": "Register, load, import, export, and preview local assets",
    "category": "3D View",
}

import bpy
import uuid
import os

from .operators import (
    register_asset,
    update_asset,
    delete_asset,
    load_asset,
    import_local,
    export_local,
    show_catalog,
)

from .ui.panel import ASSETMANAGER_PT_panel
from .ui.ui_list import ASSETMANAGER_UL_list
from .properties.scene_props import AssetItem, init_scene_properties, clear_scene_properties
from .core.database import create_table_if_not_exists

classes = (
    AssetItem,
    ASSETMANAGER_UL_list,
    register_asset.ASSETMANAGER_OT_register,
    load_asset.ASSETMANAGER_OT_load_from_db,
    import_local.ASSETMANAGER_OT_import_local,
    export_local.ASSETMANAGER_OT_export_local,
    delete_asset.ASSETMANAGER_OT_delete,
    update_asset.ASSETMANAGER_OT_update,
    show_catalog.ASSETMANAGER_OT_show_catalog,
    ASSETMANAGER_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

    init_scene_properties()
    create_table_if_not_exists()

def unregister():
    clear_scene_properties()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)