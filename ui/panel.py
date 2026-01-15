import bpy

class ASSETMANAGER_PT_panel(bpy.types.Panel):
    bl_label = "3D Asset Manager"
    bl_idname = "ASSETMANAGER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'

    def draw(self, context):
        layout = self.layout
        layout.operator("assetmanager.load_assets", icon='FILE_REFRESH')
