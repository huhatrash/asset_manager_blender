import os
import bpy

class ASSETMANAGER_OT_import_local(bpy.types.Operator):
    bl_idname = "assetmanager.import_local"
    bl_label = "Import Local File"
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        ext = os.path.splitext(self.filepath)[1].lower()
        try:
            if ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=self.filepath)
            elif ext == '.obj':
                bpy.ops.import_scene.obj(filepath=self.filepath)
            elif ext == '.blend':
                # append all objects from that blend's Object folder - this may vary on structure
                directory = os.path.join(self.filepath, "Object") + os.sep
                bpy.ops.wm.append(directory=directory, filename="")
            else:
                self.report({'WARNING'}, "Unsupported file type")
                return {'CANCELLED'}
            self.report({'INFO'}, f"Imported {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}