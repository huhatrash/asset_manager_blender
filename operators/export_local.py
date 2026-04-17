import bpy
from ..core.export_import import export_selected_to_fbx
from ..core.paths import get_exports_dir

class ASSETMANAGER_OT_export_local(bpy.types.Operator):
    bl_idname = "assetmanager.export_local"
    bl_label = "Export Selected to Local (FBX)"
    bl_description = "Export the active mesh object as FBX to the asset library"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No active MESH object to export")
            return {'CANCELLED'}
        try:
            path = export_selected_to_fbx(obj, get_exports_dir())
            if not path:
                self.report({'ERROR'}, "Export failed — file was not created")
                return {'CANCELLED'}
            self.report({'INFO'}, f"Exported to {path}")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        return {'FINISHED'}