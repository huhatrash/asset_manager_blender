import bpy

class AssetManagerPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    page_size: bpy.props.IntProperty(
        name="Assets Per Page",
        description="Number of assets to load at once",
        default=50,
        min=10,
        max=200
    )
    
    thumbnail_size: bpy.props.IntProperty(
        name="Thumbnail Size",
        description="Thumbnail resolution (pixels)",
        default=256,
        min=128,
        max=1024
    )
    
    auto_backup: bpy.props.BoolProperty(
        name="Auto Backup Database",
        description="Backup database weekly",
        default=True
    )
    
    # ✅ Export settings
    default_export_format: bpy.props.EnumProperty(
        name="Default Export Format",
        items=[
            ('FBX', 'FBX', ''),
            ('BLEND', 'BLEND', ''),
        ],
        default='FBX'
    )
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Performance Settings", icon='PREFERENCES')
        box.prop(self, "page_size")
        box.prop(self, "thumbnail_size")
        
        box = layout.box()
        box.label(text="Database", icon='FILE')
        box.prop(self, "auto_backup")
        
        box = layout.box()
        box.label(text="Export", icon='EXPORT')
        box.prop(self, "default_export_format")