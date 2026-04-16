import bpy
from bpy.props import IntProperty, EnumProperty, StringProperty, BoolProperty


# ─────────────────────────────────────────────────────────────────────────────
#  CATALOG OPERATOR — modern grid layout, working prev/next
# ─────────────────────────────────────────────────────────────────────────────

class ASSETMANAGER_OT_show_catalog(bpy.types.Operator):
    """Open the Asset Catalog grid viewer"""
    bl_idname      = "assetmanager.show_catalog"
    bl_label       = "Asset Catalog"
    bl_description = "Browse all registered assets in a grid view"

    # ── State (stored on operator so reopening the same instance refreshes) ──
    _assets:   list = []
    _previews: dict = {}
    _total:    int  = 0

    # ── Editable props (survive across pages) ────────────────────────────────
    current_page: IntProperty(default=0, min=0)
    page_size:    IntProperty(default=16, min=4, max=64)

    search_text: StringProperty(
        name="Search",
        description="Filter assets by name",
        default="",
        options={'TEXTEDIT_UPDATE'},
    )

    category_filter: EnumProperty(
        name="Category",
        items=[
            ('ALL',         'All Categories', '', 'ASSET_MANAGER', 0),
            ('model',       'Models',         '', 'MESH_CUBE',     1),
            ('character',   'Characters',     '', 'ARMATURE_DATA', 2),
            ('environment', 'Environment',    '', 'WORLD',         3),
            ('props',       'Props',          '', 'OBJECT_DATA',   4),
        ],
        default='ALL',
    )
    
    filter_favorites: BoolProperty(
        name="Show Favorites",
        description="Show only favorite assets",
        default=False
    )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _load_page(self):
        """Fetch assets for the current page and pre-load their previews."""
        from ..core.database     import db_get_paginated
        from ..core.preview      import load_preview_for_single_asset

        cat = None if self.category_filter == 'ALL' else self.category_filter

        self._assets, self._total = db_get_paginated(
            page      = self.current_page,
            page_size = self.page_size,
            category  = cat,
            search    = self.search_text.strip(),
            filter_favorites = self.filter_favorites
        )

        # Reload previews for this page only
        self._previews = {}
        for asset in self._assets:
            preview = load_preview_for_single_asset(asset)
            if preview:
                self._previews[f"asset_{asset['uuid']}"] = preview

    def _total_pages(self) -> int:
        if self._total <= 0:
            return 1
        return (self._total + self.page_size - 1) // self.page_size

    # ── Blender operator interface ───────────────────────────────────────────

    def invoke(self, context, event):
        self.current_page = 0
        self._load_page()
        # invoke_props_dialog gives a proper modal dialog with OK/Cancel
        # width=960 gives a comfortable 4-column grid
        return context.window_manager.invoke_props_dialog(self, width=900)

    def draw(self, context):
        layout = self.layout
        total_pages = self._total_pages()

        # ── Header ───────────────────────────────────────────────────────────
        
        header = layout.box()
        header.scale_y = 1.0

        # Title row
        row = header.row(align=True)
        row.label(text="Asset Catalog", icon='ASSET_MANAGER')
        row.separator()
        # Asset count badge
        if self._total > 0:
            row.label(text=f"{self._total:,} assets")
        else:
            row.label(text="No assets")

        header.separator(factor=0.4)

        # Search + Category in one compact row
        # Use split to prevent inputs from equally dividing the total space
        split = header.split(factor=0.6, align=True)
        
        # Search bar takes 40% of the row
        split.prop(self, "search_text", text="", icon='VIEWZOOM', placeholder="Search assets…")
        
        # The rest of the controls share the remaining 60%
        right_row = split.row(align=True)
        right_row.prop(self, "category_filter", text="")
        
        filter_icon = 'SOLO_ON' if self.filter_favorites else 'SOLO_OFF'
        right_row.prop(self, "filter_favorites", text="", icon=filter_icon)
        right_row.separator(factor=0.5)
        
        # Items per page with a shorter label
        right_row.prop(self, "page_size", text="Per Page")
        right_row.separator(factor=0.5)
        
        # Refresh
        right_row.operator("assetmanager.catalog_refresh", text="", icon='FILE_REFRESH')

        # ── Empty state ───────────────────────────────────────────────────────
        if not self._assets:
            layout.separator()
            layout.label(text="No assets match your search.", icon='INFO')
            return

        layout.separator(factor=0.5)

        # ── Batch toolbar ─────────────────────────────────────────────────────
        from .batch_operations import get_selected_ids, is_selected
        selected_ids  = get_selected_ids()
        n_selected    = len(selected_ids)
        visible_ids   = [a['id'] for a in self._assets]
        all_ids_str   = ",".join(str(i) for i in visible_ids)
        all_selected  = all(is_selected(i) for i in visible_ids) if visible_ids else False

        batch_bar = layout.box()
        brow = batch_bar.row(align=True)

        # Select/Deselect all toggle
        sel_icon = 'CHECKBOX_HLT' if all_selected else 'CHECKBOX_DEHLT'
        op_all = brow.operator(
            "assetmanager.batch_select_all",
            text="All" if not all_selected else "None",
            icon=sel_icon,
        )
        op_all.asset_ids = all_ids_str
        op_all.select    = not all_selected

        if n_selected:
            brow.separator()
            brow.label(text=f"{n_selected} selected", icon='INFO')
            brow.separator()

            # Batch Load
            brow.operator("assetmanager.batch_load",
                          text="Load", icon='IMPORT')

            # Batch Export
            brow.operator("assetmanager.batch_export",
                          text="Export", icon='EXPORT')

            # Batch Delete (red / alert)
            del_row = brow.row(align=True)
            del_row.alert = True
            del_row.operator("assetmanager.batch_delete",
                             text="Delete", icon='TRASH')

            # Clear selection
            brow.separator()
            brow.operator("assetmanager.batch_clear_selection",
                          text="", icon='X')
        else:
            brow.label(text="Select assets for batch operations")

        layout.separator(factor=0.5)

        # ── Asset Grid ────────────────────────────────────────────────────────
        # 4 columns; Blender's grid_flow handles wrapping automatically
        grid = layout.grid_flow(
            columns=4, even_columns=True, even_rows=False,
            align=True, row_major=True,
        )

        for asset in self._assets:
            from .batch_operations import is_selected
            asset_is_selected = is_selected(asset['id'])

            # OUTER CARD
            cell = grid.column()
            cell.separator(factor=0.6)

            outer = cell.column()
            outer.scale_y = 1.15

            # INNER CARD — no red, warna normal
            card = outer.box()

            col = card.column(align=True)

            # --- TOP BAR: tombol checkbox depress=biru saat selected ---
            top_row = col.row(align=True)

            if asset_is_selected:
                op_chk = top_row.operator(
                    "assetmanager.batch_toggle_select",
                    text="", icon='CHECKBOX_HLT',
                    emboss=True, depress=True,
                )
            else:
                op_chk = top_row.operator(
                    "assetmanager.batch_toggle_select",
                    text="", icon='CHECKBOX_DEHLT',
                    emboss=False, depress=False,
                )
            op_chk.asset_id = asset['id']

            # Name + Star
            right_split = top_row.split(factor=0.80, align=True)

            name_col = right_split.column()
            name_col.alignment = 'LEFT'
            name = asset.get('name', 'Unknown')
            if len(name) > 14:
                name = name[:12] + "..."
            name_col.label(text=name)

            star_col = right_split.column()
            star_col.alignment = 'RIGHT'
            is_fav   = bool(asset.get('is_favorite', 0))
            fav_icon = 'SOLO_ON' if is_fav else 'SOLO_OFF'
            op_fav   = star_col.operator("assetmanager.toggle_favorite", text="", icon=fav_icon, emboss=False)
            op_fav.asset_id = asset['id']

            # ================= THUMBNAIL AREA =================
            thumb_wrap = col.box()  # bikin section khusus
            thumb_wrap.scale_y = 1.0

            thumb = thumb_wrap.row()
            thumb.alignment = 'CENTER'

            key = f"asset_{asset['uuid']}"

            if key in self._previews:
                thumb.template_icon(
                    icon_value=self._previews[key].icon_id,
                    scale=9  # lebih besar = lebih modern
                )
            else:
                thumb.label(text="", icon='IMAGE_DATA')

            col.separator()

            # ================= TEXT AREA (Category) =================
            text_col = col.column(align=True)
            text_col.scale_y = 0.9

            cat_row = text_col.row()
            cat_row.alignment = 'CENTER'
            cat_row.scale_y = 0.75
            cat_row.label(text=asset.get('category', '').upper())

            col.separator()

            # ================= BUTTON =================
            btn = col.row()
            btn.scale_y = 1.0

            op = btn.operator(
                "assetmanager.load_from_db_deferred",
                text="Load",
                icon='IMPORT'
            )
            op.asset_id = asset['id']
            
        layout.separator(factor=1.0)

        # ── Pagination bar ────────────────────────────────────────────────────
        self._draw_pagination(layout, total_pages)

    def _draw_pagination(self, layout, total_pages):
        """Compact, always-visible pagination footer."""
        footer = layout.box()
        row = footer.row(align=True)
        row.scale_y = 1.1

        # First Page
        sub = row.row(align=True)
        sub.enabled = self.current_page > 0
        sub.operator("assetmanager.catalog_first_page",
                     text="", icon='REW')

        # Prev Page
        sub2 = row.row(align=True)
        sub2.enabled = self.current_page > 0
        sub2.operator("assetmanager.catalog_prev_page",
                      text="", icon='TRIA_LEFT')

        row.separator()

        # Numbered Pagination
        pages_row = row.row(align=True)
        
        # Calculate window of pages to show
        window_size = 2 # Show 2 pages before and after current
        start_page = max(0, self.current_page - window_size)
        end_page = min(total_pages - 1, self.current_page + window_size)

        if total_pages > 0:
            # Show first page + ellipsis if needed
            if start_page > 0:
                op = pages_row.operator("assetmanager.catalog_goto_page", text="1")
                op.page = 0
                if start_page > 1:
                    pages_row.label(text="...")
            
            for p in range(start_page, end_page + 1):
                is_current = (p == self.current_page)
                op = pages_row.operator("assetmanager.catalog_goto_page", text=str(p + 1), depress=is_current)
                op.page = p
                    
            # Show last page + ellipsis if needed
            if end_page < total_pages - 1:
                if end_page < total_pages - 2:
                    pages_row.label(text="...")
                op = pages_row.operator("assetmanager.catalog_goto_page", text=str(total_pages))
                op.page = total_pages - 1

        row.separator()

        # Next Page
        sub3 = row.row(align=True)
        sub3.enabled = self.current_page < total_pages - 1
        sub3.operator("assetmanager.catalog_next_page",
                      text="", icon='TRIA_RIGHT')

        # Last Page
        sub4 = row.row(align=True)
        sub4.enabled = self.current_page < total_pages - 1
        sub4.operator("assetmanager.catalog_last_page",
                      text="", icon='FF')

    def execute(self, context):
        # OK button pressed — nothing to do (load was done in invoke/page ops)
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  PAGINATION OPERATORS — these re-call _load_page on the active operator
# ─────────────────────────────────────────────────────────────────────────────

def _get_catalog_op():
    """Return the currently open catalog operator instance (stored as a module-level ref)."""
    return _CATALOG_REF[0] if _CATALOG_REF else None

# Module-level reference so pagination ops can reach the live operator
_CATALOG_REF: list = []


class _CatalogPageBase(bpy.types.Operator):
    """Shared base for catalog pagination actions."""
    bl_options = {'INTERNAL', 'REGISTER'}

    def _navigate(self, context, target_page):
        op = _get_catalog_op()
        if op is None:
            self.report({'WARNING'}, "Catalog is not open")
            return {'CANCELLED'}
        op.current_page = target_page
        op._load_page()
        # Force the popup to redraw
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


class ASSETMANAGER_OT_catalog_refresh(_CatalogPageBase):
    bl_idname     = "assetmanager.catalog_refresh"
    bl_label      = "Refresh"
    bl_description = "Reload assets from the database"

    def execute(self, context):
        op = _get_catalog_op()
        if op:
            op._load_page()
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
        return {'FINISHED'}


class ASSETMANAGER_OT_catalog_first_page(_CatalogPageBase):
    bl_idname      = "assetmanager.catalog_first_page"
    bl_label       = "First Page"
    bl_description = "Go to the first page"

    def execute(self, context):
        return self._navigate(context, 0)


class ASSETMANAGER_OT_catalog_goto_page(_CatalogPageBase):
    bl_idname      = "assetmanager.catalog_goto_page"
    bl_label       = "Go to Page"
    bl_description = "Go to a specific page"

    page: IntProperty(default=0)

    def execute(self, context):
        return self._navigate(context, self.page)


class ASSETMANAGER_OT_catalog_prev_page(_CatalogPageBase):
    bl_idname      = "assetmanager.catalog_prev_page"
    bl_label       = "Previous Page"
    bl_description = "Go to the previous page"

    def execute(self, context):
        op = _get_catalog_op()
        if op is None:
            return {'CANCELLED'}
        return self._navigate(context, max(0, op.current_page - 1))


class ASSETMANAGER_OT_catalog_next_page(_CatalogPageBase):
    bl_idname      = "assetmanager.catalog_next_page"
    bl_label       = "Next Page"
    bl_description = "Go to the next page"

    def execute(self, context):
        op = _get_catalog_op()
        if op is None:
            return {'CANCELLED'}
        total_pages = op._total_pages()
        return self._navigate(context, min(total_pages - 1, op.current_page + 1))


class ASSETMANAGER_OT_catalog_last_page(_CatalogPageBase):
    bl_idname      = "assetmanager.catalog_last_page"
    bl_label       = "Last Page"
    bl_description = "Go to the last page"

    def execute(self, context):
        op = _get_catalog_op()
        if op is None:
            return {'CANCELLED'}
        return self._navigate(context, op._total_pages() - 1)


# ─────────────────────────────────────────────────────────────────────────────
#  MONKEY-PATCH: hook into ASSETMANAGER_OT_show_catalog.invoke to store ref
# ─────────────────────────────────────────────────────────────────────────────

_orig_invoke = ASSETMANAGER_OT_show_catalog.invoke


def _patched_invoke(self, context, event):
    _CATALOG_REF.clear()
    _CATALOG_REF.append(self)
    return _orig_invoke(self, context, event)


ASSETMANAGER_OT_show_catalog.invoke = _patched_invoke


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTER
# ─────────────────────────────────────────────────────────────────────────────

classes = (
    ASSETMANAGER_OT_show_catalog,
    ASSETMANAGER_OT_catalog_refresh,
    ASSETMANAGER_OT_catalog_goto_page,
    ASSETMANAGER_OT_catalog_first_page,
    ASSETMANAGER_OT_catalog_prev_page,
    ASSETMANAGER_OT_catalog_next_page,
    ASSETMANAGER_OT_catalog_last_page,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)