import bpy
from ..core.database import db_get_paginated
from ..core.preview import load_preview_for_single_asset
from ..core.preview import get_preview_collection


class ASSETMANAGER_PT_panel(bpy.types.Panel):
    """Main Asset Manager Panel"""
    bl_label = "3D Asset Manager"
    bl_idname = "ASSETMANAGER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # ================= TOP ACTIONS =================
        box = layout.box()
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("assetmanager.import_local", icon='IMPORT', text="Import")
        row.operator("assetmanager.export_local", icon='EXPORT', text="Export")
        
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("assetmanager.register", icon='ADD', text="Register Asset")
        row.operator("assetmanager.refresh_assets", icon='FILE_REFRESH', text="")
        
        layout.separator()

        # ================= UTILITIES =================
        utils_box = layout.box()
        utils_box.label(text="Utilities", icon='TOOL_SETTINGS')
        
        row = utils_box.row(align=True)
        row.operator("assetmanager.show_catalog", icon='WINDOW', text="Catalog View")
        row.operator("assetmanager.show_statistics", icon='INFO', text="Stats")
        
        # ================= SEARCH & FILTERS =================
        filter_box = layout.box()
        filter_box.label(text="Search & Filter", icon='VIEWZOOM')
        
        # Search box
        row = filter_box.row()
        row.prop(scene, "asset_search", text="", icon='VIEWZOOM', placeholder="Search assets...")
        
        # Category filter
        row = filter_box.row()
        row.prop(scene, "asset_category", text="Category")
        
        # ================= ADVANCED FILTERS (COLLAPSIBLE) =================

        # Toggle header untuk advanced filters
        row = filter_box.row(align=True)
        show_advanced = getattr(scene, "show_advanced_filters", False)

        icon = 'TRIA_DOWN' if show_advanced else 'TRIA_RIGHT'
        row.prop(scene, "show_advanced_filters", 
                icon=icon, icon_only=True, emboss=False)
        row.label(text="Advanced Filters", icon='PREFERENCES')

        # Tampilkan filter advanced hanya jika expanded
        if show_advanced:
            
            # File size filters
            col = filter_box.column(align=True)
            col.label(text="File Size (KB):", icon='FILE')
            row = col.row(align=True)
            row.prop(scene, "filter_min_size", text="Min")
            row.prop(scene, "filter_max_size", text="Max")
            
            # Polygon filters
            col = filter_box.column(align=True)
            col.label(text="Polygon Count:", icon='MESH_CUBE')
            row = col.row(align=True)
            row.prop(scene, "filter_min_poly", text="Min")
            row.prop(scene, "filter_max_poly", text="Max")

        # Filter controls
        row = filter_box.row(align=True)
        row.operator("assetmanager.apply_filters", text="Apply", icon='FILTER')
        row.operator("assetmanager.clear_filters", text="Clear", icon='X')

        # ================= PAGINATION INFO (COLLAPSIBLE) =================
        total = getattr(scene, "asset_total_count", 0)
        current_page = getattr(scene, "asset_current_page", 0)
        total_pages = getattr(scene, "asset_total_pages", 0)
        page_size = getattr(scene, "asset_page_size", 10)
        loaded = len(scene.asset_items)
        
        info_box = layout.box()
        
        # Toggle header
        row = info_box.row(align=True)
        show_pagination = getattr(scene, "show_pagination_info", True)
        
        icon = 'TRIA_DOWN' if show_pagination else 'TRIA_RIGHT'
        row.prop(scene, "show_pagination_info", 
                 icon=icon, icon_only=True, emboss=False)
        row.label(text=f"Pagination ({loaded} of {total:,} assets)", icon='ASSET_MANAGER')
        
        # Show pagination details if expanded
        if show_pagination:
            info_box.separator(factor=0.3)
            
            if total_pages > 1:
                row = info_box.row(align=True)
                row.label(text=f"Page {current_page + 1} / {total_pages}", icon='DOCUMENTS')
            
            # Sorting
            row = info_box.row()
            sort_by = getattr(scene, "asset_sort_by", 'created_at')
            sort_order = getattr(scene, "asset_sort_order", 'DESC')
            sort_icon = 'SORT_DESC' if sort_order == 'DESC' else 'SORT_ASC'
            
            sort_labels = {
                'created_at': 'Date',
                'name': 'Name',
                'category': 'Category',
                'file_size': 'Size',
                'poly_count': 'Polys',
            }
            sort_text = f"Sort: {sort_labels.get(sort_by, sort_by)}"
            row.operator("assetmanager.change_sort", text=sort_text, icon=sort_icon)
        
        layout.separator()
        
        # ================= PAGINATION CONTROLS =================
        # Always show navigation box
        nav_box = layout.box()
        nav_box.label(text="Navigation", icon='SHORTDISPLAY')
        
        # Navigation buttons
        row = nav_box.row(align=True)
        row.scale_y = 1.2
        
        # Disable all if only 1 page
        row.enabled = (total_pages > 1)
        
        # First button
        row.operator("assetmanager.first_page", text="", icon='REW')
        
        # Previous button
        row.operator("assetmanager.previous_page", text="Prev", icon='TRIA_LEFT')
        
        # Page indicator
        if total_pages > 0:
            row.operator("assetmanager.go_to_page", text=f"{current_page + 1}/{total_pages}")
        else:
            row.operator("assetmanager.go_to_page", text="0/0")
        
        # Next button
        row.operator("assetmanager.next_page", text="Next", icon='TRIA_RIGHT')
        
        # Last button
        row.operator("assetmanager.last_page", text="", icon='FF')
        
        # Page size selector - ALWAYS VISIBLE
        row = nav_box.row()
        row.operator("assetmanager.change_page_size", text=f"Items per page: {page_size}", icon='PREFERENCES')
        
        # Show info if only 1 page
        if total_pages <= 1:
            row = nav_box.row()
            row.label(text="All assets on one page", icon='INFO')
        
        layout.separator()
        
         # ================= ASSET BROWSER =================
        # Info header (compact)
        total = getattr(scene, "asset_total_count", 0)
        current_page = getattr(scene, "asset_current_page", 0)
        total_pages = getattr(scene, "asset_total_pages", 0)
        page_size = getattr(scene, "asset_page_size", 10)
        loaded = len(scene.asset_items)

        box = layout.box()
        row = box.row(align=True)

        # Show result count (LEFT)
        if total > 0:
            row.label(text=f"Showing {loaded} of {total:,} assets", icon='ASSET_MANAGER')
        else:
            row.label(text="No assets found", icon='INFO')

        # Spacer untuk push ke kanan
        row.label(text="")

        # Sort button (RIGHT)
        sort_by = getattr(scene, "asset_sort_by", 'created_at')
        sort_order = getattr(scene, "asset_sort_order", 'DESC')
        sort_icon = 'SORT_DESC' if sort_order == 'DESC' else 'SORT_ASC'
        sort_labels = {
            'created_at': 'Date',
            'name': 'Name',
            'category': 'Category',
            'file_size': 'Size',
            'poly_count': 'Polys',
        }
        row.operator("assetmanager.change_sort", 
                    text=sort_labels.get(sort_by, sort_by), 
                    icon=sort_icon, emboss=False)
        
        # ================= ASSET LIST & PREVIEW =================
        split = layout.split(factor=0.5)
        
        # LEFT: Asset List
        col_left = split.column()
        col_left.label(text="Assets", icon='OUTLINER')
        col_left.template_list(
            "ASSETMANAGER_UL_list",
            "",
            scene,
            "asset_items",
            scene,
            "asset_index",
            rows=8
        )
        
        # RIGHT: Preview
        col_right = split.column()
        col_right.label(text="Preview", icon='IMAGE_DATA')

        if scene.show_thumbnail:
            idx = scene.asset_index
            if 0 <= idx < len(scene.asset_items):
                item = scene.asset_items[idx]
                
                # Gunakan key yang sudah di-load
                preview_key = f"asset_{item.uuid}"
                pcoll = get_preview_collection()
                
                if preview_key in pcoll:
                    col_right.template_icon(
                        icon_value=pcoll[preview_key].icon_id,
                        scale=8
                    )
                else:
                    col_right.label(text="No Preview", icon='INFO')
            else:
                col_right.label(text="No Selection", icon='INFO')
        else:
            col_right.label(text="Preview disabled", icon='HIDE_ON')

        col_right.prop(scene, "show_thumbnail")
        
        # ================= ASSET DETAILS =================
        details_box = layout.box()
        details_box.label(text="Asset Details", icon='PROPERTIES')
        
        idx = scene.asset_index
        if 0 <= idx < len(scene.asset_items):
            item = scene.asset_items[idx]
            
            # Metadata section
            meta_box = details_box.box()
            meta_box.label(text="Metadata", icon='FILE_TEXT')
            
            col = meta_box.column(align=True)
            col.prop(item, "name", text="Name", emboss=False)
            col.prop(item, "category", text="Category", emboss=False)
            col.prop(item, "description", text="Description", emboss=False)
            
            meta_box.separator()
            
            # Timestamps
            split = meta_box.split(factor=0.35)
            split.label(text="Created:")
            split.label(text=item.created_at)
            
            split = meta_box.split(factor=0.35)
            split.label(text="Updated:")
            split.label(text=item.updated_at)
            
            # Mesh Statistics section
            stats_box = details_box.box()
            stats_box.label(text="Mesh Statistics", icon='MESH_CUBE')
            
            grid = stats_box.grid_flow(columns=2, even_columns=True, align=True)
            
            col = grid.column()
            col.label(text="Polygons:")
            col.label(text=f"{item.poly_count:,}")
            
            col = grid.column()
            col.label(text="Vertices:")
            col.label(text=f"{item.vertices:,}")
            
            # File Information section
            file_box = details_box.box()
            file_box.label(text="File Information", icon='FILE_FOLDER')
            
            # File path (read-only, scrollable)
            col = file_box.column()
            col.enabled = False
            col.prop(item, "file_path", text="Path")
            
            # File size
            file_size_mb = item.file_size / (1024 * 1024)
            row = file_box.row()
            row.label(text="Size:")
            row.label(text=f"{file_size_mb:.2f} MB")
            
        else:
            details_box.label(text="No asset selected", icon='INFO')
        
        layout.separator()
        
        # ================= ACTION BUTTONS =================
        action_box = layout.box()
        action_box.label(text="Actions", icon='SETTINGS')
        
        idx = scene.asset_index
        if 0 <= idx < len(scene.asset_items):
            item = scene.asset_items[idx]
            
            # Primary actions
            row = action_box.row(align=True)
            row.scale_y = 1.3
            
            op_load = row.operator(
                "assetmanager.load_from_db",
                text="Load",
                icon='IMPORT'
            )
            op_load.asset_id = item.id
            
            op_update = row.operator(
                "assetmanager.update",
                text="Update",
                icon='FILE_REFRESH'
            )
            op_update.asset_id = item.id
            
            # Dangerous action (delete) - separate row
            row = action_box.row()
            row.scale_y = 1.2
            op_delete = row.operator(
                "assetmanager.delete",
                text="Delete Asset",
                icon='TRASH'
            )
            op_delete.asset_id = item.id
            
        else:
            row = action_box.row()
            row.label(text="Select an asset to enable actions", icon='INFO')
        
        layout.separator()


# =====================================================
# ADDITIONAL SUB-PANELS (OPTIONAL)
# =====================================================

class ASSETMANAGER_PT_quick_filters(bpy.types.Panel):
    """Quick filter presets sub-panel"""
    bl_label = "Quick Filters"
            # File path (read-only, scrollable)
    bl_idname = "ASSETMANAGER_PT_quick_filters"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Category quick filters
        box = layout.box()
        box.label(text="By Category", icon='BOOKMARKS')
        
        categories = [
            ('model', 'Models', 'MESH_CUBE'),
            ('character', 'Characters', 'ARMATURE_DATA'),
            ('environment', 'Environment', 'WORLD'),
            ('props', 'Props', 'OBJECT_DATA'),
        ]
        
        for cat_id, cat_name, icon in categories:
            op = box.operator(
                "assetmanager.apply_filters",
                text=cat_name,
                icon=icon
            )
            # Note: This would need custom implementation to set category
        
        # Size presets
        box = layout.box()
        box.label(text="By Size", icon='FILE')
        
        row = box.row(align=True)
        row.operator("assetmanager.apply_filters", text="Small (<10MB)")
        row.operator("assetmanager.apply_filters", text="Large (>100MB)")


# =====================================================
# REGISTER
# =====================================================

classes = (
    ASSETMANAGER_PT_panel,
    ASSETMANAGER_PT_quick_filters,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)