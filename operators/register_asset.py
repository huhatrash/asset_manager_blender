import bpy
import os
import uuid
from ..core.paths import EXPORTS_DIR, THUMBS_DIR
from ..core.export_import import export_selected_with_textures
from ..core.thumbnail import render_thumbnail_for_object
from ..core.database import db_insert_or_update_by_uuid
from ..properties.scene_props import load_assets_to_scene

class ASSETMANAGER_OT_register(bpy.types.Operator):
    bl_idname = "assetmanager.register"
    bl_label = "Register Selected to Database"
    bl_description = "Export selected object, render thumbnail, input metadata, and register to SQLite"
    bl_options = {'REGISTER', 'UNDO'}

    asset_name: bpy.props.StringProperty(name="Asset Name", description="Nama asset")
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
    description: bpy.props.StringProperty(name="Description", description="Deskripsi asset")
    file_format: bpy.props.EnumProperty(
        name="Export Format",
        items=[
            ('FBX','FBX (.fbx)',''),
            ('BLEND','BLEND (.blend)',''),
        ],
        
        default='FBX'
    )

    def invoke(self, context, event):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "Tidak ada object yang dipilih.")
            return {'CANCELLED'}
        self.asset_name = obj.name
        self.description = f"Auto-generated from {obj.name}"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "asset_name")
        layout.prop(self, "category")
        layout.prop(self, "description")
        layout.prop(self, "file_format")

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "Tidak ada object yang dipilih!")
            return {'CANCELLED'}
        if obj.type != 'MESH':
            self.report({'WARNING'}, "Object yang dipilih bukan tipe MESH!")
            return {'CANCELLED'}

        try:
            # 1. Export file
            asset_uuid = str(uuid.uuid4())
            fpath = export_selected_with_textures(
            obj,
            EXPORTS_DIR,
            self.file_format,
            force_name=asset_uuid   # ← nama file = uuid
        )

            # 2. Hitung statistik
            poly_count = len(obj.data.polygons)
            vertices = len(obj.data.vertices)
            faces = len(obj.data.polygons)
            file_size = os.path.getsize(fpath)

            # 3. Buat path thumbnail
            thumb_path = os.path.join(THUMBS_DIR, f"{asset_uuid}.png")

            # 4. Render thumbnail
            render_thumbnail_for_object(obj, thumb_path, size=(256,256))

            # 5. Simpan/update DB
            inserted = db_insert_or_update_by_uuid(
                asset_uuid,
                self.asset_name,
                self.category,
                self.description,
                fpath,
                thumb_path,
                poly_count,
                vertices,
                faces,
                file_size
            )

            # 6. Refresh UI
            load_assets_to_scene(context)

            if inserted:
                self.report({'INFO'}, f"Asset '{self.asset_name}' berhasil diregistrasi.")
            else:
                self.report({'INFO'}, f"Asset '{self.asset_name}' berhasil diperbarui.")

        except Exception as e:
            self.report({'ERROR'}, f"Kesalahan: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}