"""
Update Asset Operator - Asset Manager
Handles updating existing assets.

Author: alfa haliza
Version: 2.0 (Fixed)
"""

import bpy
import os

from ..core.database import db_get_by_id, db_update_asset
from ..core.export_import import export_selected_with_textures
from ..core.thumbnail import render_thumbnail_for_object, regenerate_thumbnail
from ..core.paths import get_exports_dir
from ..core.scene_assets import update_single_asset_in_scene
from ..core.preview import reload_preview


class ASSETMANAGER_OT_update(bpy.types.Operator):
    """Update existing asset metadata and files"""
    bl_idname = "assetmanager.update"
    bl_label = "Update Asset"
    bl_description = "Update asset metadata, regenerate file and thumbnail"
    bl_options = {'REGISTER', 'UNDO'}

    # Asset ID to update
    asset_id: bpy.props.IntProperty()
    
    # Editable properties
    name: bpy.props.StringProperty(
        name="Name",
        description="Asset name"
    )
    
    category: bpy.props.EnumProperty(
        name="Category",
        description="Asset category",
        items=[
            ('model', 'Model', 'Generic 3D model'),
            ('character', 'Character', 'Character or creature'),
            ('environment', 'Environment', 'Environment piece'),
            ('props', 'Props', 'Prop object'),
        ],
        default='model'
    )
    
    description: bpy.props.StringProperty(
        name="Description",
        description="Asset description"
    )
    
    update_file: bpy.props.BoolProperty(
        name="Re-export File",
        description="Export selected object and replace asset file",
        default=True
    )
    
    update_thumbnail: bpy.props.BoolProperty(
        name="Regenerate Thumbnail",
        description="Render new thumbnail preview",
        default=True
    )

    # =====================================================
    # POLL
    # =====================================================

    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    # =====================================================
    # INVOKE
    # =====================================================

    def invoke(self, context, event):
        """Load current asset data and show dialog."""
        asset = db_get_by_id(self.asset_id)
        
        if not asset:
            self.report({'ERROR'}, "Asset not found in database")
            return {'CANCELLED'}

        # Load current values
        self.name = asset.get("name", "")
        self.category = asset.get("category", "model")
        self.description = asset.get("description", "")
        
        return context.window_manager.invoke_props_dialog(self, width=400)

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, context):
        """Draw operator properties."""
        layout = self.layout
        
        # Metadata
        box = layout.box()
        box.label(text="Metadata", icon='FILE_TEXT')
        box.prop(self, "name")
        box.prop(self, "category")
        box.prop(self, "description")
        
        # Update options
        box = layout.box()
        box.label(text="Update Options", icon='FILE_REFRESH')
        box.prop(self, "update_file")
        box.prop(self, "update_thumbnail")
        
        # Warning
        if self.update_file:
            box.label(text="⚠ Old file will be replaced", icon='ERROR')

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, context):
        """Main execution logic."""
        obj = context.active_object
        
        # Validation
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a MESH object to update from")
            return {'CANCELLED'}
        
        if not self.name.strip():
            self.report({'ERROR'}, "Asset name cannot be empty")
            return {'CANCELLED'}
        
        # Get current asset data
        asset = db_get_by_id(self.asset_id)
        if not asset:
            self.report({'ERROR'}, "Asset not found")
            return {'CANCELLED'}

        try:
            # Prepare update data
            update_data = {
                'name': self.name.strip(),
                'category': self.category,
                'description': self.description.strip(),
            }
            
            # Update file if requested
            if self.update_file:
                self.report({'INFO'}, "Re-exporting asset file...")
                new_file_path = self._update_asset_file(obj, asset)
                
                if new_file_path:
                    update_data['file_path'] = new_file_path
                    update_data['file_size'] = os.path.getsize(new_file_path)
                    
                    # Update geometry stats
                    stats = self._calculate_geometry_stats(obj)
                    update_data.update(stats)
                else:
                    self.report({'WARNING'}, "File export failed, keeping old file")
            
            # Update thumbnail if requested
            if self.update_thumbnail:
                self.report({'INFO'}, "Regenerating thumbnail...")
                new_thumb_path = self._update_thumbnail(obj, asset)
                
                if new_thumb_path:
                    update_data['thumbnail_path'] = new_thumb_path
                    
                    # Reload preview in UI
                    reload_preview(asset)
                else:
                    self.report({'WARNING'}, "Thumbnail generation failed, keeping old thumbnail")
            
            # Save to database
            success = db_update_asset(self.asset_id, **update_data)
            
            if not success:
                raise RuntimeError("Database update failed")
            
            # Update UI
            update_single_asset_in_scene(context, self.asset_id)
            
            # Refresh area
            if context.area:
                context.area.tag_redraw()
            
            self.report({'INFO'}, f"Asset '{self.name}' updated successfully")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Update failed: {str(e)}")
            
            # Log error
            import traceback
            print(f"[AssetManager] Update error:")
            traceback.print_exc()
            
            return {'CANCELLED'}

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _update_asset_file(self, obj, asset):
        """
        Re-export asset file.
        
        Args:
            obj: Object to export
            asset: Current asset data
        
        Returns:
            str: Path to new file, or None if failed
        """
        old_file_path = asset.get('file_path')
        
        # Determine format from old file
        if old_file_path:
            ext = os.path.splitext(old_file_path)[1].lower()
            if ext == '.fbx':
                file_format = 'FBX'
            elif ext == '.blend':
                file_format = 'BLEND'
            else:
                file_format = 'FBX'  # Default
        else:
            file_format = 'FBX'
        
        # Export with same UUID (overwrite)
        uuid = asset.get('uuid')
        exports_dir = get_exports_dir()
        
        # Delete old file first
        if old_file_path and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                print(f"[AssetManager] Failed to delete old file: {e}")
        
        # Export new file
        new_file_path = export_selected_with_textures(
            obj,
            exports_dir,
            file_format=file_format,
            force_name=uuid
        )
        
        return new_file_path

    def _update_thumbnail(self, obj, asset):
        """
        Regenerate thumbnail.
        
        Args:
            obj: Object to render
            asset: Current asset data
        
        Returns:
            str: Path to thumbnail, or None if failed
        """
        thumbnail_path = asset.get('thumbnail_path')
        
        if not thumbnail_path:
            # Create new thumbnail path
            from ..core.paths import get_thumbnails_dir
            uuid = asset.get('uuid')
            thumbnail_path = os.path.join(get_thumbnails_dir(), f"{uuid}.png")
        
        # Delete old thumbnail
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                print(f"[AssetManager] Failed to delete old thumbnail: {e}")
        
        # Render new thumbnail
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