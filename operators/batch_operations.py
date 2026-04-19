"""
Batch Operations — Asset Manager
Provides batch load, export, and delete for multiple selected assets.

Selection state is stored in a module-level set so any part of the addon
can read / write it without needing a Blender scene property.
"""

import bpy
import os
from bpy.props import BoolProperty, StringProperty

# ─────────────────────────────────────────────────────────────────────────────
#  SELECTION STATE  (module-level, avoids polluting bpy.types.Scene)
# ─────────────────────────────────────────────────────────────────────────────

# Set of asset IDs (int) currently selected for batch ops
_selected_ids: set = set()


def get_selected_ids() -> set:
    return _selected_ids


def is_selected(asset_id: int) -> bool:
    return asset_id in _selected_ids


def set_selected(asset_id: int, value: bool):
    if value:
        _selected_ids.add(asset_id)
    else:
        _selected_ids.discard(asset_id)


def clear_selection():
    _selected_ids.clear()


def select_all(asset_ids):
    _selected_ids.update(asset_ids)


# ─────────────────────────────────────────────────────────────────────────────
#  TOGGLE SELECTION OPERATOR
# ─────────────────────────────────────────────────────────────────────────────

class ASSETMANAGER_OT_batch_toggle_select(bpy.types.Operator):
    """Toggle selection of a single asset for batch operations"""
    bl_idname  = "assetmanager.batch_toggle_select"
    bl_label   = "Toggle Select"
    bl_options = {'INTERNAL'}

    asset_id: bpy.props.IntProperty()

    def execute(self, context):
        set_selected(self.asset_id, not is_selected(self.asset_id))
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


class ASSETMANAGER_OT_batch_select_all(bpy.types.Operator):
    """Select / deselect all visible assets"""
    bl_idname  = "assetmanager.batch_select_all"
    bl_label   = "Select All"
    bl_options = {'INTERNAL'}

    # IDs passed as comma-separated string (Blender props can't take lists)
    asset_ids: StringProperty(default="")
    select:    BoolProperty(default=True)

    def execute(self, context):
        ids = [int(x) for x in self.asset_ids.split(",") if x.strip()]
        if self.select:
            select_all(ids)
        else:
            clear_selection()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


class ASSETMANAGER_OT_batch_clear_selection(bpy.types.Operator):
    """Clear all batch selections"""
    bl_idname  = "assetmanager.batch_clear_selection"
    bl_label   = "Clear Selection"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        clear_selection()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  BATCH LOAD
# ─────────────────────────────────────────────────────────────────────────────

class ASSETMANAGER_OT_batch_load(bpy.types.Operator):
    """Load all selected assets into the current scene"""
    bl_idname      = "assetmanager.batch_load"
    bl_label       = "Batch Load"
    bl_description = "Import all selected assets into the current scene"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(_selected_ids) and context.mode == 'OBJECT'

    def execute(self, context):
        from ..core.database    import db_get_by_id
        from ..core.export_import import import_file_auto

        ids = list(_selected_ids)
        ok, fail = [], []

        for asset_id in ids:
            asset = db_get_by_id(asset_id)
            if not asset:
                fail.append(str(asset_id))
                continue

            file_path = asset.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                fail.append(asset.get('name', str(asset_id)))
                continue

            try:
                imported = import_file_auto(file_path)
                if imported:
                    ok.append(asset['name'])
                else:
                    fail.append(asset['name'])
            except Exception as e:
                print(f"[AssetManager] Batch load error for '{asset.get('name')}': {e}")
                fail.append(asset.get('name', str(asset_id)))

        msg = f"Loaded {len(ok)} asset(s)"
        if fail:
            msg += f" | Failed: {len(fail)} ({', '.join(fail[:3])}{'...' if len(fail) > 3 else ''})"
        self.report({'INFO'} if not fail else {'WARNING'}, msg)

        clear_selection()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  BATCH EXPORT
# ─────────────────────────────────────────────────────────────────────────────

class ASSETMANAGER_OT_batch_export(bpy.types.Operator):
    """Export all selected assets to a chosen folder"""
    bl_idname      = "assetmanager.batch_export"
    bl_label       = "Batch Export"
    bl_description = "Copy asset files for all selected assets to a folder"
    bl_options     = {'REGISTER'}

    directory: StringProperty(
        name="Export Directory",
        description="Folder to export assets into",
        subtype='DIR_PATH',
    )

    @classmethod
    def poll(cls, context):
        return bool(_selected_ids)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import shutil
        from ..core.database import db_get_by_id

        dest_dir = self.directory
        if not dest_dir or not os.path.isdir(dest_dir):
            self.report({'ERROR'}, "Invalid export directory")
            return {'CANCELLED'}

        ids = list(_selected_ids)
        ok, fail = [], []

        for asset_id in ids:
            asset = db_get_by_id(asset_id)
            if not asset:
                fail.append(str(asset_id))
                continue

            file_path = asset.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                fail.append(asset.get('name', str(asset_id)))
                continue

            try:
                dest_path = os.path.join(dest_dir, os.path.basename(file_path))
                # Avoid overwriting — add suffix if needed
                base, ext = os.path.splitext(dest_path)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = f"{base}_{counter}{ext}"
                    counter += 1

                shutil.copy2(file_path, dest_path)
                ok.append(asset['name'])
            except Exception as e:
                print(f"[AssetManager] Batch export error for '{asset.get('name')}': {e}")
                fail.append(asset.get('name', str(asset_id)))

        msg = f"Exported {len(ok)} file(s) to {dest_dir}"
        if fail:
            msg += f" | Failed: {len(fail)}"
        self.report({'INFO'} if not fail else {'WARNING'}, msg)

        clear_selection()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  BATCH DELETE
# ─────────────────────────────────────────────────────────────────────────────

class ASSETMANAGER_OT_batch_delete(bpy.types.Operator):
    """Delete all selected assets from the library"""
    bl_idname      = "assetmanager.batch_delete"
    bl_label       = "Batch Delete"
    bl_description = "Remove all selected assets from the library"
    bl_options     = {'REGISTER', 'UNDO'}

    delete_files: BoolProperty(
        name="Delete Files from Disk",
        description="Also delete the actual asset files from your hard drive",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return bool(_selected_ids)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        layout = self.layout
        count = len(_selected_ids)

        box = layout.box()
        row = box.row()
        row.alert = True
        row.label(text=f"Delete {count} asset(s)?", icon='ERROR')
        box.label(text="This cannot be undone!", icon='INFO')
        layout.separator(factor=0.5)
        layout.prop(self, "delete_files")

    def execute(self, context):
        from ..core.database    import db_get_by_id, db_delete_by_id
        from ..core.scene_assets import remove_single_asset_from_scene, refresh_current_page
        from ..core.preview     import unload_preview

        ids = list(_selected_ids)
        ok, fail = [], []

        for asset_id in ids:
            asset = db_get_by_id(asset_id)
            if not asset:
                continue

            try:
                db_delete_by_id(asset_id)

                # Optionally remove files
                if self.delete_files:
                    for path_key in ('file_path', 'thumbnail_path'):
                        p = asset.get(path_key)
                        if p and os.path.exists(p):
                            try:
                                os.remove(p)
                            except Exception as e:
                                print(f"[AssetManager] Could not delete file {p}: {e}")

                # Unload preview cache (pass full asset to handle versioned keys)
                try:
                    unload_preview(asset)
                except Exception:
                    pass

                ok.append(asset['name'])
            except Exception as e:
                print(f"[AssetManager] Batch delete error for id={asset_id}: {e}")
                fail.append(asset.get('name', str(asset_id)))

        msg = f"Deleted {len(ok)} asset(s)"
        if fail:
            msg += f" | Failed: {len(fail)} items"
        
        self.report({'INFO'} if not fail else {'WARNING'}, msg)

        clear_selection()
        # Reload catalog page if open
        try:
            from .show_catalog import _CATALOG_REF
            if _CATALOG_REF:
                op = _CATALOG_REF[0]
                op._load_page()
            
            # Sync with Sidebar / N-Panel list
            refresh_current_page(context)
        except Exception:
            pass

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTER
# ─────────────────────────────────────────────────────────────────────────────

classes = (
    ASSETMANAGER_OT_batch_toggle_select,
    ASSETMANAGER_OT_batch_select_all,
    ASSETMANAGER_OT_batch_clear_selection,
    ASSETMANAGER_OT_batch_load,
    ASSETMANAGER_OT_batch_export,
    ASSETMANAGER_OT_batch_delete,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
