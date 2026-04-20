"""
Register Asset Operator - Asset Manager
Handles registration of new assets to the library.

Author: alfa haliza
Version: 2.0 (Bug Fixed)
"""

import bpy
import os
import uuid

from ..core.paths import (
    get_exports_dir, 
    get_thumbnails_dir, 
    get_safe_filename,
    get_free_space_mb,
    clean_asset_name
)
from ..core.export_import import export_selected_with_textures, validate_export_path
from ..core.thumbnail import render_thumbnail_for_object
from ..core.database import db_insert_or_update_by_uuid, db_get_by_uuid
from ..core.scene_assets import add_single_asset_to_scene


class ASSETMANAGER_OT_register(bpy.types.Operator):
    """Register selected object as asset"""
    bl_idname = "assetmanager.register"
    bl_label = "Register Selected Asset"
    bl_description = "Export selected object, generate thumbnail, and save to asset library"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties
    registration_mode: bpy.props.EnumProperty(
        name="Mode",
        description="Pilih untuk menimpa data lama (Update) atau membuat variasi baru (New)",
        items=[
            ('UPDATE', 'Update Existing Asset', 'Timpa data aset yang lama (Skenario 1)'),
            ('NEW', 'Register as New Asset', 'Buat sebagai aset baru / Aset 2 (Skenario 2)'),
        ],
        default='UPDATE'
    )
    
    
    has_existing_uuid: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    asset_name: bpy.props.StringProperty(
        name="Asset Name",
        description="Name for the asset",
        default=""
    )

    category: bpy.props.EnumProperty(
        name="Category",
        description="Asset category",
        items=[
            ('model', 'Model', 'Generic 3D model'),
            ('character', 'Character', 'Character or creature'),
            ('environment', 'Environment', 'Environment piece'),
            ('props', 'Props', 'Prop object'),
        ],
        default='model'
    )

    description: bpy.props.StringProperty(
        name="Description",
        description="Asset description",
        default=""
    )

    file_format: bpy.props.EnumProperty(
        name="Export Format",
        description="File format for export",
        items=[
            ('FBX', 'FBX (.fbx)', 'Export as FBX format'),
            ('BLEND', 'BLEND (.blend)', 'Export as Blender file'),
            ('OBJ', 'OBJ (.obj)', 'Export as Wavefront OBJ'),
            ('GLTF', 'GLB (.glb)', 'Export as glTF Binary (GLB)'),
        ],
        default='FBX'
    )
    
    generate_thumbnail: bpy.props.BoolProperty(
        name="Generate Thumbnail",
        description="Render thumbnail preview",
        default=True
    )
    
    thumbnail_size: bpy.props.EnumProperty(
        name="Thumbnail Size",
        items=[
            ('128', '128x128', 'Small thumbnail'),
            ('256', '256x256', 'Medium thumbnail (recommended)'),
            ('512', '512x512', 'Large thumbnail'),
        ],
        default='256'
    )

    # =====================================================
    # POLL
    # =====================================================

    @classmethod
    def poll(cls, context):
        """Check if operator can run. Must have an active, selected mesh object."""
        obj = context.active_object
        return (obj is not None and 
                obj.type == 'MESH' and 
                obj.select_get())

    # =====================================================
    # INVOKE
    # =====================================================

    def invoke(self, context, event):
        """Initialize properties before showing dialog."""
        obj = context.active_object
        
        if not obj:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}
        

        # Cek apakah objek ini sudah pernah didaftarkan sebelumnya
        from ..core.database import db_get_by_uuid
        uuid_detected = obj.get("asset_uuid")
        
        if uuid_detected:
            # Cek juga apakah UUID tersebut benar-benar ada di database
            existing_in_db = db_get_by_uuid(str(uuid_detected))
            if existing_in_db:
                self.has_existing_uuid = True
                self.registration_mode = 'UPDATE'
            else:
                self.has_existing_uuid = False
                self.registration_mode = 'NEW'
        else:
            self.has_existing_uuid = False
            self.registration_mode = 'NEW'
        
        # Set default name from object (with Smart Clean Up)
        self.asset_name = clean_asset_name(obj.name)
        self.description = f"Asset created from '{obj.name}'"
        
        return context.window_manager.invoke_props_dialog(self, width=400)

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, context):
        """Draw operator properties in dialog."""
        layout = self.layout
        
        # --- SMART NAME CHECK ---
        primitive_targets = {
            "Cube", "Plane", "Circle", "Sphere", "Uv Sphere", "Ico Sphere", 
            "Cylinder", "Cone", "Torus", "Monkey", "Grid"
        }
        
        # Check if current name is a primitive
        current_name = self.asset_name.strip()
        is_primitive = current_name in primitive_targets
        
        if is_primitive:
            row = layout.row()
            row.alert = True
            row.label(text=f"WARNING: Rename '{current_name}' to something unique!", icon='ERROR')
            layout.separator(factor=0.5)
        
        # Tampilkan pilihan mode jika objek sudah pernah terdaftar di DB
        if self.has_existing_uuid:
            box = layout.box()
            box.label(text="This record already exists!", icon='INFO')
            box.prop(self, "registration_mode", expand=True)
            layout.separator()
        
        # Asset Info
        box = layout.box()
        box.label(text="Asset Information", icon='INFO')
        box.prop(self, "asset_name")
        box.prop(self, "category")
        box.prop(self, "description")
        
        # Export Settings
        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(self, "file_format")
        
        # Thumbnail Settings
        box = layout.box()
        box.label(text="Thumbnail Settings", icon='IMAGE_DATA')
        box.prop(self, "generate_thumbnail")
        if self.generate_thumbnail:
            box.prop(self, "thumbnail_size")

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, context):
        """Main execution logic."""
        obj = context.active_object

        # Validation
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        if not self.asset_name.strip():
            self.report({'ERROR'}, "Asset name cannot be empty")
            return {'CANCELLED'}

        # --- MODE ENFORCEMENT ---
        # Switch to Object Mode to ensure mesh data can be read/exported correctly
        # This is safe because context is checked in poll()
        try:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch to Object Mode: {e}")
            return {'CANCELLED'}

        # --- DISK SPACE VALIDATION ---
        try:
            free_mb = get_free_space_mb()
            if free_mb < 50.0:
                self.report({'ERROR'}, f"LOW DISK SPACE ({free_mb:.1f} MB)! Please free up space (min 50MB) before registering.")
                return {'CANCELLED'}
        except Exception:
            pass # Continue if space check fails (fallback)

        try:
            # --- PENENTUAN UUID & MODE ---
            if self.has_existing_uuid and self.registration_mode == 'UPDATE':
                # Skenario 1: Pakai UUID lama → timpa data yang sudah ada
                asset_uuid = str(obj.get("asset_uuid", uuid.uuid4()))
                db_mode = 'UPDATE'
            elif self.has_existing_uuid and self.registration_mode == 'NEW':
                # Skenario 2: Objek sudah punya UUID di DB, tapi user minta buat aset BARU (Varian).
                asset_uuid = str(uuid.uuid4())
                db_mode = 'NEW'
            else:
                # Aset belum terdaftar di DB lokal (atau benar-benar baru)
                original_uuid = obj.get("asset_uuid")
                if original_uuid:
                    asset_uuid = str(original_uuid)
                    db_mode = 'NEW'
                else:
                    asset_uuid = str(uuid.uuid4())
                    obj["asset_uuid"] = asset_uuid
                    db_mode = 'NEW'

            
            # Step 1: Export asset file
            self.report({'INFO'}, "Exporting asset...")
            file_path = self._export_asset(obj, asset_uuid)
            
            if not file_path:
                raise RuntimeError("Export failed - could not create file. Check permissions.")
            
            # Step 2: Calculate geometry statistics
            stats = self._calculate_geometry_stats(obj)
            file_size = os.path.getsize(file_path)
            
            # Step 3: Generate thumbnail
            self.report({'INFO'}, "Rendering thumbnail...")
            thumbnail_path = self._generate_thumbnail(obj, asset_uuid)
            
            # Step 4: Save to database
            self.report({'INFO'}, "Saving to database...")
            inserted = db_insert_or_update_by_uuid(
                asset_uuid,
                self.asset_name.strip(),
                self.category,
                self.description.strip(),
                file_path,
                thumbnail_path,
                file_size,
                stats['poly_count'],
                stats['vertices'],
                stats['faces'],
                mode=db_mode
            )
            
            # Step 5: Update UI & Load Preview
            asset_data = db_get_by_uuid(asset_uuid)
            if asset_data:
                # Load preview immediately
                from ..core.preview import load_preview_for_single_asset
                load_preview_for_single_asset(
                    asset_data, 
                    force_reload=(db_mode == 'UPDATE')
                )
                
                # Add to scene property
                add_single_asset_to_scene(context, asset_data['id'])
                
                # Refresh UI
                for window in context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()
            
            action = "registered" if inserted else "updated"
            self.report({'INFO'}, f"Asset '{self.asset_name}' {action} successfully")
            
            return {'FINISHED'}

        except Exception as e:
            error_msg = str(e)
            if "No space left on device" in error_msg or "ENOSPC" in error_msg:
                self.report({'ERROR'}, "DISK FULL! Registration aborted.")
            else:
                self.report({'ERROR'}, f"Registration error: {error_msg}")
            
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _export_asset(self, obj, asset_uuid):
        """
        Export asset to file.
        
        Args:
            obj: Object to export
            asset_uuid: UUID for filename
        
        Returns:
            str: Path to exported file
        """
        exports_dir = get_exports_dir()
        
        file_path = export_selected_with_textures(
            obj,
            exports_dir,
            file_format=self.file_format,
            force_name=asset_uuid  # ✅ Use same UUID
        )
        
        return file_path

    def _generate_thumbnail(self, obj, asset_uuid):
        """
        Generate thumbnail for asset.
        
        Args:
            obj: Object to render
            asset_uuid: UUID for filename
        
        Returns:
            str: Path to thumbnail, or None if failed
        """
        thumbs_dir = get_thumbnails_dir()
        thumbnail_path = os.path.join(thumbs_dir, f"{asset_uuid}.png")
        
        # Get size
        size = int(self.thumbnail_size)
        
        # Render
        success = render_thumbnail_for_object(
            obj,
            thumbnail_path,
            size=(size, size),
            samples=32,
            use_transparent=True
        )
        
        if success and os.path.exists(thumbnail_path):
            return thumbnail_path
        else:
            print(f"[AssetManager] Thumbnail generation failed")
            return None

    def _calculate_geometry_stats(self, obj):
        """
        Calculate geometry statistics.
        
        Args:
            obj: Mesh object
        
        Returns:
            dict: Statistics
        """
        mesh = obj.data
        
        # Safe access for Blender 4.x/5.x
        polygons = getattr(mesh, "polygons", [])
        vertices = getattr(mesh, "vertices", [])
        
        return {
            'poly_count': len(polygons),
            'vertices': len(vertices),
            'faces': len(polygons)
        }