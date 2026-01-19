import bpy
from ..core.export_import import export_selected_to_fbx
from ..core.paths import EXPORTS_DIR

class ASSETMANAGER_OT_export_local(bpy.types.Operator):
    bl_idname = "assetmanager.export_local"
    bl_label = "Export Selected to Local (FBX)"

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object to export")
            return {'CANCELLED'}
        path = export_selected_to_fbx(obj, EXPORTS_DIR)
        self.report({'INFO'}, f"Exported to {path}")
        return {'FINISHED'}