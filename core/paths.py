import bpy
import os

BASE_DIR = bpy.utils.user_resource(
    'CONFIG',
    path="asset_manager",
    create=True
)

DB_PATH = os.path.join(BASE_DIR, "assets.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
THUMBS_DIR = os.path.join(DATA_DIR, "thumbs")

for p in (DATA_DIR, EXPORTS_DIR, THUMBS_DIR):
    os.makedirs(p, exist_ok=True)
