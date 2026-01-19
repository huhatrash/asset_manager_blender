import bpy
import os
from ..core.database import db_get_all

preview_collection = None
def load_previews_for_assets(assets):
    global preview_collection

    if preview_collection is None:
        preview_collection = bpy.utils.previews.new()

    for a in assets:
        key = f"asset_{a['id']}"
        thumb = a.get("thumbnail_path")

        if not thumb or not os.path.exists(thumb):
            continue

        if key in preview_collection:
            try:
                preview_collection.remove(key)
            except Exception:
                pass

        try:
            preview_collection.load(key, thumb, 'IMAGE')
        except Exception as e:
            print("Preview load error:", e)

    return preview_collection

def refresh_asset_preview(asset_id, thumb_path):
    # ===== FORCE FULL PREVIEW RELOAD =====
    global preview_collection
    if preview_collection:
        bpy.utils.previews.remove(preview_collection)
        preview_collection = None

    load_previews_for_assets(db_get_all())

    key = f"asset_{asset_id}"

    if preview_collection:
        if key in preview_collection:
            try:
                preview_collection.remove(key)
            except Exception:
                pass

        try:
            preview_collection.load(key, thumb_path, 'IMAGE')
        except Exception as e:
            print("Preview reload error:", e)

def update_preview(self, context):
    idx = context.scene.asset_index
    if idx >= 0 and idx < len(context.scene.asset_items):
        item = context.scene.asset_items[idx]
        context.scene.asset_preview = item.preview_icon