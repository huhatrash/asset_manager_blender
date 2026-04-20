
import bpy
import os
from ..core.preview import get_preview_collection, load_preview_for_single_asset
from ..core.database import db_get_by_id


class ASSETMANAGER_UL_list(bpy.types.UIList):
    """Custom UIList for asset display with preview icons"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Draw single list item with preview icon"""
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Get preview icon
            preview_icon_id = self._get_preview_icon(item)
            
            # Category icon as fallback
            category_icons = {
                'model': 'MESH_CUBE',
                'character': 'ARMATURE_DATA',
                'environment': 'WORLD',
                'props': 'OBJECT_DATA',
            }
            cat_icon = category_icons.get(item.category, 'MESH_CUBE')
            
            # Main row
            row = layout.row(align=True)
            
            # ✅ PREVIEW THUMBNAIL - UKURAN KECIL (1.0 scale)
            if preview_icon_id > 0:
                row.template_icon(icon_value=preview_icon_id, scale=1.0)
            else:
                row.label(text="", icon=cat_icon)
            
            # Split untuk name dan stats
            split = row.split(factor=0.6, align=True)
            
            # Left: Name
            col = split.column()
            col.label(text=item.name)
            
            # Right: Stats
            col = split.column()
            row_stats = col.row(align=True)
            row_stats.alignment = 'RIGHT'
            
            row_stats.separator(factor=0.5)
            
            # Favorite star at the far right
            fav_icon = 'SOLO_ON' if item.is_favorite else 'SOLO_OFF'
            op = row_stats.operator("assetmanager.toggle_favorite", text="", icon=fav_icon, emboss=False)
            op.asset_id = item.id
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            
            # Get preview icon
            preview_icon_id = self._get_preview_icon(item)
            
            # ✅ GRID VIEW - ukuran sedang (3.0 scale)
            if preview_icon_id > 0:
                layout.template_icon(icon_value=preview_icon_id, scale=3.0)
            else:
                layout.label(text="", icon='FILE_3D')
            
            # Asset name and Favorite
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(text=item.name)
            
            row.separator(factor=0.2)
            
            fav_icon = 'SOLO_ON' if item.is_favorite else 'SOLO_OFF'
            op = row.operator("assetmanager.toggle_favorite", text="", icon=fav_icon, emboss=False)
            op.asset_id = item.id
    
    def _get_preview_icon(self, item):
        """
        Get preview icon ID for an asset item.
        CRITICAL: No disk I/O or DB queries allowed in this loop!
        """
        try:
            # 1. Get centralized key
            from ..core.preview import get_asset_preview_key, get_preview_collection
            preview_key = get_asset_preview_key(item)
            
            pcoll = get_preview_collection()
            if not pcoll:
                return 0
            
            # 2. Fast Lookup: Only return if already loaded in pcoll
            if preview_key in pcoll:
                return pcoll[preview_key].icon_id
            
            # NOTE: If not in pcoll, we return 0 (fallback icon will be shown)
            # Pre-loading is handled by scene_assets.load_assets_to_scene() or timers.
            return 0
            
        except Exception:
            return 0


# Register
classes = (
    ASSETMANAGER_UL_list,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)