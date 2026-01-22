import bpy
import os
import uuid

from ..core.paths import EXPORTS_DIR, THUMBS_DIR
from ..core.export_import import export_selected_with_textures
from ..core.thumbnail import render_thumbnail_for_object
from ..core.database import db_insert_or_update_by_uuid
from ..core.scene_assets import load_assets_to_scene


class ASSETMANAGER_OT_register(bpy.types.Operator):
    bl_idname = "assetmanager.register"
    bl_label = "Register Selected Asset"
    bl_description = "Export selected object, generate thumbnail, and save metadata"
    bl_options = {'REGISTER', 'UNDO'}

    asset_name: bpy.props.StringProperty(
        name="Asset Name",
        default=""
    )

    category: bpy.props.EnumProperty(
        name="Category",
        items=[
            ('model', 'Model', ''),
            ('character', 'Character', ''),
            ('environment', 'Environment', ''),
            ('props', 'Props', ''),
        ],
        default='model'
    )

    description: bpy.props.StringProperty(
        name="Description",
        default=""
    )

    file_format: bpy.props.EnumProperty(
        name="Export Format",
        items=[
            ('FBX', 'FBX (.fbx)', ''),
            ('BLEND', 'BLEND (.blend)', ''),
        ],
        default='FBX'
    )

    # --------------------------------------------------

    def invoke(self, context, event):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}

        self.asset_name = obj.name
        self.description = f"Generated from object '{obj.name}'"
        return context.window_manager.invoke_props_dialog(self)

    # --------------------------------------------------

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "asset_name")
        layout.prop(self, "category")
        layout.prop(self, "description")
        layout.prop(self, "file_format")

    # --------------------------------------------------

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        try:
            # UUID = identity asset
            asset_uuid = str(uuid.uuid4())

            # 1. Export asset
            file_path = export_selected_with_textures(
                obj,
                EXPORTS_DIR,
                file_format=self.file_format,
                force_name=asset_uuid
            )
            asset_uuid = str(uuid.uuid4())

            if not file_path or not os.path.exists(file_path):
                raise RuntimeError("Export failed")

            # 2. Geometry stats
            poly_count = len(obj.data.polygons)
            vertices = len(obj.data.vertices)
            faces = len(obj.data.polygons)
            file_size = os.path.getsize(file_path)

            # 3. Thumbnail
            thumb_path = os.path.join(THUMBS_DIR, f"{asset_uuid}.png")
            render_thumbnail_for_object(obj, thumb_path, size=(256, 256))

            # 4. Save to DB (URUTAN BENAR)
            inserted = db_insert_or_update_by_uuid(
                asset_uuid,
                self.asset_name,
                self.category,
                self.description,
                file_path,
                thumb_path,
                file_size,
                poly_count,
                vertices,
                faces
            )

            # 5. Refresh UI
            load_assets_to_scene(context)

            self.report(
                {'INFO'},
                "Asset registered" if inserted else "Asset updated"
            )

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
