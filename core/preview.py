"""
Preview Module - Asset Manager
Handles thumbnail/preview loading and caching.

Author: alfa haliza
Version: 2.0 (Optimized with Lazy Loading)
"""

import bpy
import os

# Global preview collection
_preview_collection = None


# =====================================================
# COLLECTION MANAGEMENT
# =====================================================

def get_preview_collection():
    """
    Get or create the global preview collection.
    
    Returns:
        bpy.utils.previews.ImagePreviewCollection: Preview collection
    """
    global _preview_collection

    if _preview_collection is None:
        _preview_collection = bpy.utils.previews.new()

    return _preview_collection


def clear_previews():
    """
    Clear all previews and free memory.
    Called on addon unregister.
    """
    global _preview_collection

    if _preview_collection:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None


# =====================================================
# LOADING FUNCTIONS
# =====================================================

def load_preview_for_single_asset(asset, force_reload=False):
    """
    Load preview for a single asset (lazy loading).
    """
    if not asset:
        return None
    
    pcoll = get_preview_collection()
    key = f"asset_{asset['uuid']}"
    thumbnail_path = asset.get('thumbnail_path')
    
    # Check if thumbnail path exists
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        return None
    
    # Safe pop for force reload
    if force_reload and key in pcoll:
        try:
            pcoll.pop(key)
        except Exception:
            pass
            
    # Check if already loaded
    if key in pcoll:
        return pcoll[key]
    
    # Load new preview
    try:
        preview = pcoll.load(key, thumbnail_path, 'IMAGE')
        return preview
    except Exception as e:
        print(f"[AssetManager] Failed to load preview: {e}")
        return None


def load_previews_for_assets(assets):
    """
    Load previews for multiple assets.
    
    Note: This loads ALL previews immediately. 
    For large asset libraries (1000+), prefer load_preview_for_single_asset().
    
    Args:
        assets (list): List of asset dictionaries
    
    Returns:
        ImagePreviewCollection: Preview collection with loaded previews
    """
    if not assets:
        return get_preview_collection()
    
    pcoll = get_preview_collection()

    for asset in assets:
        key = f"asset_{asset['uuid']}"
        thumbnail_path = asset.get('thumbnail_path')

        # Skip if no path or already loaded
        if not thumbnail_path:
            continue
        
        if not os.path.exists(thumbnail_path):
            continue

        if key in pcoll:
            continue

        # Load preview
        try:
            pcoll.load(key, thumbnail_path, 'IMAGE')
        except Exception as e:
            print(f"[AssetManager] Failed to load preview {key}: {e}")

    return pcoll


def load_previews_batch(assets, start_index=0, count=20):
    """
    Load a batch of previews (for pagination).
    
    Args:
        assets (list): List of asset dictionaries
        start_index (int): Starting index
        count (int): Number of previews to load
    
    Returns:
        int: Number of previews loaded
    """
    pcoll = get_preview_collection()
    loaded = 0
    
    end_index = min(start_index + count, len(assets))
    
    for i in range(start_index, end_index):
        asset = assets[i]
        key = f"asset_{asset['uuid']}"
        thumbnail_path = asset.get('thumbnail_path')
        
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            continue
        
        if key in pcoll:
            continue
        
        try:
            pcoll.load(key, thumbnail_path, 'IMAGE')
            loaded += 1
        except Exception as e:
            print(f"[AssetManager] Batch load failed for {key}: {e}")
    
    return loaded


# =====================================================
# UNLOADING FUNCTIONS
# =====================================================

def unload_preview(asset_uuid):
    """
    Unload a specific preview to free memory.
    
    Args:
        asset_uuid (str): UUID of asset to unload
    
    Returns:
        bool: True if unloaded, False if not found
    """
    pcoll = get_preview_collection()
    key = f"asset_{asset_uuid}"
    
    if key in pcoll:
        try:
            pcoll.pop(key)
            return True
        except Exception as e:
            print(f"[AssetManager] Failed to unload preview {key}: {e}")
            return False
    
    return False


def unload_previews_not_in_list(current_uuids):
    """
    Unload previews that are not in the current list (memory management).
    
    Args:
        current_uuids (set or list): UUIDs of assets to keep
    
    Returns:
        int: Number of previews unloaded
    """
    pcoll = get_preview_collection()
    
    if not pcoll:
        return 0
    
    # Convert to set for O(1) lookup
    current_set = set(current_uuids)
    
    # Find keys to remove
    keys_to_remove = []
    for key in pcoll.keys():
        if key.startswith("asset_"):
            uuid = key.replace("asset_", "")
            if uuid not in current_set:
                keys_to_remove.append(key)
    
    # Remove them
    unloaded = 0
    for key in keys_to_remove:
        try:
            pcoll.pop(key)
            unloaded += 1
        except Exception as e:
            print(f"[AssetManager] Failed to unload {key}: {e}")
    
    return unloaded


def clear_all_asset_previews():
    """
    Clear all asset previews (keeps collection alive).
    Useful for refresh without recreating collection.
    
    Returns:
        int: Number of previews cleared
    """
    pcoll = get_preview_collection()
    
    if not pcoll:
        return 0
    
    # Get all asset preview keys
    asset_keys = [key for key in pcoll.keys() if key.startswith("asset_")]
    
    # Remove them
    cleared = 0
    for key in asset_keys:
        try:
            pcoll.pop(key)
            cleared += 1
        except Exception as e:
            print(f"[AssetManager] Failed to clear {key}: {e}")
    
    return cleared


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def get_preview_by_uuid(asset_uuid):
    """
    Get preview by asset UUID (if loaded).
    
    Args:
        asset_uuid (str): Asset UUID
    
    Returns:
        ImagePreview or None: Preview if loaded, None otherwise
    """
    pcoll = get_preview_collection()
    key = f"asset_{asset_uuid}"
    
    return pcoll.get(key)


def is_preview_loaded(asset_uuid):
    """
    Check if preview is loaded for an asset.
    
    Args:
        asset_uuid (str): Asset UUID
    
    Returns:
        bool: True if loaded, False otherwise
    """
    pcoll = get_preview_collection()
    key = f"asset_{asset_uuid}"
    
    return key in pcoll


def get_loaded_preview_count():
    """
    Get number of currently loaded previews.
    
    Returns:
        int: Number of loaded previews
    """
    pcoll = get_preview_collection()
    
    if not pcoll:
        return 0
    
    # Count only asset previews (exclude other potential previews)
    count = sum(1 for key in pcoll.keys() if key.startswith("asset_"))
    
    return count


def get_preview_memory_estimate():
    """
    Estimate memory used by previews (rough calculation).
    
    Returns:
        int: Estimated memory in bytes
    """
    # Assume average preview is 256x256 RGBA = 256KB
    avg_preview_size = 256 * 256 * 4
    
    count = get_loaded_preview_count()
    
    return count * avg_preview_size


def reload_preview(asset):
    """
    Reload a preview (unload then load again).
    Useful after thumbnail update.
    
    Args:
        asset (dict): Asset data
    
    Returns:
        bool: True if successful
    """
    uuid = asset.get('uuid')
    if not uuid:
        return False
    
    # Unload if exists
    unload_preview(uuid)
    
    # Load fresh
    preview = load_preview_for_single_asset(asset)
    
    return preview is not None


# =====================================================
# PREVIEW CACHE MANAGEMENT
# =====================================================

class PreviewCache:
    """
    Simple LRU cache for preview management.
    Automatically unloads least recently used previews when limit reached.
    """
    
    def __init__(self, max_size=100):
        """
        Initialize preview cache.
        
        Args:
            max_size (int): Maximum number of previews to keep loaded
        """
        self.max_size = max_size
        self.access_order = []  # Track access order
    
    def access(self, asset_uuid):
        """
        Record access to a preview (move to end = most recent).
        
        Args:
            asset_uuid (str): Asset UUID
        """
        # Remove if exists
        if asset_uuid in self.access_order:
            self.access_order.remove(asset_uuid)
        
        # Add to end (most recent)
        self.access_order.append(asset_uuid)
        
        # Check if over limit
        if len(self.access_order) > self.max_size:
            # Unload oldest
            oldest_uuid = self.access_order.pop(0)
            unload_preview(oldest_uuid)
    
    def load_with_cache(self, asset):
        """
        Load preview with cache management.
        
        Args:
            asset (dict): Asset data
        
        Returns:
            ImagePreview or None: Loaded preview
        """
        uuid = asset.get('uuid')
        if not uuid:
            return None
        
        # Load preview
        preview = load_preview_for_single_asset(asset)
        
        if preview:
            # Record access
            self.access(uuid)
        
        return preview
    
    def clear(self):
        """Clear cache tracking."""
        self.access_order.clear()


# Global cache instance (optional - can be enabled in preferences)
_preview_cache = None


def get_preview_cache():
    """Get or create global preview cache."""
    global _preview_cache
    
    if _preview_cache is None:
        _preview_cache = PreviewCache(max_size=100)
    
    return _preview_cache


def enable_preview_caching(max_size=100):
    """
    Enable preview caching with LRU eviction.
    
    Args:
        max_size (int): Maximum previews to cache
    """
    global _preview_cache
    _preview_cache = PreviewCache(max_size=max_size)


def disable_preview_caching():
    """Disable preview caching."""
    global _preview_cache
    if _preview_cache:
        _preview_cache.clear()
    _preview_cache = None


# =====================================================
# VALIDATION & DIAGNOSTICS
# =====================================================

def validate_preview_paths(assets):
    """
    Check which assets have valid preview paths.
    
    Args:
        assets (list): List of asset dictionaries
    
    Returns:
        dict: Statistics about preview validity
    """
    total = len(assets)
    valid = 0
    missing = 0
    invalid_path = 0
    
    for asset in assets:
        thumb_path = asset.get('thumbnail_path')
        
        if not thumb_path:
            missing += 1
        elif not os.path.exists(thumb_path):
            invalid_path += 1
        else:
            valid += 1
    
    return {
        'total': total,
        'valid': valid,
        'missing': missing,
        'invalid_path': invalid_path,
        'validity_rate': (valid / total * 100) if total > 0 else 0
    }


def get_preview_info():
    """
    Get information about current preview state.
    
    Returns:
        dict: Preview collection info
    """
    pcoll = get_preview_collection()
    
    info = {
        'loaded_count': get_loaded_preview_count(),
        'memory_estimate_mb': get_preview_memory_estimate() / (1024 * 1024),
        'collection_exists': pcoll is not None,
        'cache_enabled': _preview_cache is not None,
    }
    
    if _preview_cache:
        info['cache_size'] = len(_preview_cache.access_order)
        info['cache_max_size'] = _preview_cache.max_size
    
    return info