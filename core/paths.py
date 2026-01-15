import os

USER_DIR = os.path.expanduser("~/Documents/blender_assets")
DATA_DIR = os.path.join(USER_DIR, "data")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
THUMBS_DIR = os.path.join(DATA_DIR, "thumbs")
DB_PATH = os.path.join(USER_DIR, "assets.db")

def ensure_dirs():
    for p in (USER_DIR, DATA_DIR, EXPORTS_DIR, THUMBS_DIR):
        os.makedirs(p, exist_ok=True)
