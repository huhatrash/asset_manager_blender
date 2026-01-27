"""
UIList - Asset Manager
Custom UI list with SMALLER preview icons.

Author: alfa haliza
Version: 2.2 (Fixed Icon Size)
"""

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
            col.alignment = 'RIGHT'
            
            # Format polygon count
            poly_count = item.poly_count
            if poly_count >= 1000000:
                poly_str = f"{poly_count / 1000000:.1f}M"
            elif poly_count >= 1000:
                poly_str = f"{poly_count / 1000:.0f}K"
            else:
                poly_str = str(poly_count)
            
            col.label(text=poly_str, icon='MESH_DATA')
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            
            # Get preview icon
            preview_icon_id = self._get_preview_icon(item)
            
            # ✅ GRID VIEW - ukuran sedang (3.0 scale)
            if preview_icon_id > 0:
                layout.template_icon(icon_value=preview_icon_id, scale=3.0)
            else:
                layout.label(text="", icon='FILE_3D')
            
            # Asset name
            layout.label(text=item.name)
    
    def _get_preview_icon(self, item):
        """Get preview icon ID for an asset item"""
        try:
            pcoll = get_preview_collection()
            
            if not pcoll:
                return 0
            
            # Check preview key
            preview_key = item.preview_icon if item.preview_icon else f"asset_{item.uuid}"
            
            # Jika sudah ada di cache
            if preview_key in pcoll:
                return pcoll[preview_key].icon_id
            
            # ✅ LOAD ON-DEMAND dari thumbnail file
            asset_data = db_get_by_id(item.id)
            if not asset_data:
                return 0
            
            thumbnail_path = asset_data.get('thumbnail_path')
            if thumbnail_path and os.path.exists(thumbnail_path):
                # Load ke preview collection
                try:
                    preview = pcoll.load(preview_key, thumbnail_path, 'IMAGE')
                    if preview:
                        item.preview_icon = preview_key
                        return preview.icon_id
                except Exception as e:
                    print(f"[AssetManager] Failed to load preview: {e}")
            
            # Fallback
            preview = load_preview_for_single_asset(asset_data)
            if preview:
                return preview.icon_id
            
            return 0
            
        except Exception as e:
            print(f"[AssetManager] Preview icon error: {e}")
            return 0


class ASSETMANAGER_UL_list_compact(bpy.types.UIList):
    """Compact UIList - no preview icons"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Draw compact item"""
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            category_icons = {
                'model': 'MESH_CUBE',
                'character': 'ARMATURE_DATA',
                'environment': 'WORLD',
                'props': 'OBJECT_DATA',
            }
            cat_icon = category_icons.get(item.category, 'MESH_CUBE')
            
            row.label(text=item.name, icon=cat_icon)
            
            size_mb = item.file_size / (1024 * 1024)
            row.label(text=f"{size_mb:.1f}MB")
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.name)


# Register
classes = (
    ASSETMANAGER_UL_list,
    ASSETMANAGER_UL_list_compact,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)