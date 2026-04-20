import os
import bpy

class ASSETMANAGER_OT_import_local(bpy.types.Operator):
    bl_idname = "assetmanager.import_local"
    bl_label = "Import Local File"
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        from ..core.export_import import import_file_auto
        
        try:
            imported_objects = import_file_auto(self.filepath)
            
            if imported_objects:
                self.report({'INFO'}, f"Imported {len(imported_objects)} objects from {os.path.basename(self.filepath)}")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "Import failed or no objects found")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Import error: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}