import bpy
import os

# =====================================================
# DELETE ASSET OPERATOR
# =====================================================

class ASSETMANAGER_OT_delete(bpy.types.Operator):
    """Delete asset from library"""
    bl_idname = "assetmanager.delete"
    bl_label = "Delete Asset"
    bl_description = "Remove asset from library and delete files"
    bl_options = {'REGISTER', 'UNDO'}
    
    asset_id: bpy.props.IntProperty()
    
    delete_files: bpy.props.BoolProperty(
        name="Delete Files",
        description="Also delete asset files from disk",
        default=True
    )
    
    def invoke(self, context, event):
        """Show confirmation dialog."""
        from ..core.database import db_get_by_id
        
        asset = db_get_by_id(self.asset_id)
        if not asset:
            self.report({'ERROR'}, "Asset not found")
            return {'CANCELLED'}
        
        # Show confirmation
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        """Draw confirmation dialog."""
        layout = self.layout
        
        from ..core.database import db_get_by_id
        asset = db_get_by_id(self.asset_id)
        
        if asset:
            layout.label(text=f"Delete '{asset['name']}'?", icon='ERROR')
            layout.prop(self, "delete_files")
            layout.label(text="This action cannot be undone!", icon='INFO')
    
    def execute(self, context):
        """Execute deletion."""
        from ..core.database import db_get_by_id, db_delete_by_id
        from ..core.scene_assets import remove_single_asset_from_scene
        from ..core.preview import unload_preview
        
        asset = db_get_by_id(self.asset_id)
        if not asset:
            self.report({'WARNING'}, "Asset not found")
            return {'CANCELLED'}
        
        asset_name = asset['name']
        
        try:
            # Delete from database first
            db_delete_by_id(self.asset_id)
            
            # Delete files if requested
            files_deleted = []
            files_failed = []
            
            if self.delete_files:
                thumbnail_path = asset.get('thumbnail_path')
                file_path = asset.get('file_path')
                
                for path in [thumbnail_path, file_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                            files_deleted.append(os.path.basename(path))
                        except Exception as e:
                            files_failed.append(os.path.basename(path))
                            print(f"[AssetManager] Failed to delete {path}: {e}")
            
            # Remove from UI
            remove_single_asset_from_scene(context, self.asset_id)
            
            # Unload preview (pass full asset for versioned key parsing)
            unload_preview(asset)
            
            # Report result
            msg = f"Deleted asset '{asset_name}'"
            if files_deleted:
                msg += f" ({len(files_deleted)} file(s) deleted)"
            if files_failed:
                msg += f" ({len(files_failed)} file(s) failed to delete)"
            
            self.report({'INFO'}, msg)
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Delete failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}