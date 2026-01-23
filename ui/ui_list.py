"""
UIList - Asset Manager
Custom UI list with preview icons.

Author: alfa haliza
Version: 2.1 (With Preview Icons)
"""

import bpy
from ..core.preview import get_preview_collection, load_preview_for_single_asset
from ..core.database import db_get_by_id


class ASSETMANAGER_UL_list(bpy.types.UIList):
    """Custom UIList for asset display with preview icons"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """
        Draw single list item with preview icon.
        
        Args:
            context: Blender context
            layout: UI layout
            data: Data container (Scene)
            item: AssetItem being drawn
            icon: Icon ID
            active_data: Active data
            active_propname: Active property name
            index: Item index
        """
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
            
            # Preview thumbnail (if available)
            if preview_icon_id > 0:
                row.template_icon(icon_value=preview_icon_id, scale=2.0)
            else:
                # Fallback to category icon
                row.label(text="", icon=cat_icon)
            
            # Split for name and stats
            split = row.split(factor=0.65, align=True)
            
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
            
            if preview_icon_id > 0:
                layout.template_icon(icon_value=preview_icon_id, scale=4.0)
            else:
                layout.label(text="", icon='FILE_3D')
            
            # Asset name below icon
            layout.label(text=item.name)
    
    def _get_preview_icon(self, item):
        """
        Get preview icon ID for an asset item.
        
        Args:
            item: AssetItem
        
        Returns:
            int: Icon ID (0 if not found)
        """
        try:
            pcoll = get_preview_collection()
            
            if not pcoll:
                return 0
            
            # Get preview key
            preview_key = item.preview_icon
            
            if not preview_key:
                preview_key = f"asset_{item.uuid}"
            
            # Check if preview exists
            if preview_key in pcoll:
                return pcoll[preview_key].icon_id
            
            # Try to load preview on-demand
            asset_data = db_get_by_id(item.id)
            if asset_data:
                preview = load_preview_for_single_asset(asset_data)
                if preview:
                    return preview.icon_id
            
            return 0
            
        except Exception as e:
            print(f"[AssetManager] Failed to get preview icon: {e}")
            return 0


# Compact variant (no preview icons, faster)
class ASSETMANAGER_UL_list_compact(bpy.types.UIList):
    """Compact UIList variant without preview icons"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """Draw single item - compact version."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Simple one-line display
            row = layout.row(align=True)
            
            # Category icon
            category_icons = {
                'model': 'MESH_CUBE',
                'character': 'ARMATURE_DATA',
                'environment': 'WORLD',
                'props': 'OBJECT_DATA',
            }
            cat_icon = category_icons.get(item.category, 'MESH_CUBE')
            
            row.label(text=item.name, icon=cat_icon)
            
            # File size
            size_mb = item.file_size / (1024 * 1024)
            row.label(text=f"{size_mb:.1f}MB")
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.name)