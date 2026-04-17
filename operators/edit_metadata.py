import bpy

from ..core.database import db_get_by_id, db_update_asset
from ..core.scene_assets import update_single_asset_in_scene


class ASSETMANAGER_OT_edit_metadata(bpy.types.Operator):
    """Edit existing asset metadata (Name, Category, Description)"""
    bl_idname = "assetmanager.edit_metadata"
    bl_label = "Edit Asset Details"
    bl_description = "Update asset name, category, and description"
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

    # =====================================================
    # POLL
    # =====================================================

    @classmethod
    def poll(cls, context):
        """Always allow editing metadata if an asset is selected."""
        return True

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
        
        box = layout.box()
        box.label(text="Edit Asset Info", icon='FILE_TEXT')
        box.prop(self, "name")
        box.prop(self, "category")
        box.prop(self, "description")

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, context):
        """Save metadata back to the database."""
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
            
            # Save to database
            success = db_update_asset(self.asset_id, **update_data)
            
            if not success:
                raise RuntimeError("Database update failed")
            
            # Update UI list item
            update_single_asset_in_scene(context, self.asset_id)
            
            # Force redraw
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    for region in area.regions:
                        region.tag_redraw()
            if context.area:
                context.area.tag_redraw()
            
            # Trigger delayed UI update just in case
            bpy.app.timers.register(self._delayed_refresh, first_interval=0.1)
            
            self.report({'INFO'}, f"Asset '{self.name}' updated successfully")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Update failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    def _delayed_refresh(self):
        """Delayed refresh to ensure UI completely updates"""
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
