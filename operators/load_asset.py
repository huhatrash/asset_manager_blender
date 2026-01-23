import bpy
import os

class ASSETMANAGER_OT_load_from_db(bpy.types.Operator):
    """Load asset from library into scene"""
    bl_idname = "assetmanager.load_from_db"
    bl_label = "Load Asset"
    bl_description = "Import asset file into current scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    asset_id: bpy.props.IntProperty()
    
    @classmethod
    def poll(cls, context):
        """Check if in a valid mode."""
        return context.mode == 'OBJECT'
    
    def execute(self, context):
        """Execute asset loading."""
        from ..core.database import db_get_by_id
        from ..core.export_import import import_file_auto
        
        asset = db_get_by_id(self.asset_id)
        
        if not asset:
            self.report({'WARNING'}, "Asset not found")
            return {'CANCELLED'}
        
        file_path = asset.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            self.report({'ERROR'}, f"Asset file missing: {file_path}")
            return {'CANCELLED'}
        
        try:
            # Import file
            imported_objects = import_file_auto(file_path)
            
            if not imported_objects:
                self.report({'WARNING'}, "No objects imported")
                return {'CANCELLED'}
            
            # Select imported objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in imported_objects:
                obj.select_set(True)
            
            if imported_objects:
                context.view_layer.objects.active = imported_objects[0]
            
            self.report({'INFO'}, f"Loaded '{asset['name']}' ({len(imported_objects)} object(s))")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}