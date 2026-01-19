import bpy
from .database import db_get_all
from .preview import load_previews_for_assets

def load_assets_to_scene(context):
    scene = context.scene
    scene.asset_items.clear()

    assets = db_get_all()
    load_previews_for_assets(assets)

    search = (scene.asset_search or "").lower()
    cat = (scene.asset_category or "ALL").upper()

    min_size = scene.filter_min_size * 1024
    max_size = scene.filter_max_size * 1024
    min_poly = scene.filter_min_poly
    max_poly = scene.filter_max_poly

    for a in assets:
        name = a.get("name", "")
        category = (a.get("category") or "").upper()
        size = a.get("file_size") or 0
        poly = a.get("poly_count") or 0

        if search and search not in name.lower():
            continue
        if cat != "ALL" and category != cat:
            continue
        if min_size and size < min_size:
            continue
        if max_size and size > max_size:
            continue
        if min_poly and poly < min_poly:
            continue
        if max_poly and poly > max_poly:
            continue

        item = scene.asset_items.add()
        item.id = a["id"]
        item.name = name
        item.category = a.get("category", "")
        item.description = a.get("description", "")
        item.file_path = a.get("file_path", "")
        item.file_size = size
        item.poly_count = poly
        item.vertices = a.get("vertices", 0)
        item.faces = a.get("faces", 0)
        item.created_at = a.get("created_at", "")
        item.updated_at = a.get("updated_at", "")
        item.preview_icon = f"asset_{a['id']}"

    if scene.asset_index >= len(scene.asset_items):
       scene.asset_index = min(scene.asset_index, len(scene.asset_items) - 1)