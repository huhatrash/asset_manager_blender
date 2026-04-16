import bpy

class SimpleOperator(bpy.types.Operator):
    bl_idname = "object.simple_operator"
    bl_label = "Simple Operator"
    
    def execute(self, context):
        return {'FINISHED'}

class SimplePanel(bpy.types.Panel):
    bl_label = "Simple Panel"
    bl_idname = "OBJECT_PT_simple_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tests'

    def draw(self, context):
        layout = self.layout
        try:
            layout.operator("object.simple_operator", depress=True)
            print("DEPRESS WORKS")
        except Exception as e:
            print("DEPRESS FAILED", e)

bpy.utils.register_class(SimpleOperator)
bpy.utils.register_class(SimplePanel)

print("REGISTERED")
