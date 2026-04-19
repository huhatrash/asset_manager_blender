import bpy
import os
import mathutils
from bpy_extras import view3d_utils

def get_view3d_region(context, event):
    """Finds the 3D Viewport area and region under the mouse pointer."""
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            if area.x <= event.mouse_x <= area.x + area.width and \
               area.y <= event.mouse_y <= area.y + area.height:
                for region in area.regions:
                     if region.type == 'WINDOW':
                         return area, region
    return None, None

def get_ground_intersection(ray_origin, view_vector):
    """Fallback intersection with the ground plane (Z=0)."""
    p = ray_origin
    v = view_vector
    if v.z != 0:
        t = -p.z / v.z
        if t > 0:
            return p + v * t
    return None

class ASSETMANAGER_OT_load_from_db(bpy.types.Operator):
    """Load asset from library into scene interactively (drag & drop)"""
    bl_idname = "assetmanager.load_from_db"
    bl_label = "Load Asset"
    bl_description = "Import asset file into current scene. Drag to place."
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: bpy.props.IntProperty()
    
    @classmethod
    def poll(cls, context):
        """Check if in a valid mode."""
        return context.mode == 'OBJECT'
        
    def invoke(self, context, event):
        """Invoke starts the import and the modal loop for interactive drag."""
        from ..core.database import db_get_by_id
        from ..core.export_import import import_file_auto
        
        self._initial_mouse_pos = (event.mouse_x, event.mouse_y)
        self._imported_objects = []
        self._root_objects = []
        
        asset = db_get_by_id(self.asset_id)
        if not asset:
            self.report({'WARNING'}, "Asset not found")
            return {'CANCELLED'}
            
        file_path = asset.get('file_path')
        if not file_path or not os.path.exists(file_path):
            self.report({'ERROR'}, f"Asset file missing: {file_path}")
            return {'CANCELLED'}
            
        try:
            # Import file
            self._imported_objects = import_file_auto(file_path)
            
            if not self._imported_objects:
                self.report({'WARNING'}, "No objects imported")
                return {'CANCELLED'}
                
            # Select imported objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in self._imported_objects:
                obj.select_set(True)
                
            if self._imported_objects:
                context.view_layer.objects.active = self._imported_objects[0]
                
            # Identify root objects (objects without a parent in the imported set)
            # This prevents moving a child and its parent and getting double translation.
            self._root_objects = [o for o in self._imported_objects if o.parent not in self._imported_objects]
            
            # Tag objects with the asset UUID so they are recognized as "already registered"
            asset_uuid = asset.get('uuid')
            if asset_uuid:
                for obj in self._imported_objects:
                    obj["asset_uuid"] = asset_uuid
            
            # Immediately try to place at cursor if we are already in View3D (e.g. N-panel)
            self._update_placement(context, event)

            # Start modal handler
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    def modal(self, context, event):
        # Allow cancellation
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            # Delete objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in self._imported_objects:
                try:
                    obj.select_set(True)
                except ReferenceError:
                    pass
            bpy.ops.object.delete()
            
            # Important: we must cause a redraw when we cancel to clean up view
            for area in context.screen.areas:
                area.tag_redraw()
                
            self.report({'INFO'}, "Asset placement cancelled")
            return {'CANCELLED'}
            
        # Finish placement on mouse release OR Enter
        if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or event.type == 'RET':
            # Force final update
            self._update_placement(context, event)

            # Ensure imported objects are selected and one is active
            if self._imported_objects:
                for obj in self._imported_objects:
                    try:
                        obj.select_set(True)
                    except ReferenceError:
                        pass
                if self._imported_objects[0].name in bpy.data.objects:
                    context.view_layer.objects.active = self._imported_objects[0]

            # Record usage
            try:
                from ..core.database import db_log_usage
                db_log_usage(self.asset_id, bpy.data.filepath or "")
            except:
                pass

            self.report({'INFO'}, f"Placed {len(self._imported_objects)} object(s).")
            return {'FINISHED'}
            
        # Interactively move
        if event.type == 'MOUSEMOVE':
            self._update_placement(context, event)
            
        return {'RUNNING_MODAL'}
        
    def _update_placement(self, context, event):
        """Raycast into the 3D viewport under the mouse and move the imported objects."""
        # We need the VIEW_3D context which might be different from where the Operator was invoked (UI Panel)
        area, region = get_view3d_region(context, event)
        if not area or not region or area.type != 'VIEW_3D':
            return
            
        space = area.spaces.active
        if not space or space.type != 'VIEW_3D':
            return
            
        rv3d = space.region_3d
        if not rv3d:
            return
            
        coord = (event.mouse_x - region.x, event.mouse_y - region.y)
        
        try:
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        except Exception as e:
            # Fallback for invalid projection
            return
            
        depsgraph = context.evaluated_depsgraph_get()
        scene = context.scene
        
        # Hide imported objects from raycast so they don't block the ray
        for obj in self._imported_objects:
            try:
                obj.hide_viewport = True
            except ReferenceError:
                pass
                
        # Perform raycast
        result, location, normal, index, hit_obj, matrix = scene.ray_cast(
            depsgraph, ray_origin, view_vector
        )
        
        # Restore viewport visibility
        for obj in self._imported_objects:
            try:
                obj.hide_viewport = False
            except ReferenceError:
                pass
                
        # Determine target location: use raycast hit, or fallback to ground plane (Z=0)
        target_loc = location if result else get_ground_intersection(ray_origin, view_vector)
        
        if target_loc:
            # Update root objects (children will follow)
            for root_obj in self._root_objects:
                try:
                    root_obj.location = target_loc
                except ReferenceError:
                    pass

class ASSETMANAGER_OT_load_from_db_deferred(bpy.types.Operator):
    """Load asset, closing any popups first, then entering placement mode"""
    bl_idname = "assetmanager.load_from_db_deferred"
    bl_label = "Load Asset"
    bl_description = "Close the catalog and enter placement mode for the asset"
    bl_options = {'REGISTER', 'UNDO'}

    asset_id: bpy.props.IntProperty()

    def execute(self, context):
        a_id = self.asset_id
        
        def start_placement():
            # Invoke the real modal operator after the initial popup context is destroyed
            bpy.ops.assetmanager.load_from_db('INVOKE_DEFAULT', asset_id=a_id)
            return None
            
        # Give the popup a tiny moment to truly close
        bpy.app.timers.register(start_placement, first_interval=0.01)
        return {'FINISHED'}