import bpy
from ..core.database import db_toggle_favorite
from ..core.scene_assets import update_single_asset_in_scene

class ASSETMANAGER_OT_toggle_favorite(bpy.types.Operator):
    """Toggle the favorite status of an asset"""
    bl_idname = "assetmanager.toggle_favorite"
    bl_label = "Toggle Favorite"
    bl_description = "Add or remove this asset from favorites"
    bl_options = {'REGISTER', 'UNDO'}
    
    asset_id: bpy.props.IntProperty()
    
    def execute(self, context):
        try:
            # Toggle in database (returns bool, new status)
            new_status = db_toggle_favorite(self.asset_id)
            
            # Update memory model so sidebar UI reacts instantly
            update_single_asset_in_scene(context, self.asset_id)
            
            # Update catalog modal memory directly so it reacts instantly
            try:
                from .show_catalog import _CATALOG_REF
                if _CATALOG_REF:
                    op = _CATALOG_REF[0]
                    for asset in op._assets:
                        if asset['id'] == self.asset_id:
                            asset['is_favorite'] = 1 if new_status else 0
                            break
            except Exception:
                pass
            
            # Force redraw to update UI
            screen = getattr(context, "screen", None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            elif context.area:
                context.area.tag_redraw()
                
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to toggle favorite: {str(e)}")
            return {'CANCELLED'}
