import bpy
import os
from ..core.database import (
    db_trim_usage_history, 
    db_delete_orphaned_assets, 
    db_optimize,
    db_check_integrity
)
from ..core.scene_assets import load_assets_to_scene

class ASSETMANAGER_OT_trim_history(bpy.types.Operator):
    """Clear usage history to keep database small"""
    bl_idname = "assetmanager.trim_history"
    bl_label = "Trim Usage History"
    bl_description = "Keep only the most recent user history (removes old logs)"
    bl_options = {'REGISTER', 'UNDO'}

    limit: bpy.props.IntProperty(
        name="Keep Recent",
        description="Number of recent entries to preserve",
        default=50,
        min=0
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            db_trim_usage_history(limit=self.limit)
            self.report({'INFO'}, f"History trimmed to {self.limit} entries")
            
            # Refresh Recently Used panel if open
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Trim failed: {e}")
            return {'CANCELLED'}

class ASSETMANAGER_OT_cleanup_orphans(bpy.types.Operator):
    """Remove records for files that no longer exist on disk"""
    bl_idname = "assetmanager.cleanup_orphans"
    bl_label = "Cleanup Orphan Records"
    bl_description = "Remove database records whose files have been deleted manually from disk"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        report = db_check_integrity()
        orphans = report.get('orphaned_files', [])
        
        if not orphans:
            self.report({'INFO'}, "No orphaned records found.")
            return {'CANCELLED'}
            
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        from ..core.database import db_delete_orphaned_assets, db_get_all_assets
        from ..core.paths import get_thumbnails_dir, get_exports_dir
        
        # 1. Clean DB records whose files are missing
        deleted_records = db_delete_orphaned_assets()
        n_records = len(deleted_records)
        
        # 2. Deep Clean: Delete abandoned files that HAVE NO record in DB
        # This cleans up files from previous crashes or manual DB edits
        all_assets = db_get_all_assets()
        db_file_names = set()
        db_thumb_names = set()
        
        for a in all_assets:
            if a.get('file_path'): db_file_names.add(os.path.basename(a['file_path']))
            if a.get('thumbnail_path'): db_thumb_names.add(os.path.basename(a['thumbnail_path']))
        
        files_scrubbed = 0
        
        # Scrub Thumbnails
        thumbs_dir = get_thumbnails_dir()
        if os.path.exists(thumbs_dir):
            for f in os.listdir(thumbs_dir):
                if f.endswith('.png') and f not in db_thumb_names:
                    try:
                        os.remove(os.path.join(thumbs_dir, f))
                        files_scrubbed += 1
                    except: pass
        
        # Scrub Exports (only files matching UUID pattern to be safe)
        exports_dir = get_exports_dir()
        if os.path.exists(exports_dir):
            for f in os.listdir(exports_dir):
                # Only scrub if looks like one of our exports and not in DB
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.fbx', '.blend', '.obj', '.glb') and f not in db_file_names:
                    # Final safety: only scrub if it looks like a UUID (our internal format)
                    if len(f.split('.')[0]) >= 32: 
                        try:
                            os.remove(os.path.join(exports_dir, f))
                            files_scrubbed += 1
                        except: pass

        # Report
        msg = f"Cleanup Result: {n_records} orphan record(s) removed."
        if files_scrubbed > 0:
            msg += f" {files_scrubbed} abandoned file(s) scrubbed from disk."
        
        self.report({'INFO'}, msg)
        
        # Reload UI
        wm = context.window_manager
        from ..core.scene_assets import load_assets_to_scene
        load_assets_to_scene(context, page=0, force_reload=True)
            
        return {'FINISHED'}

class ASSETMANAGER_OT_optimize_db(bpy.types.Operator):
    """Rebuild database indexes and compress file"""
    bl_idname = "assetmanager.optimize_db"
    bl_label = "Optimize Database"
    bl_description = "Run VACUUM and ANALYZE to improve database performance"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            db_optimize()
            self.report({'INFO'}, "Database optimization complete")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Optimization failed: {e}")
            return {'CANCELLED'}

classes = (
    ASSETMANAGER_OT_trim_history,
    ASSETMANAGER_OT_cleanup_orphans,
    ASSETMANAGER_OT_optimize_db,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
