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
                # Correct approach: append all objects via libraries.load
                objects_before = set(bpy.data.objects)
                with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
                    data_to.objects = data_from.objects
                scene_col = context.scene.collection
                for obj in data_to.objects:
                    if obj is not None:
                        scene_col.objects.link(obj)
                imported = [o for o in bpy.data.objects if o not in objects_before]
                if not imported:
                    self.report({'WARNING'}, "No objects found in .blend file")
                    return {'CANCELLED'}
            else:
                self.report({'WARNING'}, "Unsupported file type")
                return {'CANCELLED'}
            self.report({'INFO'}, f"Imported {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}