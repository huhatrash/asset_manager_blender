import bpy
from bpy.props import IntProperty, EnumProperty, StringProperty


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
        return context.window_manager.invoke_props_dialog(self, width=960)

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
        ctrl_row = header.row(align=True)
        ctrl_row.prop(self, "search_text",     text="", icon='VIEWZOOM',
                      placeholder="Search assets…")
        ctrl_row.separator()
        ctrl_row.prop(self, "category_filter", text="")
        ctrl_row.separator()
        # Refresh
        ctrl_row.operator("assetmanager.catalog_refresh",
                          text="", icon='FILE_REFRESH')

        # ── Empty state ───────────────────────────────────────────────────────
        if not self._assets:
            layout.separator()
            layout.label(text="No assets match your search.", icon='INFO')
            return

        layout.separator(factor=0.5)

        # ── Asset Grid ────────────────────────────────────────────────────────
        # 4 columns; Blender's grid_flow handles wrapping automatically
        grid = layout.grid_flow(
            columns=4, even_columns=True, even_rows=False,
            align=True, row_major=True,
        )

        for asset in self._assets:
            card = grid.box()
            card.scale_y = 1.0

            # Thumbnail
            key = f"asset_{asset['uuid']}"
            if key in self._previews:
                card.template_icon(
                    icon_value=self._previews[key].icon_id,
                    scale=5.5,
                )
            else:
                # Placeholder icon row — centred
                ph = card.row()
                ph.alignment = 'CENTER'
                ph.label(text="", icon='IMAGE_DATA')
                # Spacer so card stays same height
                for _ in range(3):
                    card.label(text="")

            # Asset name — truncated if very long
            name = asset.get('name', '—')
            if len(name) > 22:
                name = name[:20] + "…"
            card.label(text=name, icon='OBJECT_DATA')

            # # Category + size on one row
            # cat       = asset.get('category', '')
            # size_mb   = asset.get('file_size', 0) / (1024 * 1024)
            # poly      = asset.get('poly_count', 0)
            # info_row  = card.row(align=True)
            # info_row.scale_y = 0.75
            # info_row.label(text=f"{cat}")
            # info_row.label(text=f"{size_mb:.1f} MB")

            # # Poly count if available
            # if poly > 0:
            #     pc_row = card.row()
            #     pc_row.scale_y = 0.75
            #     pc_row.label(text=f"{poly:,} polys", icon='MESH_CUBE')

            # card.separator(factor=0.3)

            # Action: Load
            op_row = card.row(align=True)
            op = op_row.operator(
                "assetmanager.load_from_db",
                text="Load", icon='IMPORT',
            )
            op.asset_id = asset['id']

        layout.separator(factor=0.6)

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
                      text="Prev", icon='TRIA_LEFT')

        # Page indicator (centred label)
        row.separator()
        row.label(
            text=f"Page  {self.current_page + 1}  /  {total_pages}  "
                 f"({self._total:,} total)"
        )
        row.separator()

        # Next Page
        sub3 = row.row(align=True)
        sub3.enabled = self.current_page < total_pages - 1
        sub3.operator("assetmanager.catalog_next_page",
                      text="Next", icon='TRIA_RIGHT')

        # Last Page
        sub4 = row.row(align=True)
        sub4.enabled = self.current_page < total_pages - 1
        sub4.operator("assetmanager.catalog_last_page",
                      text="", icon='FF')

        # Page size selector on a separate row
        ps_row = footer.row(align=True)
        ps_row.scale_y = 0.8
        ps_row.prop(self, "page_size", text="Items per page")

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