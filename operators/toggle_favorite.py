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
            # Toggle in database (returns bool: True = now a favorite)
            new_status = db_toggle_favorite(self.asset_id)

            # If filtering by favorites, a full reload is needed so the
            # unfavorited asset disappears from the filtered list immediately.
            scene = context.scene
            filter_favorites = getattr(scene, 'filter_favorites', False)
            if filter_favorites:
                from ..core.scene_assets import refresh_current_page
                refresh_current_page(context)
            else:
                # Just update the single item in-place (faster)
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

            # Force redraw everywhere
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to toggle favorite: {str(e)}")
            return {'CANCELLED'}
