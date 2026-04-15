import bpy
from ..core.export_import import export_selected_to_fbx
from ..core.paths import get_exports_dir

class ASSETMANAGER_OT_export_local(bpy.types.Operator):
    bl_idname = "assetmanager.export_local"
    bl_label = "Export Selected to Local (FBX)"

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object to export")
            return {'CANCELLED'}
        path = export_selected_to_fbx(obj, get_exports_dir())
        self.report({'INFO'}, f"Exported to {path}")
        return {'FINISHED'}