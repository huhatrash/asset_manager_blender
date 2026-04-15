import bpy
from ..core.database import db_get_paginated
from ..core.preview import load_preview_for_single_asset
from ..core.preview import get_preview_collection


# =====================================================
# HELPER
# =====================================================

def _format_size(size_bytes):
    """Format file size to human-readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _format_count(n):
    """Format large numbers: 1500 -> 1.5K, 2000000 -> 2.0M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


SORT_LABELS = {
    'created_at': 'Date',
    'name': 'Name',
    'category': 'Category',
    'file_size': 'Size',
    'poly_count': 'Polys',
}


# =====================================================
# MAIN PANEL  (parent for all sub-panels)
# =====================================================

class ASSETMANAGER_PT_panel(bpy.types.Panel):
    """Main Asset Manager Panel — header only"""
    bl_label = "3D Asset Manager"
    bl_idname = "ASSETMANAGER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'

    def draw_header(self, context):
        self.layout.label(text="", icon='ASSET_MANAGER')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        total = getattr(scene, "asset_total_count", 0)
        loaded = len(scene.asset_items)

        # Compact status line
        row = layout.row(align=True)
        if total > 0:
            row.label(text=f"{loaded} shown / {total:,} total")
        else:
            row.label(text="No assets yet — register your first one below!")
        row.operator("assetmanager.refresh_assets", text="", icon='FILE_REFRESH')

# =====================================================
# 1) SEARCH & BROWSE  — the most-used section
# =====================================================

class ASSETMANAGER_PT_browse(bpy.types.Panel):
    """Browse, search & load assets"""
    bl_label = "Browse Assets"
    bl_idname = "ASSETMANAGER_PT_browse"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # ---- Search + Category + Favorites + Sort (compact single row) ----
        row = layout.row(align=True)
        row.prop(scene, "asset_search", text="", icon='VIEWZOOM',
                 placeholder="Search...")
        row.prop(scene, "asset_category", text="")
        
        # Favorites toggle
        filter_icon = 'SOLO_ON' if scene.filter_favorites else 'SOLO_OFF'
        row.prop(scene, "filter_favorites", text="", icon=filter_icon)

        # Sort toggle (icon only)
        sort_order = getattr(scene, "asset_sort_order", 'DESC')
        sort_icon = 'SORT_DESC' if sort_order == 'DESC' else 'SORT_ASC'
        row.operator("assetmanager.change_sort", text="", icon='PROPERTIES')

        # ---- Asset list + preview ----
        split = layout.split(factor=0.50)

        # LEFT — list
        col_list = split.column()
        col_list.template_list(
            "ASSETMANAGER_UL_list", "",
            scene, "asset_items",
            scene, "asset_index",
            rows=8,
        )

        # RIGHT — preview
        col_prev = split.column()
        if scene.show_thumbnail:
            idx = scene.asset_index
            if 0 <= idx < len(scene.asset_items):
                item = scene.asset_items[idx]
                preview_key = f"asset_{item.uuid}"
                pcoll = get_preview_collection()

                if preview_key in pcoll:
                    col_prev.template_icon(
                        icon_value=pcoll[preview_key].icon_id,
                        scale=8,
                    )
                else:
                    box = col_prev.box()
                    box.scale_y = 4.0
                    box.label(text="No Preview", icon='RENDERLAYERS')
            else:
                box = col_prev.box()
                box.scale_y = 4.0
                box.label(text="Select an asset", icon='RESTRICT_SELECT_OFF')
        else:
            box = col_prev.box()
            box.scale_y = 4.0
            box.label(text="Preview off", icon='HIDE_ON')

        col_prev.prop(scene, "show_thumbnail", text="Preview")

        # ---- Pagination (optimized width) ----
        total_pages = getattr(scene, "asset_total_pages", 0)
        current_page = getattr(scene, "asset_current_page", 0)

        # Split: pagination vs page size (align=False to keep them separate)
        split = layout.split(factor=0.80, align=False)
        
        row_pag = split.row(align=True)
        row_pag.enabled = (total_pages > 1)
        row_pag.operator("assetmanager.first_page", text="", icon='REW')
        row_pag.operator("assetmanager.previous_page", text="", icon='TRIA_LEFT')

        if total_pages > 0:
            row_pag.operator("assetmanager.go_to_page",
                             text=f"{current_page + 1} / {total_pages}")
        else:
            row_pag.operator("assetmanager.go_to_page", text="1 / 1")

        row_pag.operator("assetmanager.next_page", text="", icon='TRIA_RIGHT')
        row_pag.operator("assetmanager.last_page", text="", icon='FF')

        # Page Size (separated by the split's natural gap)
        row_size = split.row(align=True)
        page_size = getattr(scene, "asset_page_size", 10)
        row_size.operator("assetmanager.change_page_size",
                          text=str(page_size), icon='PREFERENCES')

        # ---- Primary actions for selected asset ----
        idx = scene.asset_index
        if 0 <= idx < len(scene.asset_items):
            item = scene.asset_items[idx]

            row = layout.row(align=True)
            row.scale_y = 1.4

            op = row.operator("assetmanager.load_from_db",
                              text="Load Asset", icon='IMPORT')
            op.asset_id = item.id

            op = row.operator("assetmanager.update",
                              text="Update", icon='FILE_REFRESH')
            op.asset_id = item.id
        else:
            row = layout.row()
            row.enabled = False
            row.scale_y = 1.4
            row.operator("assetmanager.load_from_db",
                         text="Select an asset first", icon='IMPORT')


# =====================================================
# 2) ASSET DETAILS  — expanded by default
# =====================================================

class ASSETMANAGER_PT_details(bpy.types.Panel):
    """Details of the selected asset"""
    bl_label = "Asset Details"
    bl_idname = "ASSETMANAGER_PT_details"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        idx = scene.asset_index
        if not (0 <= idx < len(scene.asset_items)):
            layout.label(text="No asset selected", icon='INFO')
            return

        item = scene.asset_items[idx]

        layout.use_property_split = True
        layout.use_property_decorate = False

       # ================= METADATA =================
        col = layout.column()
        col.enabled = False

        def draw_field(col, label, prop):
            row = col.row()
            split = row.split(factor=0.25)
            split.label(text=label)
            split.prop(item, prop, text="")

        draw_field(col, "Name", "name")
        draw_field(col, "Category", "category")
        draw_field(col, "Desc", "description")

        layout.separator(factor=0.5)

        # ================= MESH STATS =================
        box = layout.box()
        grid = box.grid_flow(columns=2, even_columns=True, even_rows=True, align=True)

        grid.label(text=f"Polys: {_format_count(item.poly_count)}", icon='MESH_DATA')
        grid.label(text=f"Verts: {_format_count(item.vertices)}", icon='VERTEXSEL')

        layout.separator(factor=0.6)
        
        # ================= FILE INFO =================
        col_file = layout.column()

        def draw_value(col, label, value):
            row = col.row()
            split = row.split(factor=0.25)
            split.label(text=label)
            split.label(text=value)

        # SIZE (normal)
        draw_value(col_file, "Size", _format_size(item.file_size))

        # PATH (ONLY THIS DISABLED)
        row = col_file.row()
        row.enabled = False
        split = row.split(factor=0.25)
        split.label(text="Path")
        split.prop(item, "file_path", text="")

        # ================= TIMESTAMPS =================
        col_file.separator(factor=0.4)

        sub = col_file.column()

        draw_value(sub, "Created", item.created_at)
        draw_value(sub, "Updated", item.updated_at)

        # Delete — deliberately at the bottom, de-emphasized
        layout.separator()
        row = layout.row()
        row.alert = True
        op = row.operator("assetmanager.delete",
                          text="Delete Asset", icon='TRASH')
        op.asset_id = item.id


# =====================================================
# 3) ADVANCED FILTERS  — collapsed by default
# =====================================================

class ASSETMANAGER_PT_filters(bpy.types.Panel):
    """Advanced filtering options"""
    bl_label = "Advanced Filters"
    bl_idname = "ASSETMANAGER_PT_filters"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.use_property_split = True
        layout.use_property_decorate = False

        # Size range
        col = layout.column(align=True)
        col.prop(scene, "filter_min_size", text="Min Size (KB)")
        col.prop(scene, "filter_max_size", text="Max Size (KB)")

        col.separator(factor=0.5)

        # Polygon range
        col.prop(scene, "filter_min_poly", text="Min Polys")
        col.prop(scene, "filter_max_poly", text="Max Polys")

        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.1
        row.operator("assetmanager.apply_filters",
                     text="Apply Filters", icon='FILTER')
        row.operator("assetmanager.clear_filters",
                     text="Reset All", icon='LOOP_BACK')


# =====================================================
# 4) QUICK FILTERS  — collapsed by default
# =====================================================

class ASSETMANAGER_PT_quick_filters(bpy.types.Panel):
    """One-click category & size presets"""
    bl_label = "Quick Filters"
    bl_idname = "ASSETMANAGER_PT_quick_filters"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Category row
        layout.label(text="Category", icon='BOOKMARKS')
        row = layout.row(align=True)
        row.operator("assetmanager.apply_filters",
                     text="Models", icon='MESH_CUBE')
        row.operator("assetmanager.apply_filters",
                     text="Chars", icon='ARMATURE_DATA')
        row.operator("assetmanager.apply_filters",
                     text="Env", icon='WORLD')
        row.operator("assetmanager.apply_filters",
                     text="Props", icon='OBJECT_DATA')

        layout.separator(factor=0.3)

        # Size presets
        layout.label(text="File Size", icon='FILE')
        row = layout.row(align=True)
        row.operator("assetmanager.apply_filters", text="Small (<10 MB)")
        row.operator("assetmanager.apply_filters", text="Large (>100 MB)")


# =====================================================
# 5) LIBRARY MANAGEMENT  — collapsed by default
# =====================================================

class ASSETMANAGER_PT_management(bpy.types.Panel):
    """Import, export, register & utilities"""
    bl_label = "Library Management"
    bl_idname = "ASSETMANAGER_PT_management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Register (primary action in this section)
        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("assetmanager.register",
                     icon='ADD', text="Register Current Object")

        col.separator()

        # Import / Export
        row = col.row(align=True)
        row.operator("assetmanager.import_local",
                     icon='IMPORT', text="Import Library")
        row.operator("assetmanager.export_local",
                     icon='EXPORT', text="Export Library")

        col.separator()

        # Utilities
        row = col.row(align=True)
        row.operator("assetmanager.show_catalog",
                     icon='WINDOW', text="Catalog View")
        row.operator("assetmanager.show_statistics",
                     icon='GRAPH', text="Statistics")


# =====================================================
# REGISTER
# =====================================================

classes = (
    ASSETMANAGER_PT_panel,
    ASSETMANAGER_PT_management,
    ASSETMANAGER_PT_browse,
    ASSETMANAGER_PT_details,
    ASSETMANAGER_PT_filters,
    ASSETMANAGER_PT_quick_filters,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)