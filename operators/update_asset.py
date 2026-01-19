import bpy
import os
import re
from ..core.database import db_get_by_id, get_connection
from ..core.export_import import export_selected_to_fbx
from ..core.thumbnail import render_thumbnail_for_object
from ..core.paths import EXPORTS_DIR, THUMBS_DIR
from ..core.scene_assets import load_assets_to_scene
from ..core.preview import refresh_asset_preview

class ASSETMANAGER_OT_update(bpy.types.Operator):
    bl_idname = "assetmanager.update"
    bl_label = "Update Asset Metadata"
    bl_description = "Perbarui metadata asset di database"

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
            self.report({'ERROR'}, "Asset not found in DB")
            return {'CANCELLED'}
        self.name = rec.get("name", "")
        self.category = rec.get("category", "model")
        self.description = rec.get("description", "")
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Pilih object MESH aktif untuk update bentuk")
            return {'CANCELLED'}

        rec = db_get_by_id(self.asset_id)
        if not rec:
            self.report({'ERROR'}, "Asset tidak ditemukan")
            return {'CANCELLED'}

        # ===== RE-EXPORT FILE =====
        try:
            fpath = export_selected_to_fbx(obj, EXPORTS_DIR, 'FBX')
            file_size = os.path.getsize(fpath)
        except Exception as e:
            self.report({'ERROR'}, f"Gagal export: {e}")
            return {'CANCELLED'}

        # ===== RENDER ULANG THUMBNAIL =====
        thumb_path = rec.get("thumbnail_path")
        if not thumb_path:
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', f"{self.name}{obj.as_pointer()}")
            thumb_path = os.path.join(THUMBS_DIR, f"{safe_name}_thumb.png")

        render_thumbnail_for_object(obj, thumb_path, size=(256,256))

        # ===== HITUNG ULANG STATISTIK =====
        poly_count = len(obj.data.polygons)
        vertices = len(obj.data.vertices)
        faces = len(obj.data.polygons)

        # ===== UPDATE DATABASE =====
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE assets4
                SET name=?, category=?, description=?, file_path=?,
                    thumbnail_path=?, poly_count=?, vertices=?, faces=?,
                    file_size=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                self.name, self.category, self.description,
                fpath, thumb_path,
                poly_count, vertices, faces,
                file_size, self.asset_id
            ))
            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            self.report({'ERROR'}, f"DB error: {e}")
            return {'CANCELLED'}

        # ===== REFRESH PREVIEW CACHE =====
        refresh_asset_preview(self.asset_id, thumb_path)

        # ===== RELOAD UI =====
        load_assets_to_scene(context)
        context.area.tag_redraw()

        self.report({'INFO'}, "Asset & preview berhasil diperbarui")
        return {'FINISHED'}