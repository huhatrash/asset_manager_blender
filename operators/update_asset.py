import bpy
import os
from ..core.database import db_get_by_id, get_connection
from ..core.export_import import export_selected_to_fbx
from ..core.thumbnail import render_thumbnail_for_object
from ..core.paths import EXPORTS_DIR
from ..core.scene_assets import load_assets_to_scene


class ASSETMANAGER_OT_update(bpy.types.Operator):
    bl_idname = "assetmanager.update"
    bl_label = "Update Asset Metadata"
    bl_description = "Perbarui metadata, file, dan thumbnail asset"

    asset_id: bpy.props.IntProperty()
    name: bpy.props.StringProperty(name="Name")
    category: bpy.props.EnumProperty(
        name="Category",
        items=[
            ('model','Model',''),
            ('characters','Characters',''),
            ('environment','Environment',''),
            ('props','Props',''),
            ('default model','Default Model',''),
        ],
        default='model'
    )
    description: bpy.props.StringProperty(name="Description")

    def invoke(self, context, event):
        rec = db_get_by_id(self.asset_id)
        if not rec:
            self.report({'ERROR'}, "Asset tidak ditemukan")
            return {'CANCELLED'}

        self.name = rec["name"]
        self.category = rec["category"]
        self.description = rec["description"]
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Pilih object MESH aktif")
            return {'CANCELLED'}

        rec = db_get_by_id(self.asset_id)
        if not rec:
            self.report({'ERROR'}, "Asset tidak ditemukan")
            return {'CANCELLED'}

        # ===== RE-EXPORT FILE (overwrite) =====
        try:
            fpath = export_selected_to_fbx(obj, EXPORTS_DIR)
            file_size = os.path.getsize(fpath)
        except Exception as e:
            self.report({'ERROR'}, f"Gagal export: {e}")
            return {'CANCELLED'}

        # ===== RENDER ULANG THUMBNAIL =====
        thumb_path = rec["thumbnail_path"]
        render_thumbnail_for_object(obj, thumb_path, size=(256, 256))

        # ===== HITUNG ULANG STATISTIK =====
        poly_count = len(obj.data.polygons)
        vertices = len(obj.data.vertices)
        faces = poly_count

        # ===== UPDATE DATABASE =====
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE assets
                SET name=?, category=?, description=?,
                    file_path=?, thumbnail_path=?,
                    poly_count=?, vertices=?, faces=?,
                    file_size=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                self.name, self.category, self.description,
                fpath, thumb_path,
                poly_count, vertices, faces,
                file_size, self.asset_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.report({'ERROR'}, f"DB error: {e}")
            return {'CANCELLED'}

        # ===== REFRESH UI & PREVIEW =====
        load_assets_to_scene(context)
        if context.area:
            context.area.tag_redraw()

        self.report({'INFO'}, "Asset berhasil diperbarui")
        return {'FINISHED'}
