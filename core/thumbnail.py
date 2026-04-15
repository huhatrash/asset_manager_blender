import bpy
import os
import math
from mathutils import Vector


def render_thumbnail_for_object(obj, output_path, size=(300, 300), 
                                samples=64, use_transparent=True):
    """
    Args:
        obj: Object untuk di-render
        output_path: Path untuk save thumbnail
        size: Ukuran thumbnail (width, height)
        samples: Render samples
        use_transparent: Background transparan (default True)
    
    Returns:
        bool: True jika berhasil
    """
    if not obj or obj.type != 'MESH':
        print(f"[AssetManager] Invalid object: {obj}")
        return False
    
    # ✅ STORE ORIGINAL SETTINGS
    scene = bpy.context.scene
    original_settings = _store_scene_settings(scene)
    original_camera = scene.camera
    original_active = bpy.context.view_layer.objects.active
    original_selection = [o for o in bpy.context.selected_objects]
    
    # Store object visibility
    original_obj_visibility = {}
    for o in scene.objects:
        original_obj_visibility[o.name] = (o.hide_viewport, o.hide_render)
    
    temp_camera = None
    temp_lights = []  # Multiple lights untuk pencahayaan merata
    
    try:
        # ✅ TRANSPARENT BACKGROUND
        scene.render.film_transparent = True
        
        # ✅ ISOLASI CAHAYA TOTAL (Konsistensi Penuh)
        # 1. Matikan World Scene, ganti hitam buta agar HDRI/ambient scene tidak bocor!
        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        scene.world.use_nodes = True
        world_nodes = scene.world.node_tree.nodes
        world_nodes.clear()
        bg_node = world_nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0, 0, 0, 1) # Hitam Total
        bg_node.inputs['Strength'].default_value = 0.0
        output_node = world_nodes.new('ShaderNodeOutputWorld')
        scene.world.node_tree.links.new(bg_node.outputs[0], output_node.inputs[0])
        
        # 2. Kembalikan Exposure ke 0.0 agar tidak "terbakar"
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0

        # ✅ BAKE OBJECT GRAPH UNTUK MELINDUNGI GEOMETRY NODES/MODIFIERS ASLI
        bpy.ops.object.select_all(action='DESELECT')
        
        obj.hide_viewport = False
        obj.hide_render = False
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        # Duplikat & Realisasi (Bake)
        bpy.ops.object.duplicate(linked=False)
        temp_obj = bpy.context.active_object
        try:
            bpy.ops.object.convert(target='MESH')
        except:
            pass # Aman jika gagal convert
            
        # ✅ HIDE SEMUA OBJECT AND LAMPU SCENE (TERMASUK ORIGINAL) KECUALI TEMP_OBJ
        for o in scene.objects:
            if o != temp_obj and getattr(o, 'type', '') not in {'CAMERA'}:
                o.hide_render = True
        
        temp_obj.hide_viewport = False
        temp_obj.hide_render = False
        
        # ✅ MATIKAN CODE PERUSAK MATERIAL
        # JANGAN gunakan _ensure_materials_visible karena akan menimpa warna asli objek Anda!
        
        # ✅ CREATE TEMPORARY CAMERA
        cam_data = bpy.data.cameras.new("_TempThumbCam")
        cam_data.lens = 50
        cam_data.sensor_width = 36
        
        temp_camera = bpy.data.objects.new("_TempThumbCam", cam_data)
        scene.collection.objects.link(temp_camera)
        scene.camera = temp_camera
        
        # ✅ POSISI KAMERA (Fokus ke geometri yang sudah di-bake)
        bbox_corners = [temp_obj.matrix_world @ Vector(corner) for corner in temp_obj.bound_box]
        bbox_center = sum(bbox_corners, Vector()) / 8
        max_distance = max((corner - bbox_center).length for corner in bbox_corners)
        
        # Kalkulasi zoom yang wajar menutupi frame
        cam_distance = max(max_distance * 2.5, 0.1)
        
        temp_camera.location = bbox_center + Vector((
            cam_distance * 0.7,
            -cam_distance * 0.7, 
            cam_distance * 0.5
        ))
        
        direction = bbox_center - temp_camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        temp_camera.rotation_euler = rot_quat.to_euler()
        
        # ✅ CREATE MULTI-LIGHT SETUP
        temp_lights = _create_studio_lighting(scene, bbox_center, cam_distance)
        
        # ✅ RENDER SETTINGS
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        scene.render.filepath = output_path
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '8'
        scene.render.image_settings.compression = 15
        scene.render.resolution_x = size[0]
        scene.render.resolution_y = size[1]
        scene.render.resolution_percentage = 100
        
        # ✅ RENDER
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        
        success = os.path.exists(output_path)
        
        if success:
            print(f"[AssetManager] ✓ Thumbnail: {output_path}")
        
        return success
        
    except Exception as e:
        print(f"[AssetManager] ✗ Thumbnail error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # ✅ CLEANUP - DELETE TEMPORARY OBJECTS
        try:
            # Delete temp lights
            if 'temp_lights' in locals():
                for light_obj in temp_lights:
                    if light_obj:
                        light_data = light_obj.data
                        if light_obj.name in bpy.data.objects:
                            bpy.data.objects.remove(light_obj, do_unlink=True)
                        if light_data and light_data.name in bpy.data.lights:
                            bpy.data.lights.remove(light_data)
        
            # Delete temp baked object
            if 'temp_obj' in locals() and temp_obj:
                if temp_obj.name in bpy.data.objects:
                    temp_mesh = temp_obj.data
                    bpy.data.objects.remove(temp_obj, do_unlink=True)
                    if temp_mesh and temp_mesh.name in bpy.data.meshes:
                        bpy.data.meshes.remove(temp_mesh)
            
            # Delete temp camera
            if 'temp_camera' in locals() and temp_camera:
                cam_data = temp_camera.data
                if temp_camera.name in bpy.data.objects:
                    bpy.data.objects.remove(temp_camera, do_unlink=True)
                if cam_data and cam_data.name in bpy.data.cameras:
                    bpy.data.cameras.remove(cam_data)
            
            # Restore original camera
            scene.camera = original_camera
            
            # Restore object visibility
            for obj_name, (hide_vp, hide_rn) in original_obj_visibility.items():
                if obj_name in bpy.data.objects:
                    o = bpy.data.objects[obj_name]
                    o.hide_viewport = hide_vp
                    o.hide_render = hide_rn
            
            # Restore scene settings
            _restore_scene_settings(scene, original_settings)
            
            # Restore selection
            bpy.ops.object.select_all(action='DESELECT')
            for o in original_selection:
                if o and o.name in bpy.data.objects:
                    o.select_set(True)
            
            if original_active and original_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = original_active
                
        except Exception as e:
            print(f"[AssetManager] Cleanup error: {e}")


def _create_studio_lighting(scene, center, distance):
    """
    Create professional 3-point studio lighting setup untuk thumbnail.
    """
    # ==============================================================
    # 🌟 PENGATURAN TINGKAT KETERANGAN CAHAYA 🌟
    # DI SINI CARA MENGATURNYA! Ubah angka "Watt" ini jika masih keputihan/gelap.
    # Nilainya saya buat standar (SOFT) agar "tidak terlalu terang"
    # ==============================================================
    BASE_KEY_LIGHT   = 200   # Lampu Utama (Kanan Atas)
    BASE_FILL_LIGHT  = 1000    # Lampu Tambahan (Kiri) agar bayangan tidak gelap buta
    BASE_RIM_LIGHT   = 1000    # Lampu Belakang (Siluet)
    BASE_AMBIENT     = 100   # Cahaya Merata dari depan atas
    # ==============================================================
    
    lights = []
    
    # Skala pembesaran cahaya linear agar tidak meledak (not "terang sekali")
    # Jika objeknya besar, cahaya perlahan membesar.
    scale_factor = max(distance / 2.5, 1.5)
    
    # 1. KEY LIGHT
    key_data = bpy.data.lights.new(name="_TempKeyLight", type='AREA')
    key_data.energy = BASE_KEY_LIGHT * scale_factor
    key_data.size = max(4 * scale_factor, 1.0)
    key_data.color = (1.0, 0.98, 0.95)
    
    key_light = bpy.data.objects.new("_TempKeyLight", key_data)
    key_light.location = center + Vector((distance * 0.9, -distance * 0.6, distance * 0.8))
    rot_quat = (center - key_light.location).to_track_quat('-Z', 'Y')
    key_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(key_light)
    lights.append(key_light)
    
    # 2. FILL LIGHT
    fill_data = bpy.data.lights.new(name="_TempFillLight", type='AREA')
    fill_data.energy = BASE_FILL_LIGHT * scale_factor
    fill_data.size = max(5 * scale_factor, 1.0)
    fill_data.color = (0.95, 0.95, 1.0)
    
    fill_light = bpy.data.objects.new("_TempFillLight", fill_data)
    fill_light.location = center + Vector((-distance * 0.7, -distance * 0.5, distance * 0.6))
    rot_quat = (center - fill_light.location).to_track_quat('-Z', 'Y')
    fill_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(fill_light)
    lights.append(fill_light)
    
    # 3. RIM LIGHT
    rim_data = bpy.data.lights.new(name="_TempRimLight", type='AREA')
    rim_data.energy = BASE_RIM_LIGHT * scale_factor
    rim_data.size = max(3 * scale_factor, 1.0)
    rim_data.color = (1.0, 1.0, 1.0)
    
    rim_light = bpy.data.objects.new("_TempRimLight", rim_data)
    rim_light.location = center + Vector((-distance * 0.4, distance * 0.8, distance * 0.9))
    rot_quat = (center - rim_light.location).to_track_quat('-Z', 'Y')
    rim_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(rim_light)
    lights.append(rim_light)
    
    # 4. AMBIENT LIGHT
    ambient_data = bpy.data.lights.new(name="_TempAmbientLight", type='AREA')
    ambient_data.energy = BASE_AMBIENT * scale_factor
    ambient_data.size = max(6 * scale_factor, 1.0)
    ambient_data.color = (1.0, 1.0, 1.0)
    
    ambient_light = bpy.data.objects.new("_TempAmbientLight", ambient_data)
    ambient_light.location = center + Vector((0, 0, distance * 1.2))
    rot_quat = (center - ambient_light.location).to_track_quat('-Z', 'Y')
    ambient_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(ambient_light)
    lights.append(ambient_light)
    
    return lights


def _store_scene_settings(scene):
    """Store original scene settings"""
    settings = {
        'engine': scene.render.engine,
        'filepath': scene.render.filepath,
        'file_format': scene.render.image_settings.file_format,
        'color_mode': scene.render.image_settings.color_mode,
        'resolution_x': scene.render.resolution_x,
        'resolution_y': scene.render.resolution_y,
        'resolution_percentage': scene.render.resolution_percentage,
        'film_transparent': scene.render.film_transparent,
        'view_transform': scene.view_settings.view_transform,
        'exposure': scene.view_settings.exposure,
        'gamma': scene.view_settings.gamma,
    }
    
    if scene.world:
        settings['world_name'] = scene.world.name
    
    return settings


def _restore_scene_settings(scene, settings):
    """Restore original scene settings"""
    try:
        scene.render.engine = settings['engine']
        scene.render.filepath = settings['filepath']
        scene.render.image_settings.file_format = settings['file_format']
        scene.render.image_settings.color_mode = settings['color_mode']
        scene.render.resolution_x = settings['resolution_x']
        scene.render.resolution_y = settings['resolution_y']
        scene.render.resolution_percentage = settings['resolution_percentage']
        scene.render.film_transparent = settings['film_transparent']
        scene.view_settings.view_transform = settings['view_transform']
        scene.view_settings.exposure = settings['exposure']
        scene.view_settings.gamma = settings['gamma']
    except Exception as e:
        print(f"[AssetManager] Restore settings error: {e}")


def _has_gpu():
    """Check GPU availability"""
    try:
        prefs = bpy.context.preferences.addons.get('cycles')
        return prefs and len(prefs.preferences.devices) > 0
    except:
        return False


def _ensure_materials_visible(obj):
    """Ensure materials visible in Cycles"""
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="_TempMaterial")
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        bsdf = nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.5  # Not too shiny
        
        obj.data.materials.append(mat)
    else:
        for mat in obj.data.materials:
            if mat and not mat.use_nodes:
                mat.use_nodes = True


# =====================================================
# BATCH & UTILITIES
# =====================================================

def render_thumbnails_batch(objects, output_dir, size=(300, 300), 
                            progress_callback=None):
    """Render thumbnails untuk multiple objects"""
    import uuid
    
    results = {'successful': [], 'failed': []}
    total = len(objects)
    
    for i, obj in enumerate(objects):
        filename = f"{obj.name}_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(output_dir, filename)
        
        success = render_thumbnail_for_object(obj, output_path, size=size)
        
        if success:
            results['successful'].append({'object': obj.name, 'path': output_path})
        else:
            results['failed'].append(obj.name)
        
        if progress_callback:
            progress_callback((i + 1) / total)
    
    return results


def regenerate_thumbnail(asset_id, obj=None):
    """Regenerate thumbnail"""
    from .database import db_get_by_id, db_update_asset
    from .paths import get_thumbnails_dir
    
    asset = db_get_by_id(asset_id)
    if not asset:
        return False
    
    if obj is None:
        obj = bpy.context.active_object
    
    if not obj or obj.type != 'MESH':
        return False
    
    thumbnail_path = asset.get('thumbnail_path')
    if not thumbnail_path:
        uuid = asset.get('uuid')
        thumbnail_path = os.path.join(get_thumbnails_dir(), f"{uuid}.png")
    
    if os.path.exists(thumbnail_path):
        try:
            os.remove(thumbnail_path)
        except:
            pass
    
    success = render_thumbnail_for_object(obj, thumbnail_path, size=(300, 300))
    
    if success:
        db_update_asset(asset_id, thumbnail_path=thumbnail_path)
    
    return success


def validate_thumbnail(filepath):
    """Validate thumbnail file"""
    if not os.path.exists(filepath):
        return False, "File not found"
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg']:
        return False, f"Invalid format: {ext}"
    
    file_size = os.path.getsize(filepath)
    if file_size < 1024 or file_size > 10 * 1024 * 1024:
        return False, "Invalid file size"
    
    return True, ""


def get_thumbnail_size_on_disk(thumbnail_path):
    """Get file size"""
    return os.path.getsize(thumbnail_path) if os.path.exists(thumbnail_path) else 0