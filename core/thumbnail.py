import os

def render_thumbnail_for_object(obj, thumb_path, size=(256,256)):
    """
    Render thumbnail tanpa bergantung posisi kamera/lampu.
    Gunakan bounding box + orthographic camera.
    """
    import bpy, math
    from mathutils import Vector

    scene = bpy.context.scene
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)

    # Backup kamera & lampu lama
    prev_cam = scene.camera
    for l in [o for o in scene.objects if o.type == 'LIGHT']:
        l.hide_render = True

    # Tambah temporary camera
    cam_data = bpy.data.cameras.new("ThumbCam")
    cam_obj = bpy.data.objects.new("ThumbCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(obj.dimensions) * 1.2  # scale bounding box

    # Posisi camera: di atas + 45 deg rotasi Z
    cam_obj.location = obj.location + Vector((0, -obj.dimensions.y*2, obj.dimensions.z*1.5))
    cam_obj.rotation_euler = (math.radians(60), 0, 0)

    # Override material supaya tidak gelap
    mat_backup = {}
    for slot in obj.material_slots:
        mat_backup[slot.name] = slot.material
        mat = bpy.data.materials.new(name="ThumbMat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.8,0.8,0.8,1)
        slot.material = mat

    # Render
    scene.render.engine = 'CYCLES'
    scene.render.film_transparent = True
    scene.render.resolution_x = size[0]
    scene.render.resolution_y = size[1]
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = thumb_path
    bpy.ops.render.render(write_still=True)

    # Restore material
    for slot in obj.material_slots:
        if slot.name in mat_backup:
            slot.material = mat_backup[slot.name]

    # Remove temp camera
    bpy.data.objects.remove(cam_obj, do_unlink=True)

    # Restore previous camera & lights
    scene.camera = prev_cam
    for l in [o for o in scene.objects if o.type == 'LIGHT']:
        l.hide_render = False

    return True