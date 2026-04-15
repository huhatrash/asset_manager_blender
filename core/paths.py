"""
Paths Module - Asset Manager
Centralized path management for addon directories and files.

Author: alfa haliza
Version: 2.0
"""

import os
import bpy


# =====================================================
# ADDON PATHS
# =====================================================

def get_addon_dir():
    """
    Get the addon's root directory.
    
    Returns:
        str: Absolute path to addon directory
    """
    # Get the directory containing this file (core/)
    current_file = os.path.abspath(__file__)
    core_dir = os.path.dirname(current_file)
    
    # Go up one level to addon root
    addon_dir = os.path.dirname(core_dir)
    
    return addon_dir


def get_data_dir():
    """
    Get the main data directory for asset manager.
    Located in Blender's user config directory.
    
    Returns:
        str: Absolute path to data directory
    """
    # Use Blender's user config path
    blender_config = bpy.utils.user_resource('CONFIG')
    data_dir = os.path.join(blender_config, "asset_manager_data")
    
    # Create if doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    return data_dir


# =====================================================
# SUBDIRECTORIES
# =====================================================

def get_exports_dir():
    """
    Get directory for exported asset files.
    
    Returns:
        str: Path to exports directory
    """
    exports_dir = os.path.join(get_data_dir(), "exports")
    
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir, exist_ok=True)
    
    return exports_dir


def get_thumbnails_dir():
    """
    Get directory for thumbnail images.
    
    Returns:
        str: Path to thumbnails directory
    """
    thumbs_dir = os.path.join(get_data_dir(), "thumbnails")
    
    if not os.path.exists(thumbs_dir):
        os.makedirs(thumbs_dir, exist_ok=True)
    
    return thumbs_dir


def get_temp_dir():
    """
    Get directory for temporary files.
    
    Returns:
        str: Path to temp directory
    """
    temp_dir = os.path.join(get_data_dir(), "temp")
    
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)
    
    return temp_dir


def get_backups_dir():
    """
    Get directory for database backups.
    
    Returns:
        str: Path to backups directory
    """
    backups_dir = os.path.join(get_data_dir(), "backups")
    
    if not os.path.exists(backups_dir):
        os.makedirs(backups_dir, exist_ok=True)
    
    return backups_dir


# =====================================================
# FILE PATHS
# =====================================================

def get_database_path():
    """
    Get path to SQLite database file.
    
    Returns:
        str: Path to database file
    """
    return os.path.join(get_data_dir(), "assets.db")


def get_log_path():
    """
    Get path to log file.
    
    Returns:
        str: Path to log file
    """
    return os.path.join(get_data_dir(), "asset_manager.log")


def get_config_path():
    """
    Get path to config file (for future use).
    
    Returns:
        str: Path to config file
    """
    return os.path.join(get_data_dir(), "config.json")


# =====================================================
# CONVENIENCE ACCESSORS (backward compatibility)
# =====================================================
# IMPORTANT: These are *functions*, not module-level constants.
# Calling bpy.utils.user_resource() at import time (before Blender is
# fully initialised) can return the wrong path, making the database
# appear empty.  Always call the functions; never cache the results at
# module scope.

def ADDON_DIR():    return get_addon_dir()
def DATA_DIR():     return get_data_dir()
def EXPORTS_DIR():  return get_exports_dir()
def THUMBS_DIR():   return get_thumbnails_dir()
def DB_PATH():      return get_database_path()
def TEMP_DIR():     return get_temp_dir()
def BACKUPS_DIR():  return get_backups_dir()


# =====================================================
# PATH UTILITIES
# =====================================================

def ensure_directory_exists(path):
    """
    Ensure a directory exists, create if needed.
    
    Args:
        path (str): Directory path
    
    Returns:
        bool: True if directory exists or was created
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"[AssetManager] Failed to create directory {path}: {e}")
        return False


def get_safe_filename(name, extension=""):
    """
    Convert name to safe filename (remove invalid characters).
    
    Args:
        name (str): Original name
        extension (str): File extension (with or without dot)
    
    Returns:
        str: Safe filename
    """
    import re
    
    # Remove invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    
    # Limit length
    safe_name = safe_name[:200]
    
    # Add extension
    if extension:
        if not extension.startswith('.'):
            extension = '.' + extension
        safe_name += extension
    
    return safe_name


def get_unique_filepath(directory, filename):
    """
    Get unique filepath by appending number if file exists.
    
    Args:
        directory (str): Directory path
        filename (str): Desired filename
    
    Returns:
        str: Unique filepath
    """
    base_path = os.path.join(directory, filename)
    
    if not os.path.exists(base_path):
        return base_path
    
    # Split name and extension
    name, ext = os.path.splitext(filename)
    
    # Try appending numbers
    counter = 1
    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        
        if not os.path.exists(new_path):
            return new_path
        
        counter += 1
        
        # Safety limit
        if counter > 9999:
            import uuid
            new_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            return os.path.join(directory, new_filename)


def get_relative_path(filepath, base_dir=None):
    """
    Get relative path from base directory.
    
    Args:
        filepath (str): Absolute file path
        base_dir (str): Base directory (default: data dir)
    
    Returns:
        str: Relative path or original if not under base_dir
    """
    if base_dir is None:
        base_dir = get_data_dir()
    
    try:
        return os.path.relpath(filepath, base_dir)
    except ValueError:
        # Different drives on Windows
        return filepath


def normalize_path(path):
    """
    Normalize path (resolve .., ., convert slashes).
    
    Args:
        path (str): Path to normalize
    
    Returns:
        str: Normalized absolute path
    """
    return os.path.normpath(os.path.abspath(path))


# =====================================================
# CLEANUP UTILITIES
# =====================================================

def cleanup_temp_files():
    """
    Clean up temporary files older than 24 hours.
    
    Returns:
        int: Number of files deleted
    """
    import time
    
    temp_dir = get_temp_dir()
    if not os.path.exists(temp_dir):
        return 0
    
    deleted = 0
    now = time.time()
    max_age = 24 * 60 * 60  # 24 hours in seconds
    
    try:
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                
                if file_age > max_age:
                    try:
                        os.remove(filepath)
                        deleted += 1
                    except Exception as e:
                        print(f"[AssetManager] Failed to delete temp file {filepath}: {e}")
    
    except Exception as e:
        print(f"[AssetManager] Temp cleanup error: {e}")
    
    return deleted


def get_directory_size(directory):
    """
    Calculate total size of directory.
    
    Args:
        directory (str): Directory path
    
    Returns:
        int: Total size in bytes
    """
    total_size = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"[AssetManager] Error calculating directory size: {e}")
    
    return total_size


def get_storage_info():
    """
    Get storage information about asset manager data.
    
    Returns:
        dict: Storage statistics
    """
    return {
        'exports_size': get_directory_size(get_exports_dir()),
        'thumbnails_size': get_directory_size(get_thumbnails_dir()),
        'temp_size': get_directory_size(get_temp_dir()),
        'backups_size': get_directory_size(get_backups_dir()),
        'total_size': get_directory_size(get_data_dir()),
    }


# =====================================================
# INITIALIZATION
# =====================================================

def init_directories():
    """
    Initialize all required directories.
    Called on addon registration.
    
    Returns:
        bool: True if all directories created successfully
    """
    directories = [
        get_data_dir(),
        get_exports_dir(),
        get_thumbnails_dir(),
        get_temp_dir(),
        get_backups_dir(),
    ]
    
    success = True
    for directory in directories:
        if not ensure_directory_exists(directory):
            success = False
    
    return success


# =====================================================
# PATH VALIDATION
# =====================================================

def is_valid_asset_path(filepath):
    """
    Check if filepath is valid for asset storage.
    
    Args:
        filepath (str): Path to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not filepath:
        return False, "Path is empty"
    
    if not os.path.isabs(filepath):
        return False, "Path must be absolute"
    
    # Check if file exists
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    # Check if it's a file (not directory)
    if not os.path.isfile(filepath):
        return False, "Path is not a file"
    
    # Check extension
    valid_extensions = ['.fbx', '.blend', '.obj', '.gltf', '.glb']
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext not in valid_extensions:
        return False, f"Unsupported file type: {ext}"
    
    return True, ""


# =====================================================
# AUTO CLEANUP ON MODULE LOAD
# =====================================================

# NOTE: Temp cleanup is intentionally NOT called at module import time.
# It is called explicitly from register() in __init__.py to ensure
# bpy is fully ready before any path resolution occurs.