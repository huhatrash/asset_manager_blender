import bpy
import os

def export_selected_to_fbx(obj, exports_dir):
    prev_sel = [o for o in bpy.context.selected_objects]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    safe_name = "".join(c if c.isalnum() or c in ".-" else "" for c in obj.name)
    out_path = os.path.join(exports_dir, f"{safe_name}.fbx")
    bpy.ops.export_scene.fbx(filepath=out_path, use_selection=True, apply_unit_scale=True, bake_space_transform=True)

    for o in prev_sel:
        o.select_set(True)
    return out_path

def export_selected_with_textures(obj, exports_dir, file_format='FBX', force_name=None):
    
    import bpy, os

    prev_sel = [o for o in bpy.context.selected_objects]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    filename = force_name if force_name else obj.name
    out_path = os.path.join(exports_dir, f"{filename}.{file_format.lower()}")

    if file_format.upper() == 'FBX':
        bpy.ops.export_scene.fbx(
            filepath=out_path,
            use_selection=True,
            apply_unit_scale=True,
            bake_space_transform=True,
            path_mode='COPY',
            embed_textures=True
        )
    elif file_format.upper() == 'GLB':
        bpy.ops.export_scene.gltf(
            filepath=out_path,
            use_selection=True,
            export_format='GLB',
            export_materials='EXPORT',
            export_images='COPY'
        )
    else:
        raise ValueError("Format tidak didukung")

    for o in prev_sel:
        o.select_set(True)

    return out_path
