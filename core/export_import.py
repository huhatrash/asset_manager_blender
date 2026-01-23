"""
Export/Import Module - Asset Manager
Handles asset file export and import operations.

Author: alfa haliza
Version: 2.0
"""

import bpy
import os
from .paths import get_exports_dir, get_safe_filename, get_unique_filepath


# =====================================================
# EXPORT FUNCTIONS
# =====================================================

def export_selected_to_fbx(obj, output_dir, filename=None):
    """
    Export selected object to FBX format.
    
    Args:
        obj (bpy.types.Object): Object to export
        output_dir (str): Output directory
        filename (str): Output filename (optional, uses object name if None)
    
    Returns:
        str: Path to exported file, or None if failed
    """
    if not obj:
        print("[AssetManager] No object provided for export")
        return None
    
    # Generate filename
    if not filename:
        filename = get_safe_filename(obj.name, '.fbx')
    elif not filename.endswith('.fbx'):
        filename += '.fbx'
    
    # Get full output path
    output_path = os.path.join(output_dir, filename)
    output_path = get_unique_filepath(output_dir, filename)
    
    # Store current selection
    original_selection = bpy.context.selected_objects.copy()
    original_active = bpy.context.view_layer.objects.active
    
    try:
        # Select only target object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Export FBX
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=True,
            global_scale=1.0,
            apply_scale_options='FBX_SCALE_NONE',
            axis_forward='-Z',
            axis_up='Y',
            object_types={'MESH'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            use_tspace=True,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            path_mode='COPY',
            embed_textures=True
        )
        
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selection:
            if o:
                o.select_set(True)
        if original_active:
            bpy.context.view_layer.objects.active = original_active
        
        if os.path.exists(output_path):
            print(f"[AssetManager] Exported to: {output_path}")
            return output_path
        else:
            print(f"[AssetManager] Export failed: file not created")
            return None
            
    except Exception as e:
        print(f"[AssetManager] Export error: {e}")
        
        # Restore selection on error
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for o in original_selection:
                if o:
                    o.select_set(True)
            if original_active:
                bpy.context.view_layer.objects.active = original_active
        except:
            pass
        
        return None


def export_selected_to_blend(obj, output_dir, filename=None):
    """
    Export selected object to .blend format.
    
    Args:
        obj (bpy.types.Object): Object to export
        output_dir (str): Output directory
        filename (str): Output filename (optional)
    
    Returns:
        str: Path to exported file, or None if failed
    """
    if not obj:
        print("[AssetManager] No object provided for export")
        return None
    
    # Generate filename
    if not filename:
        filename = get_safe_filename(obj.name, '.blend')
    elif not filename.endswith('.blend'):
        filename += '.blend'
    
    # Get full output path
    output_path = get_unique_filepath(output_dir, filename)
    
    # Store current selection
    original_selection = bpy.context.selected_objects.copy()
    
    try:
        # Select only target object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        
        # Save as blend file
        bpy.data.libraries.write(
            output_path,
            {obj},
            compress=True
        )
        
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selection:
            if o:
                o.select_set(True)
        
        if os.path.exists(output_path):
            print(f"[AssetManager] Exported to: {output_path}")
            return output_path
        else:
            print(f"[AssetManager] Export failed: file not created")
            return None
            
    except Exception as e:
        print(f"[AssetManager] Export error: {e}")
        
        # Restore selection on error
        try:
            bpy.ops.object.select_all(action='DESELECT')
            for o in original_selection:
                if o:
                    o.select_set(True)
        except:
            pass
        
        return None


def export_selected_with_textures(obj, output_dir, file_format='FBX', force_name=None):
    """
    Export object with textures embedded/packed.
    
    Args:
        obj (bpy.types.Object): Object to export
        output_dir (str): Output directory
        file_format (str): 'FBX' or 'BLEND'
        force_name (str): Force specific filename (without extension)
    
    Returns:
        str: Path to exported file
    """
    # Determine filename
    if force_name:
        base_name = force_name
    else:
        base_name = obj.name
    
    # Export based on format
    if file_format == 'FBX':
        filename = get_safe_filename(base_name, '.fbx')
        return export_selected_to_fbx(obj, output_dir, filename)
    elif file_format == 'BLEND':
        filename = get_safe_filename(base_name, '.blend')
        return export_selected_to_blend(obj, output_dir, filename)
    else:
        print(f"[AssetManager] Unsupported export format: {file_format}")
        return None


# =====================================================
# IMPORT FUNCTIONS
# =====================================================

def import_fbx_file(filepath, use_custom_props=True):
    """
    Import FBX file into current scene.
    
    Args:
        filepath (str): Path to FBX file
        use_custom_props (bool): Import custom properties
    
    Returns:
        list: Imported objects
    """
    if not os.path.exists(filepath):
        print(f"[AssetManager] File not found: {filepath}")
        return []
    
    # Store objects before import
    objects_before = set(bpy.data.objects)
    
    try:
        bpy.ops.import_scene.fbx(
            filepath=filepath,
            use_custom_props=use_custom_props,
            use_custom_normals=True,
            use_image_search=True,
            ignore_leaf_bones=True,
            force_connect_children=False,
            automatic_bone_orientation=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X'
        )
        
        # Get newly imported objects
        objects_after = set(bpy.data.objects)
        imported_objects = list(objects_after - objects_before)
        
        print(f"[AssetManager] Imported {len(imported_objects)} objects from FBX")
        return imported_objects
        
    except Exception as e:
        print(f"[AssetManager] FBX import error: {e}")
        return []


def import_blend_file(filepath, link=False):
    """
    Import objects from .blend file.
    
    Args:
        filepath (str): Path to .blend file
        link (bool): Link instead of append
    
    Returns:
        list: Imported objects
    """
    if not os.path.exists(filepath):
        print(f"[AssetManager] File not found: {filepath}")
        return []
    
    # Store objects before import
    objects_before = set(bpy.data.objects)
    
    try:
        # Construct directory path for append/link
        directory = os.path.join(filepath, "Object")
        
        # Get list of objects in the blend file
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            object_names = data_from.objects
        
        # Import each object
        for obj_name in object_names:
            if link:
                bpy.ops.wm.link(
                    directory=directory,
                    filename=obj_name
                )
            else:
                bpy.ops.wm.append(
                    directory=directory,
                    filename=obj_name
                )
        
        # Get newly imported objects
        objects_after = set(bpy.data.objects)
        imported_objects = list(objects_after - objects_before)
        
        print(f"[AssetManager] Imported {len(imported_objects)} objects from .blend")
        return imported_objects
        
    except Exception as e:
        print(f"[AssetManager] .blend import error: {e}")
        return []


def import_obj_file(filepath):
    """
    Import OBJ file into current scene.
    
    Args:
        filepath (str): Path to OBJ file
    
    Returns:
        list: Imported objects
    """
    if not os.path.exists(filepath):
        print(f"[AssetManager] File not found: {filepath}")
        return []
    
    # Store objects before import
    objects_before = set(bpy.data.objects)
    
    try:
        bpy.ops.import_scene.obj(
            filepath=filepath,
            use_split_objects=True,
            use_split_groups=False,
            use_image_search=True
        )
        
        # Get newly imported objects
        objects_after = set(bpy.data.objects)
        imported_objects = list(objects_after - objects_before)
        
        print(f"[AssetManager] Imported {len(imported_objects)} objects from OBJ")
        return imported_objects
        
    except Exception as e:
        print(f"[AssetManager] OBJ import error: {e}")
        return []


def import_file_auto(filepath):
    """
    Auto-detect file type and import.
    
    Args:
        filepath (str): Path to file
    
    Returns:
        list: Imported objects
    """
    if not os.path.exists(filepath):
        print(f"[AssetManager] File not found: {filepath}")
        return []
    
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == '.fbx':
        return import_fbx_file(filepath)
    elif ext == '.blend':
        return import_blend_file(filepath)
    elif ext == '.obj':
        return import_obj_file(filepath)
    else:
        print(f"[AssetManager] Unsupported file format: {ext}")
        return []


# =====================================================
# BATCH OPERATIONS
# =====================================================

def export_multiple_objects(objects, output_dir, file_format='FBX'):
    """
    Export multiple objects at once.
    
    Args:
        objects (list): List of objects to export
        output_dir (str): Output directory
        file_format (str): Export format
    
    Returns:
        dict: Export results
    """
    results = {
        'successful': [],
        'failed': []
    }
    
    for obj in objects:
        try:
            filepath = export_selected_with_textures(obj, output_dir, file_format)
            
            if filepath:
                results['successful'].append({
                    'object': obj.name,
                    'path': filepath
                })
            else:
                results['failed'].append(obj.name)
                
        except Exception as e:
            print(f"[AssetManager] Failed to export {obj.name}: {e}")
            results['failed'].append(obj.name)
    
    return results


def import_multiple_files(filepaths):
    """
    Import multiple files at once.
    
    Args:
        filepaths (list): List of file paths
    
    Returns:
        dict: Import results
    """
    results = {
        'successful': [],
        'failed': [],
        'total_objects': 0
    }
    
    for filepath in filepaths:
        try:
            imported = import_file_auto(filepath)
            
            if imported:
                results['successful'].append({
                    'file': filepath,
                    'objects': [obj.name for obj in imported]
                })
                results['total_objects'] += len(imported)
            else:
                results['failed'].append(filepath)
                
        except Exception as e:
            print(f"[AssetManager] Failed to import {filepath}: {e}")
            results['failed'].append(filepath)
    
    return results


# =====================================================
# VALIDATION
# =====================================================

def validate_export_path(filepath):
    """
    Validate if export path is writable.
    
    Args:
        filepath (str): Path to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    directory = os.path.dirname(filepath)
    
    if not directory:
        return False, "Invalid directory"
    
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create directory: {e}"
    
    if not os.access(directory, os.W_OK):
        return False, "Directory is not writable"
    
    # Check if file already exists
    if os.path.exists(filepath):
        if not os.access(filepath, os.W_OK):
            return False, "File exists and is not writable"
    
    return True, ""


def validate_import_file(filepath):
    """
    Validate if file can be imported.
    
    Args:
        filepath (str): Path to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not filepath:
        return False, "No file path provided"
    
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    if not os.path.isfile(filepath):
        return False, "Path is not a file"
    
    ext = os.path.splitext(filepath)[1].lower()
    supported_formats = ['.fbx', '.blend', '.obj', '.gltf', '.glb']
    
    if ext not in supported_formats:
        return False, f"Unsupported format: {ext}"
    
    # Check file size (warn if very large)
    file_size = os.path.getsize(filepath)
    if file_size > 500 * 1024 * 1024:  # 500MB
        return True, "Warning: File is very large (>500MB)"
    
    return True, ""


# =====================================================
# UTILITIES
# =====================================================

def get_object_file_size_estimate(obj):
    """
    Estimate export file size for an object.
    
    Args:
        obj (bpy.types.Object): Object to estimate
    
    Returns:
        int: Estimated size in bytes
    """
    if not obj or obj.type != 'MESH':
        return 0
    
    mesh = obj.data
    
    # Rough estimate based on geometry
    vertex_count = len(mesh.vertices)
    poly_count = len(mesh.polygons)
    
    # Average: 50 bytes per vertex, 30 bytes per polygon
    estimated_size = (vertex_count * 50) + (poly_count * 30)
    
    # Add estimate for materials/textures
    if obj.data.materials:
        estimated_size += len(obj.data.materials) * 1024  # 1KB per material
    
    return estimated_size


def cleanup_imported_objects(objects):
    """
    Clean up imported objects (remove empties, fix names, etc.).
    
    Args:
        objects (list): List of imported objects
    
    Returns:
        list: Cleaned objects
    """
    cleaned = []
    
    for obj in objects:
        # Skip empties
        if obj.type == 'EMPTY':
            continue
        
        # Fix names (remove .001 suffixes if needed)
        if obj.name.endswith('.001'):
            base_name = obj.name[:-4]
            obj.name = base_name
        
        cleaned.append(obj)
    
    return cleaned