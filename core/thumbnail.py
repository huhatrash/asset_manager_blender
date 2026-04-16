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
    original_world = scene.world  # Simpan referensi world asli
    
    # Store object visibility
    original_obj_visibility = {}
    for o in scene.objects:
        original_obj_visibility[o.name] = (o.hide_viewport, o.hide_render)
    
    temp_camera = None
    temp_lights = []  # Multiple lights untuk pencahayaan merata
    temp_world = None  # World sementara untuk render thumbnail
    
    try:
        # ✅ TRANSPARENT BACKGROUND
        scene.render.film_transparent = True
        
        # ✅ WORLD — Buat world sementara yang terpisah agar world asli tidak berubah
        temp_world = bpy.data.worlds.new("_TempThumbWorld")
        temp_world.use_nodes = True
        world_nodes = temp_world.node_tree.nodes
        world_nodes.clear()
        bg_node = world_nodes.new('ShaderNodeBackground')
        bg_node.inputs['Color'].default_value = (0, 0, 0, 1)
        bg_node.inputs['Strength'].default_value = 0.0
        output_node = world_nodes.new('ShaderNodeOutputWorld')
        temp_world.node_tree.links.new(bg_node.outputs[0], output_node.inputs[0])
        scene.world = temp_world  # Pakai world sementara
        
        # ✅ RENDER ENGINE: Cycles + Denoiser untuk hasil realistis
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        try:
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        except Exception:
            pass
        scene.cycles.max_bounces = 8
        scene.cycles.diffuse_bounces = 4
        scene.cycles.glossy_bounces = 4
        scene.cycles.transmission_bounces = 8
        scene.cycles.transparent_max_bounces = 8
        
        # ✅ TONE MAPPING: Filmic/AgX agar warna tidak terpotong & saturasi terjaga
        try:
            scene.view_settings.view_transform = 'AgX'
        except Exception:
            try:
                scene.view_settings.view_transform = 'Filmic'
            except Exception:
                scene.view_settings.view_transform = 'Standard'
        try:
            scene.view_settings.look = 'None'
        except Exception:
            pass
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
            
            # Restore world asli (sebelum hapus temp_world)
            scene.world = original_world
            
            # Hapus world sementara
            if temp_world and temp_world.name in bpy.data.worlds:
                bpy.data.worlds.remove(temp_world)
            
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
    3-point studio lighting dengan rasio yang benar.

    Rasio industri marketplace profesional:
      Key   : 1.0   — main illumination, warm white, kanan-atas-depan
      Fill  : 0.20  — softens shadow tanpa menghilangkannya, kiri
      Rim   : 0.40  — edge separation, belakang atas
      Ambient: 0.05 — bounce fill sangat lembut dari bawah

    Energi dihitung dari luas penampang objek (distance²) bukan linear,
    agar tidak meledak pada objek besar.
    """
    lights = []

    # Energi dasar dihitung kuadratik (distance sudah merupakan radius objek)
    # Nilai 40 dipilih agar objek ukuran wajar (~1m) = sekitar 40W per unit
    energy_base = max(distance * distance * 40.0, 10.0)

    # ── 1. KEY LIGHT ─────────────────────────────────────────────────────────
    # Warm white, 45° horizontal-kanan & 45° atas, softbox menengah
    key_data = bpy.data.lights.new(name="_TempKeyLight", type='AREA')
    key_data.energy = energy_base * 1.0
    key_data.size   = max(distance * 1.5, 0.3)
    key_data.color  = (1.0, 0.97, 0.93)  # warm white

    key_light = bpy.data.objects.new("_TempKeyLight", key_data)
    key_light.location = center + Vector((
         distance * 1.2,    # kanan
        -distance * 0.8,    # depan
         distance * 1.0,    # atas
    ))
    rot_quat = (center - key_light.location).to_track_quat('-Z', 'Y')
    key_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(key_light)
    lights.append(key_light)

    # ── 2. FILL LIGHT ────────────────────────────────────────────────────────
    # Cool-neutral, JAUH lebih redup dari key (rasio 1:5)
    # Softbox besar agar wrap mengelilingi objek dengan lembut
    fill_data = bpy.data.lights.new(name="_TempFillLight", type='AREA')
    fill_data.energy = energy_base * 0.20
    fill_data.size   = max(distance * 2.5, 0.5)
    fill_data.color  = (0.93, 0.95, 1.0)  # slight cool tint

    fill_light = bpy.data.objects.new("_TempFillLight", fill_data)
    fill_light.location = center + Vector((
        -distance * 1.0,    # kiri
        -distance * 0.3,    # sedikit depan
         distance * 0.3,    # setinggi objek
    ))
    rot_quat = (center - fill_light.location).to_track_quat('-Z', 'Y')
    fill_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(fill_light)
    lights.append(fill_light)

    # ── 3. RIM / BACK LIGHT ──────────────────────────────────────────────────
    # Silhouette separation, dari belakang-atas
    # Kuat cukup untuk edge tapi tidak menerangi permukaan depan
    rim_data = bpy.data.lights.new(name="_TempRimLight", type='AREA')
    rim_data.energy = energy_base * 0.40
    rim_data.size   = max(distance * 1.0, 0.3)
    rim_data.color  = (0.97, 0.98, 1.0)  # neutral cool

    rim_light = bpy.data.objects.new("_TempRimLight", rim_data)
    rim_light.location = center + Vector((
        -distance * 0.2,    # hampir tengah-kiri
         distance * 1.3,    # belakang
         distance * 1.2,    # cukup tinggi
    ))
    rot_quat = (center - rim_light.location).to_track_quat('-Z', 'Y')
    rim_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(rim_light)
    lights.append(rim_light)

    # ── 4. GROUND BOUNCE ─────────────────────────────────────────────────────
    # Area light besar dari bawah mensimulasikan bounce cahaya dari lantai
    # Sangat redup — hanya mengisi shadow terbawah sedikit
    bounce_data = bpy.data.lights.new(name="_TempBounceLight", type='AREA')
    bounce_data.energy = energy_base * 0.05
    bounce_data.size   = max(distance * 4.0, 1.0)
    bounce_data.color  = (1.0, 1.0, 1.0)

    bounce_light = bpy.data.objects.new("_TempBounceLight", bounce_data)
    bounce_light.location = center + Vector((0, 0, -distance * 0.8))
    rot_quat = (center - bounce_light.location).to_track_quat('-Z', 'Y')
    bounce_light.rotation_euler = rot_quat.to_euler()
    scene.collection.objects.link(bounce_light)
    lights.append(bounce_light)

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