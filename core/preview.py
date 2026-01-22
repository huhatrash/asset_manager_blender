import bpy
import os

_preview_collection = None


# ==============================
# GET COLLECTION
# ==============================

def get_preview_collection():
    global _preview_collection

    if _preview_collection is None:
        _preview_collection = bpy.utils.previews.new()

    return _preview_collection


# ==============================
# LOAD PREVIEWS
# ==============================

def load_previews_for_assets(assets):

    pcoll = get_preview_collection()

    for a in assets:

        key = f"asset_{a['uuid']}"
        path = a.get("thumbnail_path")

        if not path:
            continue

        if not os.path.exists(path):
            continue

        if key in pcoll:
            continue

        pcoll.load(key, path, 'IMAGE')

    return pcoll


# ==============================
# CLEAR
# ==============================

def clear_previews():

    global _preview_collection

    if _preview_collection:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None
