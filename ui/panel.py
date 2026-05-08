import bpy
from ..core.database import db_get_paginated, db_get_library_stats
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
    'vertices': 'Verts',
    'edges': 'Edges',
}


# =====================================================
# PERFORMANCE: DISK CHECK CACHE
# =====================================================

from ..core.paths import safe_file_exists

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
        wm = context.window_manager

        total = getattr(wm, "asset_total_count", 0)
        loaded = len(wm.asset_items)

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
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        # ---- Search + Category + Favorites + Sort (compact single row) ----
        row = layout.row(align=True)
        row.prop(wm, "asset_search", text="", icon='VIEWZOOM',
                 placeholder="Search...")
        row.prop(wm, "asset_category", text="")
        
        # Favorites toggle
        fav_icon = 'SOLO_ON' if wm.filter_favorites else 'SOLO_OFF'
        row.prop(wm, "filter_favorites", text="", icon=fav_icon)

        # Sort toggle (icon only)
        row.operator("assetmanager.change_sort", text="", icon='SORT_DESC')

        # ---- Asset list + preview ----
        split = layout.split(factor=0.50)

        # LEFT — list
        col_list = split.column()
        col_list.template_list(
            "ASSETMANAGER_UL_list", "",
            wm, "asset_items",
            wm, "asset_index",
            rows=8,
        )

        # RIGHT — preview
        col_prev = split.column()
        if wm.show_thumbnail:
            idx = wm.asset_index
            if 0 <= idx < len(wm.asset_items):
                item = wm.asset_items[idx]
                from ..core.preview import get_asset_preview_key
                preview_key = get_asset_preview_key(item)
                pcoll = get_preview_collection()

                if preview_key not in pcoll:
                    # ✅ ON-DEMAND LOAD: Only for the main preview panel
                    load_preview_for_single_asset(item)

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

        col_prev.prop(wm, "show_thumbnail", text="Preview")

        # ---- Pagination (optimized width) ----
        total_pages = getattr(wm, "asset_total_pages", 0)
        current_page = getattr(wm, "asset_current_page", 0)

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
        page_size = getattr(wm, "asset_page_size", 10)
        row_size.operator("assetmanager.change_page_size",
                          text=str(page_size), icon='PREFERENCES')

        # ---- Primary actions for selected asset ----
        idx = wm.asset_index
        if 0 <= idx < len(wm.asset_items):
            item = wm.asset_items[idx]

            row = layout.row(align=True)
            row.scale_y = 1.4

            # Check if file exists on disk (using cached check for speed)
            file_exists = safe_file_exists(item.file_path)

            op = row.operator("assetmanager.load_from_db",
                               text="Load" if file_exists else "File Missing", 
                               icon='IMPORT' if file_exists else 'ERROR')
            op.asset_id = item.id
            row.enabled = file_exists

            op = row.operator("assetmanager.edit_metadata",
                              text="Edit", icon='FILE_TEXT')
            op.asset_id = item.id

            op = row.operator("assetmanager.update_source",
                              text="Update Source", icon='FILE_REFRESH')
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
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        idx = wm.asset_index
        if not (0 <= idx < len(wm.asset_items)):
            layout.label(text="No asset selected", icon='INFO')
            return

        item = wm.asset_items[idx]

        # ── ROBUST FEEDBACK: Check if file exists ──────────────────────────
        file_exists = safe_file_exists(item.file_path)
        
        if not file_exists:
            box = layout.box()
            row = box.row()
            row.alert = True
            row.label(text="FILE MISSING FROM DISK", icon='ERROR')
            box.label(text="This record should be cleaned up or the file restored.", icon='INFO')
            layout.separator()

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
        grid.label(text=f"Edges: {_format_count(item.edges)}", icon='EDGESEL')
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
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        layout.use_property_split = True
        layout.use_property_decorate = False

        # Size range
        col = layout.column(align=True)
        col.prop(wm, "filter_min_size", text="Min Size (KB)")
        col.prop(wm, "filter_max_size", text="Max Size (KB)")

        col.separator(factor=0.5)

        # Polygon & Vertex range
        col = layout.column(align=True)
        col.prop(wm, "filter_min_poly", text="Min Polys")
        col.prop(wm, "filter_max_poly", text="Max Polys")
        col.prop(wm, "filter_min_vert", text="Min Verts")
        col.prop(wm, "filter_max_vert", text="Max Verts")

        layout.separator(factor=0.5)
        
        # Date Logic
        col = layout.column(align=True)
        col.prop(wm, "filter_days_old", text="Added Last")

        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("assetmanager.apply_filters",
                     text="Apply Filters", icon='FILTER')
        row.operator("assetmanager.clear_filters",
                     text="Reset All", icon='LOOP_BACK')


# =====================================================
# 5.5) RECENTLY USED  — collapsed by default
# =====================================================

def _relative_time(dt_str):
    """Return a human-readable relative time string for a datetime string."""
    import datetime
    if not dt_str:
        return "?"
    try:
        then = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        diff = datetime.datetime.now() - then
        secs = int(diff.total_seconds())
        if secs < 60:
            return "Just now"
        elif secs < 3600:
            return f"{secs // 60}m ago"
        elif secs < 86400:
            return f"{secs // 3600}h ago"
        elif secs < 86400 * 7:
            return f"{diff.days}d ago"
        else:
            return then.strftime("%d %b")
    except Exception:
        return dt_str[:10]

class ASSETMANAGER_PT_recently_used(bpy.types.Panel):
    """Show recently loaded assets"""
    bl_label = "Recently Used"
    bl_idname = "ASSETMANAGER_PT_recently_used"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 5

    def draw(self, context):
        import os
        layout = self.layout
        from ..core.database import db_get_recently_used
        from ..core.preview import get_preview_collection

        recent = db_get_recently_used(limit=5)

        if not recent:
            layout.label(text="No history yet.")
            return

        pcoll = get_preview_collection()
        layout.separator(factor=0.5)

        for asset in recent:
            asset_id = asset['id']
            box = layout.box()
            row = box.row()

            # ── 1. Thumbnail — lazy-load on demand
            from ..core.preview import get_asset_preview_key
            key = get_asset_preview_key(asset)
            if key not in pcoll:
                # Preview not cached yet (asset might be on page 2+) — load it now
                from ..core.preview import load_preview_for_single_asset
                load_preview_for_single_asset(asset)

            if key in pcoll:
                row.template_icon(icon_value=pcoll[key].icon_id, scale=3.2)
            else:
                col_icon = row.column()
                col_icon.scale_y = 2.5
                col_icon.label(text="", icon='IMAGE_DATA')


            # ── 2. Clickable Info area (Right side)
            col = row.column(align=True)
            col.alignment = 'LEFT'
            
            # Name
            name = asset.get('name', 'Unknown')
            r1 = col.row()
            r1.alignment = 'LEFT'
            op1 = r1.operator("assetmanager.load_from_db", text=name, emboss=False)
            op1.asset_id = asset_id
            
            col.separator(factor=0.3)

            # Source Blend File
            source = asset.get('source_file', '')
            s_name = os.path.basename(source) if source else "Unsaved Scene"
            if len(s_name) > 24: s_name = s_name[:22] + "..."
            
            r2 = col.row()
            r2.alignment = 'LEFT'
            r2.scale_y = 0.8
            r2.enabled = False # Subtle look for metadata
            op2 = r2.operator("assetmanager.load_from_db", text=s_name, emboss=False)
            op2.asset_id = asset_id
            
            # Time Relative
            time_str = _relative_time(asset.get('used_at', ''))
            r3 = col.row()
            r3.alignment = 'LEFT'
            r3.scale_y = 0.8
            r3.enabled = False # Subtle look for metadata
            op3 = r3.operator("assetmanager.load_from_db", text=time_str, emboss=False)
            op3.asset_id = asset_id


# =====================================================
# 6) LIBRARY MANAGEMENT  — collapsed by default
# =====================================================

class ASSETMANAGER_PT_management(bpy.types.Panel):
    """Import, export, register & utilities"""
    bl_label = "Library Management"
    bl_idname = "ASSETMANAGER_PT_management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_order = 1

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

        col.separator()

        # Utilities
        row = col.row(align=True)
        row.operator("assetmanager.show_catalog",
                     icon='WINDOW', text="Catalog View")
        row.operator("assetmanager.show_statistics",
                     icon='GRAPH', text="Statistics")


# =====================================================
# 7) MAINTENANCE  — collapsed by default
# =====================================================

class ASSETMANAGER_PT_maintenance(bpy.types.Panel):
    """Diagnostic and cleanup tools"""
    bl_label = "Maintenance"
    bl_idname = "ASSETMANAGER_PT_maintenance"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    bl_parent_id = "ASSETMANAGER_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="System Maintenance", icon='NONE')
        
        # Row 1: Optimize
        row = box.row(align=True)
        row.label(text="Database Health", icon='NONE')
        row.operator("assetmanager.optimize_db", text="Optimize", icon='FILE_REFRESH')
        
        # Row 2: Orphans
        row = box.row(align=True)
        row.label(text="Integrity Cleanup", icon='NONE')
        row.operator("assetmanager.cleanup_orphans", text="Cleanup", icon='TRASH')
        
        # Row 3: History
        row = box.row(align=True)
        row.label(text="Usage History", icon='NONE')
        row.operator("assetmanager.trim_history", text="Trim", icon='REMOVE')

        box.separator(factor=0.5)
        
        # --- NEW: Library Diagnostics ---
        diag_box = box.box()
        diag_box.label(text="Library Diagnostics", icon='INFO')
        
        stats = db_get_library_stats()
        if 'error' not in stats:
            col = diag_box.column(align=True)
            
            # Row: Total Assets
            row = col.row()
            row.label(text="Total Assets:")
            row.label(text=str(stats.get('total_assets', 0)))
            
            # Row: Library Size
            row = col.row()
            row.label(text="Library Size:")
            row.label(text=_format_size(stats.get('total_bytes', 0)))
            
            # Row: Categories Breakdown (compact)
            if stats.get('categories'):
                diag_box.separator(factor=0.3)
                cats = stats['categories']
                cat_text = ", ".join([f"{c.capitalize()}: {v}" for c, v in cats.items()])
                diag_box.label(text=cat_text, icon='NONE')
        else:
            diag_box.label(text="Stats unavailable", icon='ERROR')

        box.separator(factor=0.5)
        
        # Version Footer
        row = layout.row()
        row.alignment = 'RIGHT'
        row.enabled = False
        row.label(text="Asset Manager v3.1.2 Production", icon='NONE')


# =====================================================
# REGISTER
# =====================================================

classes = (
    ASSETMANAGER_PT_panel,
    ASSETMANAGER_PT_management,
    ASSETMANAGER_PT_browse,
    ASSETMANAGER_PT_filters,
    ASSETMANAGER_PT_details,
    ASSETMANAGER_PT_recently_used,
    ASSETMANAGER_PT_maintenance,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)