import bpy
from ..core.database import db_get_all
from ..core.preview import load_previews_for_assets

class ASSETMANAGER_PT_panel(bpy.types.Panel):
    bl_label = "3D Asset Manager"
    bl_idname = "ASSETMANAGER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Manager'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # top row: import/export
        row = layout.row()
        row.operator("assetmanager.import_local", icon='IMPORT')
        row.operator("assetmanager.export_local", icon='EXPORT')
        
        row = layout.row()
        row.operator("assetmanager.register", icon='PLUS')
        
        row = layout.row()
        row.operator("assetmanager.show_catalog", icon='ASSET_MANAGER')
        
        layout.separator()
        # ================= SEARCH =================
        box = layout.box()
        box.prop(scene, "asset_search", text="", icon='VIEWZOOM')
        
        # ================= CATEGORY =================
        box.prop(scene, "asset_category", text="")
        
          # Smart filter tambahan
        min_size_kb = getattr(scene, "filter_min_size", 0)
        max_size_kb = getattr(scene, "filter_max_size", 0)
        min_poly = getattr(scene, "filter_min_poly", 0)
        max_poly = getattr(scene, "filter_max_poly", 0)

        layout.separator()
        layout.label(text="Filter Tambahan:")
        layout.prop(scene, "filter_min_size")
        layout.prop(scene, "filter_max_size")
        layout.prop(scene, "filter_min_poly")
        layout.prop(scene, "filter_max_poly")

        # ================= LIST + PREVIEW =================
        split = layout.split(factor=0.45)

        # LEFT: LIST
        col_l = split.column()
        col_l.template_list(
            "ASSETMANAGER_UL_list",
            "",
            scene,
            "asset_items",
            scene,
            "asset_index",
            rows=8
        )

        # RIGHT: PREVIEW
        col_r = split.column()
        col_r.label(text="Preview")

        if scene.show_thumbnail:
            idx = scene.asset_index
            if idx >= 0 and idx < len(scene.asset_items):
                item = scene.asset_items[idx]
                previews = load_previews_for_assets(db_get_all())

                if previews and item.preview_icon in previews:
                    col_r.template_icon(
                        icon_value=previews[item.preview_icon].icon_id,
                        scale=6
                    )
                else:
                    col_r.label(text="No Preview")
            else:
                col_r.label(text="No Asset Selected")
        
        # ================= DETAIL ASSETS =================
        box = layout.box()
        box.label(text="Asset Details")

        idx = scene.asset_index
        if 0 <= idx < len(scene.asset_items):
            item = scene.asset_items[idx]

            # ---------- METADATA ----------
            meta_box = box.box()
            meta_box.label(text="Metadata", icon='FILE_TEXT')

            col = meta_box.column(align=True)
            col.prop(item, "name", text="Name")
            col.prop(item, "category", text="Category")
            col.prop(item, "description", text="Description")
            
            meta_box.separator()
            split = meta_box.split(factor=0.35)
            split.label(text="Created at :")
            split.label(text=item.created_at)
            split = meta_box.split(factor=0.35)
            split.label(text="Updated at :")
            split.label(text=item.updated_at)

            # ---------- MESH STATISTICS ----------
            stats_box = box.box()
            stats_box.label(text="Mesh Statistics", icon='MESH_CUBE')

            stats_col = stats_box.column()
            stats_col.enabled = False  # READ ONLY

            grid = stats_col.grid_flow(columns=1, align=True)
            grid.prop(item, "poly_count", text="Polys")
            grid.prop(item, "vertices", text="Verts")
            grid.prop(item, "faces", text="Faces")

            # ---------- FILE INFO ----------
            file_box = box.box()
            file_box.label(text="File Information", icon='FILE_FOLDER')
             
            file_col = file_box.column(align=True)
            file_col.enabled = False 

            file_col.prop(item, "file_path", text="File Path")
            file_col.separator()
            file_col.prop(item, "file_size", text="File Size")

        else:
            box.label(text="No asset selected", icon='INFO')

     # ================= CHECKBOX =================
        layout.prop(scene, "show_thumbnail")

        # ================= BUTTON =================
        box.separator()

        idx = scene.asset_index

        if 0 <= idx < len(scene.asset_items):
            item = scene.asset_items[idx]

            row = box.row(align=True)
            row.scale_y = 1.2

            op_load = row.operator(
                "assetmanager.load_from_db",
                text="Load",
                icon='IMPORT'
            )
            op_load.asset_id = item.id

            op_upd = row.operator(
                "assetmanager.update",
                text="Update",
                icon='FILE_REFRESH'
            )
            op_upd.asset_id = item.id

            op_del = row.operator(
                "assetmanager.delete",
                text="Delete",
                icon='TRASH'
            )
            op_del.asset_id = item.id
        else:
            row = box.row()
            row.label(text="Select an asset to enable actions", icon='INFO')

