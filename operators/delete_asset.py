import bpy
import os
from ..core.database import db_get_by_id, db_delete_by_id
from ..core.scene_assets import load_assets_to_scene

class ASSETMANAGER_OT_delete(bpy.types.Operator):
    bl_idname = "assetmanager.delete"
    bl_label = "Delete Asset from DB"
    asset_id: bpy.props.IntProperty()

    def execute(self, context):
        rec = db_get_by_id(self.asset_id)
        if rec:
            try:
                db_delete_by_id(self.asset_id)
                # optionally delete files
                t = rec.get('thumbnail_path')
                f = rec.get('file_path')
                try:
                    if t and os.path.exists(t):
                        os.remove(t)
                    if f and os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass
                
                load_assets_to_scene(context)
                
                self.report({'INFO'}, f"Deleted asset '{rec['name']}'")
            except Exception as e:
                self.report({'ERROR'}, f"DB delete error: {e}")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "Asset not found")
            return {'CANCELLED'}
        return {'FINISHED'}
