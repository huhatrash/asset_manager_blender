import bpy

class ASSETMANAGER_OT_place_asset(bpy.types.Operator):
    bl_idname = "assetmanager.place_asset"
    bl_label = "Place Asset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        
        self.report({'INFO'}, "Invoke called")
        print("Invoke called")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ASSETMANAGER_OT_place_asset)

def unregister():
    bpy.utils.unregister_class(ASSETMANAGER_OT_place_asset)
