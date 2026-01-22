import bpy

from .database import db_get_all
from .preview import load_previews_for_assets


def load_assets_to_scene(context):

    scene = context.scene

    if not hasattr(scene, "asset_items"):
        return

    scene.asset_items.clear()

    assets = db_get_all()

    # Load previews once
    previews = load_previews_for_assets(assets)

    for a in assets:

        item = scene.asset_items.add()

        item.id = a["id"]
        item.uuid = a["uuid"]

        item.name = a.get("name", "")
        item.category = a.get("category", "")
        item.description = a.get("description", "")

        item.file_path = a.get("file_path", "")
        item.file_size = a.get("file_size", 0)

        item.poly_count = a.get("poly_count", 0)
        item.vertices = a.get("vertices", 0)
        item.faces = a.get("faces", 0)

        item.created_at = a.get("created_at", "")
        item.updated_at = a.get("updated_at", "")

        key = f"asset_{a['uuid']}"
        item.preview_icon = key
