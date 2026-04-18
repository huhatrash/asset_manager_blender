import bpy
import os

from ..core.database import db_get_by_id, db_update_asset
from ..core.export_import import export_selected_with_textures
from ..core.thumbnail import render_thumbnail_for_object
from ..core.paths import get_exports_dir, get_thumbnails_dir
from ..core.scene_assets import update_single_asset_in_scene
from ..core.preview import unload_preview, load_preview_for_single_asset


class ASSETMANAGER_OT_update_source(bpy.types.Operator):
    """Replace Asset Geometry and Thumbnail with Current Selection"""
    bl_idname = "assetmanager.update_source"
    bl_label = "Update Source"
    bl_description = "Instantly replace asset file and regenerate thumbnail with current selection"
    bl_options = {'REGISTER', 'UNDO'}

    # Asset ID to update
    asset_id: bpy.props.IntProperty()

    # =====================================================
    # POLL
    # =====================================================

    @classmethod
    def poll(cls, context):
        """Check if operator can run - Must have an active, selected MESH object."""
        obj = context.active_object
        return (obj is not None and 
                obj.type == 'MESH' and 
                obj.select_get())

    # =====================================================
    # EXECUTE (No Invoke Dialog)
    # =====================================================

    def execute(self, context):
        """Instantly update the asset file and thumbnail."""
        obj = context.active_object
        
        # Validation
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a MESH object to update from")
            return {'CANCELLED'}
            
        # Get current asset data
        asset = db_get_by_id(self.asset_id)
        if not asset:
            self.report({'ERROR'}, "Asset not found")
            return {'CANCELLED'}

        try:
            update_data = {}
            
            # --- 1) OVERWRITE FILE ---
            self.report({'INFO'}, "Re-exporting asset file...")
            new_file_path = self._update_asset_file(obj, asset)
            
            if new_file_path:
                update_data['file_path'] = new_file_path
                update_data['file_size'] = os.path.getsize(new_file_path)
                
                # Update geometry stats
                stats = self._calculate_geometry_stats(obj)
                update_data.update(stats)
            else:
                self.report({'WARNING'}, "File export failed")
                return {'CANCELLED'}
                
            # --- 2) REGENERATE THUMBNAIL ---
            self.report({'INFO'}, "Regenerating thumbnail...")
            new_thumb_path = self._update_thumbnail(obj, asset)
            
            if new_thumb_path:
                update_data['thumbnail_path'] = new_thumb_path
            else:
                self.report({'WARNING'}, "Thumbnail generation failed")
            
            # --- 3) SAVE DATABASE & SYNC ---
            success = db_update_asset(self.asset_id, **update_data)
            if not success:
                raise RuntimeError("Database update failed")
            
            # Sync to scene UI list
            update_single_asset_in_scene(context, self.asset_id)
            
            # --- 4) FORCE THUMBNAIL REFRESH ---
            updated_asset = db_get_by_id(self.asset_id)
            if updated_asset:
                load_preview_for_single_asset(updated_asset, force_reload=True)
            
            # --- 5) REDRAW INTERFACE ---
            # Refresh 3D View and other areas
            if context.screen:
                for area in context.screen.areas:
                    area.tag_redraw()
            
            # One shot timer for late-bound redraw (optional, safer)
            bpy.app.timers.register(self._delayed_refresh, first_interval=0.2)
            
            self.report({'INFO'}, f"Asset '{asset.get('name')}' source updated successfully")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Update failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _delayed_refresh(self):
        """Delayed refresh to ensure UI is updated"""
        try:
            # Safe access to context
            ctx = bpy.context
            if not ctx or not ctx.screen:
                return None
            
            for area in ctx.screen.areas:
                if area:
                    area.tag_redraw()
        except Exception:
            pass
        return None

    def _update_asset_file(self, obj, asset):
        """Re-export asset file without prompts."""
        old_file_path = asset.get('file_path')
        
        if old_file_path:
            ext = os.path.splitext(old_file_path)[1].lower()
            if ext == '.fbx':
                file_format = 'FBX'
            elif ext == '.blend':
                file_format = 'BLEND'
            else:
                file_format = 'FBX' 
        else:
            file_format = 'FBX'
            
        uuid = asset.get('uuid')
        exports_dir = get_exports_dir()
        
        # Delete old file
        if old_file_path and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                print(f"[AssetManager] Failed to delete old file: {e}")
                
        # Export new
        new_file_path = export_selected_with_textures(
            obj,
            exports_dir,
            file_format=file_format,
            force_name=uuid
        )
        return new_file_path

    def _update_thumbnail(self, obj, asset):
        """Regenerate thumbnail without prompts."""
        thumbnail_path = asset.get('thumbnail_path')
        
        if not thumbnail_path:
            uuid = asset.get('uuid')
            thumbnail_path = os.path.join(get_thumbnails_dir(), f"{uuid}.png")
            
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                print(f"[AssetManager] Failed to delete old thumbnail: {e}")
                
        # Render
        success = render_thumbnail_for_object(
            obj,
            thumbnail_path,
            size=(256, 256),
            samples=32
        )
        
        if success and os.path.exists(thumbnail_path):
            return thumbnail_path
        return None

    def _calculate_geometry_stats(self, obj):
        """Calculate geometry statistics."""
        mesh = obj.data
        return {
            'poly_count': len(mesh.polygons),
            'vertices': len(mesh.vertices),
            'faces': len(mesh.polygons)
        }
