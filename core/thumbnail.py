import os

def render_thumbnail_for_object(obj, thumb_path, size=(256, 256)):
    import bpy
    import math
    from mathutils import Vector

    scene = bpy.context.scene
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)

    # ===============================
    # BACKUP STATE
    # ===============================
    prev_cam = scene.camera

    lights = [o for o in scene.objects if o.type == 'LIGHT']
    light_states = {l.name: l.hide_render for l in lights}

    mat_backup = []
    for i, slot in enumerate(obj.material_slots):
        mat_backup.append(slot.material)

    # ===============================
    # TEMP CAMERA
    # ===============================
    cam_data = bpy.data.cameras.new("AM_ThumbCam")
    cam_obj = bpy.data.objects.new("AM_ThumbCam", cam_data)
    scene.collection.objects.link(cam_obj)

    scene.camera = cam_obj
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(obj.dimensions) * 1.3

    cam_obj.location = obj.location + Vector((0, -obj.dimensions.y * 2, obj.dimensions.z * 1.5))
    cam_obj.rotation_euler = (math.radians(60), 0, 0)

    # ===============================
    # LIGHT SETUP (AMAN)
    # ===============================
    for l in lights:
        l.hide_render = True

    temp_light = bpy.data.lights.new("AM_ThumbLight", type='AREA')
    temp_light.energy = 1500
    light_obj = bpy.data.objects.new("AM_ThumbLight", temp_light)
    scene.collection.objects.link(light_obj)
    light_obj.location = cam_obj.location

    # ===============================
    # OVERRIDE MATERIAL (SINGLE)
    # ===============================
    thumb_mat = bpy.data.materials.new("AM_ThumbMat")
    thumb_mat.use_nodes = True
    bsdf = thumb_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)
        bsdf.inputs['Roughness'].default_value = 0.4

    for slot in obj.material_slots:
        slot.material = thumb_mat

    # ===============================
    # RENDER
    # ===============================
    scene.render.engine = 'CYCLES'
    scene.render.film_transparent = True
    scene.render.resolution_x = size[0]
    scene.render.resolution_y = size[1]
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = thumb_path

    bpy.ops.render.render(write_still=True)

    # ===============================
    # RESTORE STATE
    # ===============================
    for i, slot in enumerate(obj.material_slots):
        slot.material = mat_backup[i]

    for l in lights:
        l.hide_render = light_states.get(l.name, False)

    scene.camera = prev_cam

    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.objects.remove(light_obj, do_unlink=True)
    bpy.data.materials.remove(thumb_mat)

    return True
