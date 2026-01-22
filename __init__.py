bl_info = {
    "name": "Local Asset Manager",
    "author": "alfa haliza",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "description": "Register, load, import, export, and preview local assets",
    "category": "3D View",
}

import bpy
from bpy.app.handlers import persistent


# ==============================
# IMPORT MODULE
# ==============================

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

from .properties.scene_props import (
    AssetItem,
    init_scene_properties,
    clear_scene_properties,
)

from .core.database import init_db, db_get_all
from .core.scene_assets import load_assets_to_scene
from .core.preview import load_previews_for_assets, clear_previews


# ==============================
# CLASSES
# ==============================

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


# ==============================
# STARTUP HANDLER
# ==============================

@persistent
def assetmanager_on_load(dummy):

    try:

        wm = bpy.context.window_manager
        win = bpy.context.window

        if not win:
            return

        scene = win.scene

        if not scene:
            return

        class DummyContext:
            pass

        ctx = DummyContext()
        ctx.scene = scene

        # Reload assets
        load_assets_to_scene(ctx)

        # Reload previews
        assets = db_get_all()
        load_previews_for_assets(assets)

        print("[AssetManager] Assets reloaded")

    except Exception as e:
        print("[AssetManager] Load error:", e)

# ==============================
# REGISTER
# ==============================

def register():

    # Register classes
    for c in classes:
        bpy.utils.register_class(c)

    # Init Scene
    init_scene_properties()

    # Init DB
    init_db()

    # Load assets immediately
    assetmanager_on_load(None)

    # Register handler
    if assetmanager_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(assetmanager_on_load)


# ==============================
# UNREGISTER
# ==============================

def unregister():

    # Remove handler
    if assetmanager_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(assetmanager_on_load)

    # Clear preview cache
    clear_previews()

    # Clear Scene props
    clear_scene_properties()

    # Unregister classes
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
