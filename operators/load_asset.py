import bpy
from ..core import database, preview

class ASSETMANAGER_OT_load_assets(bpy.types.Operator):
    bl_idname = "assetmanager.load_assets"
    bl_label = "Load Assets"

    def execute(self, context):
        scene = context.scene
        scene.asset_items.clear()

        assets = database.get_all()
        previews = preview.load_previews(assets)

        for a in assets:
            item = scene.asset_items.add()
            item.id = a["id"]
            item.name = a["name"]
            item.category = a["category"]
            item.description = a["description"]
            item.file_path = a["file_path"]
            item.preview_icon = f"asset_{a['id']}"

        return {'FINISHED'}
