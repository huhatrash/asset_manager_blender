import bpy
import os
from ..core.database import db_get_by_id
from ..core.scene_assets import load_assets_to_scene

class ASSETMANAGER_OT_load_from_db(bpy.types.Operator):
    bl_idname = "assetmanager.load_from_db"
    bl_label = "Load Asset from Database"
    asset_id: bpy.props.IntProperty()

    def execute(self, context):
        rec = db_get_by_id(self.asset_id)
        if not rec:
            self.report({'WARNING'}, "Asset not found")
            return {'CANCELLED'}

        fpath = rec.get('file_path') or ""
        if not fpath or not os.path.exists(fpath):
            self.report({'WARNING'}, f"File missing: {fpath}")
            return {'CANCELLED'}

        ext = os.path.splitext(fpath)[1].lower()
        try:
            if ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=fpath)
            elif ext == '.blend':
                # append: open blend and append objects by name may need user input
                bpy.ops.wm.append(filepath=fpath)
            else:
                self.report({'WARNING'}, f"Unsupported import ext: {ext}")
                return {'CANCELLED'}
            self.report({'INFO'}, f"Imported {rec['name']} from {fpath}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}