"""
Thumbnail Module - Asset Manager
Advanced thumbnail generation with isolation and material rendering.

Author: alfa haliza
Version: 3.0 (Isolated + Textured)
"""

import bpy
import os
import math
import mathutils


# =====================================================
# MAIN THUMBNAIL GENERATION (ISOLATED & TEXTURED)
# =====================================================

def render_thumbnail_for_object(obj, output_path, size=(256, 256), 
                                samples=64, use_transparent=False):
    """
    Render isolated thumbnail with materials and textures.
    
    Key Features:
    - Object is temporarily duplicated to avoid moving original
    - Isolated at world origin
    - Other objects hidden
    - Materials and textures preserved
    - Smart camera positioning
    
    Args:
        obj (bpy.types.Object): Object to render
        output_path (str): Path to save thumbnail
        size (tuple): Thumbnail dimensions (width, height)
        samples (int): Render samples for quality
        use_transparent (bool): Use transparent background
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not obj or obj.type != 'MESH':
        print(f"[AssetManager] Invalid object for thumbnail: {obj}")
        return False
    
    # Store original settings
    original_scene = bpy.context.scene
    original_active = bpy.context.view_layer.objects.active
    original_selection = bpy.context.selected_objects.copy()
    
    # Store original object state
    original_location = obj.location.copy()
    original_hide_viewport = obj.hide_viewport
    original_hide_render = obj.hide_render
    
    temp_scene = None
    temp_obj = None
    camera = None
    lights = []
    
    try:
        # Create temporary scene for rendering
        temp_scene = bpy.data.scenes.new("ThumbnailScene")
        
        # Link temp scene to view layer
        bpy.context.window.scene = temp_scene
        
        # Setup render settings
        _setup_render_settings(temp_scene, size, samples, use_transparent)
        
        # ✅ DUPLICATE OBJECT (so we don't move the original)
        temp_obj = obj.copy()
        temp_obj.data = obj.data  # Share mesh data (no need to copy)
        
        # Link to temp scene
        temp_scene.collection.objects.link(temp_obj)
        
        # ✅ MOVE DUPLICATE TO WORLD ORIGIN
        temp_obj.location = (0, 0, 0)
        temp_obj.rotation_euler = (0, 0, 0)
        temp_obj.scale = (1, 1, 1)
        
        # Make sure it's visible
        temp_obj.hide_viewport = False
        temp_obj.hide_render = False
        
        # ✅ HIDE ALL OTHER OBJECTS (isolation)
        for other_obj in temp_scene.objects:
            if other_obj != temp_obj:
                other_obj.hide_render = True
        
        # Create and setup camera
        camera = _create_thumbnail_camera(temp_scene, temp_obj)
        
        # Setup 3-point lighting
        lights = _setup_thumbnail_lighting(temp_scene, temp_obj)
        
        # ✅ ENSURE MATERIALS ARE VISIBLE
        _ensure_materials_visible(temp_obj)
        
        # Set output path
        temp_scene.render.filepath = output_path
        
        # Render
        bpy.ops.render.render(write_still=True, scene=temp_scene.name)
        
        # Cleanup
        success = os.path.exists(output_path)
        
        return success
        
    except Exception as e:
        print(f"[AssetManager] Thumbnail generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # ✅ RESTORE ORIGINAL STATE
        try:
            # Switch back to original scene
            bpy.context.window.scene = original_scene
            
            # Restore original object state
            obj.location = original_location
            obj.hide_viewport = original_hide_viewport
            obj.hide_render = original_hide_render
            
            # Restore selection
            bpy.ops.object.select_all(action='DESELECT')
            for o in original_selection:
                if o and o.name in bpy.data.objects:
                    o.select_set(True)
            
            if original_active and original_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = original_active
            
            # Delete temporary objects
            if temp_obj and temp_obj.name in bpy.data.objects:
                bpy.data.objects.remove(temp_obj)
            
            if camera and camera.name in bpy.data.objects:
                bpy.data.objects.remove(camera)
                if camera.data:
                    bpy.data.cameras.remove(camera.data)
            
            for light in lights:
                if light and light.name in bpy.data.objects:
                    light_data = light.data
                    bpy.data.objects.remove(light)
                    if light_data:
                        bpy.data.lights.remove(light_data)
            
            # Delete temporary scene
            if temp_scene and temp_scene.name in bpy.data.scenes:
                bpy.data.scenes.remove(temp_scene)
                
        except Exception as e:
            print(f"[AssetManager] Cleanup error: {e}")


# =====================================================
# RENDER SETUP FUNCTIONS
# =====================================================

def _setup_render_settings(scene, size, samples, use_transparent):
    """Configure render settings for high-quality thumbnail with materials."""
    render = scene.render
    
    # Resolution
    render.resolution_x = size[0]
    render.resolution_y = size[1]
    render.resolution_percentage = 100
    
    # Format
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_mode = 'RGBA' if use_transparent else 'RGB'
    render.image_settings.color_depth = '8'
    render.image_settings.compression = 15
    
    # ✅ USE CYCLES FOR MATERIALS & TEXTURES
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.preview_samples = samples
    
    # ✅ ENABLE DENOISING FOR CLEAN RESULT
    scene.cycles.use_denoising = True
    
    # Performance settings
    if _has_gpu():
        scene.cycles.device = 'GPU'
        # Get GPU preferences
        prefs = bpy.context.preferences.addons.get('cycles')
        if prefs:
            prefs.preferences.compute_device_type = 'CUDA'  # or 'OPTIX' or 'HIP'
    else:
        scene.cycles.device = 'CPU'
    
    # Light paths (for better material rendering)
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 2
    
    # ✅ TRANSPARENT BACKGROUND
    if use_transparent:
        render.film_transparent = True
    else:
        render.film_transparent = False
        
        # Setup world background (neutral gray)
        if not scene.world:
            scene.world = bpy.data.worlds.new("ThumbnailWorld")
        
        scene.world.use_nodes = True
        nodes = scene.world.node_tree.nodes
        
        # Clear existing nodes
        nodes.clear()
        
        # Add background node
        bg_node = nodes.new('ShaderNodeBackground')
        bg_node.inputs[0].default_value = (0.8, 0.8, 0.8, 1.0)  # Light gray
        
        # Add output node
        output_node = nodes.new('ShaderNodeOutputWorld')
        
        # Link
        scene.world.node_tree.links.new(bg_node.outputs[0], output_node.inputs[0])


def _has_gpu():
    """Check if GPU is available for rendering."""
    try:
        prefs = bpy.context.preferences.addons.get('cycles')
        if prefs:
            return len(prefs.preferences.devices) > 0
        return False
    except:
        return False


def _ensure_materials_visible(obj):
    """
    Ensure object materials are set up for rendering.
    Fixes common issues with material visibility.
    """
    if not obj.data.materials:
        # No materials - create a simple white material
        mat = bpy.data.materials.new(name="ThumbnailMaterial")
        mat.use_nodes = True
        
        # Set to white
        nodes = mat.node_tree.nodes
        bsdf = nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
        
        obj.data.materials.append(mat)
    else:
        # Materials exist - ensure they use nodes for Cycles
        for mat in obj.data.materials:
            if mat and not mat.use_nodes:
                mat.use_nodes = True


def _create_thumbnail_camera(scene, obj):
    """
    Create and position camera to frame object perfectly.
    """
    # Create camera
    camera_data = bpy.data.cameras.new("ThumbnailCamera")
    camera_data.lens = 50  # Standard lens
    camera_data.sensor_width = 36
    camera = bpy.data.objects.new("ThumbnailCamera", camera_data)
    
    # Add to scene
    scene.collection.objects.link(camera)
    scene.camera = camera
    
    # ✅ SMART CAMERA POSITIONING
    # Get object bounding box in world space
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # Calculate center
    bbox_center = sum(bbox_corners, mathutils.Vector()) / 8
    
    # Calculate bounding sphere radius
    max_distance = max((corner - bbox_center).length for corner in bbox_corners)
    
    # Camera distance (adjust to frame object nicely)
    camera_distance = max_distance * 2.5
    
    # Position at 45-degree angle (classic 3/4 view)
    angle = math.radians(45)
    elevation_angle = math.radians(30)  # Look slightly from above
    
    camera.location.x = bbox_center.x + camera_distance * math.cos(angle) * math.cos(elevation_angle)
    camera.location.y = bbox_center.y - camera_distance * math.sin(angle) * math.cos(elevation_angle)
    camera.location.z = bbox_center.z + camera_distance * math.sin(elevation_angle)
    
    # Point camera at object center
    direction = bbox_center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    
    return camera


def _setup_thumbnail_lighting(scene, obj):
    """
    Create professional 3-point lighting setup.
    Optimized for material and texture visibility.
    """
    # Get object bounds
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    center = sum(bbox_corners, mathutils.Vector()) / 8
    max_distance = max((corner - center).length for corner in bbox_corners)
    
    light_distance = max_distance * 3
    
    lights = []
    
    # ✅ KEY LIGHT (main light - slightly warm)
    key_light = _create_light(
        scene, "KeyLight",
        location=(center.x + light_distance * 0.7, 
                  center.y - light_distance * 0.7, 
                  center.z + light_distance * 0.8),
        energy=1500,
        color=(1.0, 0.98, 0.95)  # Slightly warm
    )
    lights.append(key_light)
    
    # ✅ FILL LIGHT (soften shadows - slightly cool)
    fill_light = _create_light(
        scene, "FillLight",
        location=(center.x - light_distance * 0.5, 
                  center.y + light_distance * 0.5, 
                  center.z + light_distance * 0.4),
        energy=500,
        color=(0.9, 0.95, 1.0)  # Slightly cool
    )
    lights.append(fill_light)
    
    # ✅ RIM LIGHT (edge highlight)
    rim_light = _create_light(
        scene, "RimLight",
        location=(center.x - light_distance * 0.8, 
                  center.y - light_distance * 0.8, 
                  center.z + light_distance),
        energy=800,
        color=(1.0, 0.95, 0.9)
    )
    lights.append(rim_light)
    
    # ✅ AMBIENT/ENVIRONMENT LIGHT (for better material visibility)
    ambient_light = _create_light(
        scene, "AmbientLight",
        location=(center.x, center.y, center.z + light_distance * 1.5),
        energy=300,
        color=(1.0, 1.0, 1.0)
    )
    lights.append(ambient_light)
    
    return lights


def _create_light(scene, name, location, energy, color):
    """Create a point light."""
    light_data = bpy.data.lights.new(name, 'POINT')
    light_data.energy = energy
    light_data.color = color
    
    # Soft light for better material rendering
    light_data.shadow_soft_size = 2.0
    
    light_obj = bpy.data.objects.new(name, light_data)
    light_obj.location = location
    
    scene.collection.objects.link(light_obj)
    
    return light_obj


# =====================================================
# BATCH THUMBNAIL GENERATION
# =====================================================

def render_thumbnails_batch(objects, output_dir, size=(256, 256), 
                            progress_callback=None):
    """
    Render thumbnails for multiple objects with progress tracking.
    """
    import uuid
    
    results = {
        'successful': [],
        'failed': [],
    }
    
    total = len(objects)
    
    for i, obj in enumerate(objects):
        # Generate unique filename
        filename = f"{obj.name}_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(output_dir, filename)
        
        # Render thumbnail
        success = render_thumbnail_for_object(obj, output_path, size=size)
        
        if success:
            results['successful'].append({
                'object': obj.name,
                'path': output_path
            })
        else:
            results['failed'].append(obj.name)
        
        # Progress callback
        if progress_callback:
            progress = (i + 1) / total
            progress_callback(progress)
    
    return results


# =====================================================
# VALIDATION
# =====================================================

def validate_thumbnail(filepath, min_size=(64, 64), max_size=(2048, 2048)):
    """Check if thumbnail file is valid."""
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    if not os.path.isfile(filepath):
        return False, "Path is not a file"
    
    # Check extension
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg']:
        return False, f"Invalid format: {ext}"
    
    # Check file size
    file_size = os.path.getsize(filepath)
    if file_size < 1024:
        return False, "File too small (possibly corrupted)"
    
    if file_size > 10 * 1024 * 1024:
        return False, "File too large"
    
    return True, ""


# =====================================================
# REGENERATE THUMBNAIL
# =====================================================

def regenerate_thumbnail(asset_id, obj=None):
    """
    Regenerate thumbnail for an existing asset.
    
    Args:
        asset_id (int): Asset database ID
        obj (bpy.types.Object): Object to render (if None, use active object)
    
    Returns:
        bool: True if successful
    """
    from .database import db_get_by_id, db_update_asset
    from .paths import get_thumbnails_dir
    
    # Get asset data
    asset = db_get_by_id(asset_id)
    if not asset:
        print(f"[AssetManager] Asset {asset_id} not found")
        return False
    
    # Get object
    if obj is None:
        obj = bpy.context.active_object
    
    if not obj or obj.type != 'MESH':
        print(f"[AssetManager] Invalid object for thumbnail regeneration")
        return False
    
    # Get thumbnail path
    thumbnail_path = asset.get('thumbnail_path')
    if not thumbnail_path:
        # Create new thumbnail path
        uuid = asset.get('uuid')
        thumbnail_path = os.path.join(get_thumbnails_dir(), f"{uuid}.png")
    
    # Delete old thumbnail if exists
    if os.path.exists(thumbnail_path):
        try:
            os.remove(thumbnail_path)
        except Exception as e:
            print(f"[AssetManager] Failed to delete old thumbnail: {e}")
    
    # Render new thumbnail
    success = render_thumbnail_for_object(obj, thumbnail_path, size=(256, 256))
    
    if success:
        # Update database
        db_update_asset(asset_id, thumbnail_path=thumbnail_path)
        print(f"[AssetManager] Thumbnail regenerated for asset {asset_id}")
    else:
        print(f"[AssetManager] Failed to regenerate thumbnail for asset {asset_id}")
    
    return success


def get_thumbnail_size_on_disk(thumbnail_path):
    """
    Get file size of thumbnail.
    
    Args:
        thumbnail_path (str): Path to thumbnail
    
    Returns:
        int: File size in bytes, or 0 if not found
    """
    if os.path.exists(thumbnail_path):
        return os.path.getsize(thumbnail_path)
    return 0