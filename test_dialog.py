import bpy

class ASSETMANAGER_OT_test(bpy.types.Operator):
    bl_idname = "assetmanager.testop"
    bl_label = "Test"
    
    my_prop: bpy.props.StringProperty(
        name="Test Prop", default="",
        update=lambda s, c: print(f"UPDATE RUNS: {s.my_prop}")
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
        
    def draw(self, context):
        self.layout.prop(self, "my_prop")
        
    def execute(self, context):
        return {'FINISHED'}

bpy.utils.register_class(ASSETMANAGER_OT_test)
