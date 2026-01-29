import bpy
from ..core.scene_assets import (
    load_assets_to_scene,
    next_page,
    previous_page,
    first_page,
    last_page,
    go_to_page,
    on_filter_changed,
    refresh_current_page,
)


# =====================================================
# PAGINATION NAVIGATION OPERATORS
# =====================================================

class ASSETMANAGER_OT_next_page(bpy.types.Operator):
    """Go to next page of assets"""
    bl_idname = "assetmanager.next_page"
    bl_label = "Next Page"
    bl_description = "Load next page of assets"
    
    def execute(self, context):
        if next_page(context):
            self.report({'INFO'}, "Loaded next page")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Already at last page")
            return {'CANCELLED'}


class ASSETMANAGER_OT_previous_page(bpy.types.Operator):
    """Go to previous page of assets"""
    bl_idname = "assetmanager.previous_page"
    bl_label = "Previous Page"
    bl_description = "Load previous page of assets"
    
    def execute(self, context):
        if previous_page(context):
            self.report({'INFO'}, "Loaded previous page")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Already at first page")
            return {'CANCELLED'}


class ASSETMANAGER_OT_first_page(bpy.types.Operator):
    """Go to first page of assets"""
    bl_idname = "assetmanager.first_page"
    bl_label = "First Page"
    bl_description = "Go to first page of assets"
    
    def execute(self, context):
        if first_page(context):
            self.report({'INFO'}, "Loaded first page")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Already at first page")
            return {'CANCELLED'}


class ASSETMANAGER_OT_last_page(bpy.types.Operator):
    """Go to last page of assets"""
    bl_idname = "assetmanager.last_page"
    bl_label = "Last Page"
    bl_description = "Go to last page of assets"
    
    def execute(self, context):
        if last_page(context):
            self.report({'INFO'}, "Loaded last page")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Already at last page")
            return {'CANCELLED'}


class ASSETMANAGER_OT_go_to_page(bpy.types.Operator):
    """Go to specific page number"""
    bl_idname = "assetmanager.go_to_page"
    bl_label = "Go To Page"
    bl_description = "Jump to specific page"
    
    page_number: bpy.props.IntProperty(
        name="Page Number",
        description="Page to jump to (1-indexed for display)",
        default=1,
        min=1
    )
    
    def invoke(self, context, event):
        scene = context.scene
        total_pages = getattr(scene, "asset_total_pages", 1)
        self.page_number = min(self.page_number, total_pages)
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        total_pages = getattr(scene, "asset_total_pages", 1)
        
        layout.label(text=f"Total Pages: {total_pages}")
        layout.prop(self, "page_number")
    
    def execute(self, context):
        # Convert 1-indexed to 0-indexed
        page = self.page_number - 1
        
        if go_to_page(context, page):
            self.report({'INFO'}, f"Loaded page {self.page_number}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Invalid page number")
            return {'CANCELLED'}


# =====================================================
# FILTER & SEARCH OPERATORS
# =====================================================

class ASSETMANAGER_OT_apply_filters(bpy.types.Operator):
    """Apply search and filter settings"""
    bl_idname = "assetmanager.apply_filters"
    bl_label = "Apply Filters"
    bl_description = "Apply current search and filter settings"
    
    def execute(self, context):
        on_filter_changed(context)
        
        scene = context.scene
        total = getattr(scene, "asset_total_count", 0)
        
        self.report({'INFO'}, f"Found {total} matching assets")
        return {'FINISHED'}


class ASSETMANAGER_OT_clear_filters(bpy.types.Operator):
    """Clear all filters and show all assets"""
    bl_idname = "assetmanager.clear_filters"
    bl_label = "Clear Filters"
    bl_description = "Reset all filters and show all assets"
    
    def execute(self, context):
        scene = context.scene
        
        # Reset all filter properties
        scene.asset_search = ""
        scene.asset_category = 'ALL'
        scene.filter_min_size = 0
        scene.filter_max_size = 0
        scene.filter_min_poly = 0
        scene.filter_max_poly = 0
        
        # Reload from first page
        on_filter_changed(context)
        
        total = getattr(scene, "asset_total_count", 0)
        self.report({'INFO'}, f"Showing all {total} assets")
        
        return {'FINISHED'}


class ASSETMANAGER_OT_refresh_assets(bpy.types.Operator):
    """Refresh current page from database"""
    bl_idname = "assetmanager.refresh_assets"
    bl_label = "Refresh"
    bl_description = "Reload assets from database"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        refresh_current_page(context)
        self.report({'INFO'}, "Assets refreshed")
        return {'FINISHED'}


# =====================================================
# PAGE SIZE CHANGE OPERATOR
# =====================================================

class ASSETMANAGER_OT_change_page_size(bpy.types.Operator):
    """Change number of assets per page"""
    bl_idname = "assetmanager.change_page_size"
    bl_label = "Change Page Size"
    bl_description = "Change how many assets to show per page"
    
    page_size: bpy.props.EnumProperty(
        name="Assets Per Page",
        items=[
            ('10', '10', 'Show 10 assets per page (Default)'),
            ('25', '25', 'Show 25 assets per page'),
            ('50', '50', 'Show 50 assets per page'),
            ('100', '100', 'Show 100 assets per page'),
            ('200', '200', 'Show 200 assets per page'),
        ],
        default='10'
    )
    
    def invoke(self, context, event):
        scene = context.scene
        current_size = getattr(scene, "asset_page_size", 10)
        self.page_size = str(current_size)
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "page_size", expand=True)
        layout.label(text="Larger sizes may slow down UI", icon='INFO')
    
    def execute(self, context):
        scene = context.scene
        new_size = int(self.page_size)
        
        # Update page size
        scene.asset_page_size = new_size
        
        # Reload from first page with new size
        load_assets_to_scene(context, page=0, page_size=new_size, force_reload=True)
        
        self.report({'INFO'}, f"Page size changed to {new_size}")
        return {'FINISHED'}


# =====================================================
# SORT OPERATORS
# =====================================================

class ASSETMANAGER_OT_change_sort(bpy.types.Operator):
    """Change asset sorting"""
    bl_idname = "assetmanager.change_sort"
    bl_label = "Sort Assets"
    bl_description = "Change how assets are sorted"
    
    sort_by: bpy.props.EnumProperty(
        name="Sort By",
        items=[
            ('created_at', 'Date Created', 'Sort by creation date'),
            ('updated_at', 'Date Modified', 'Sort by last update'),
            ('name', 'Name', 'Sort alphabetically by name'),
            ('category', 'Category', 'Sort by category'),
            ('file_size', 'File Size', 'Sort by file size'),
            ('poly_count', 'Polygon Count', 'Sort by polygon count'),
        ],
        default='created_at'
    )
    
    sort_order: bpy.props.EnumProperty(
        name="Order",
        items=[
            ('DESC', 'Descending', 'Newest/Largest first'),
            ('ASC', 'Ascending', 'Oldest/Smallest first'),
        ],
        default='DESC'
    )
    
    def invoke(self, context, event):
        scene = context.scene
        self.sort_by = getattr(scene, "asset_sort_by", 'created_at')
        self.sort_order = getattr(scene, "asset_sort_order", 'DESC')
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "sort_by")
        layout.prop(self, "sort_order", expand=True)
    
    def execute(self, context):
        scene = context.scene
        
        # Update scene properties
        scene.asset_sort_by = self.sort_by
        scene.asset_sort_order = self.sort_order
        
        # Reload current page with new sorting
        current_page = getattr(scene, "asset_current_page", 0)
        page_size = getattr(scene, "asset_page_size", 10)
        
        load_assets_to_scene(context, page=current_page, page_size=page_size, force_reload=True)
        
        order_text = "descending" if self.sort_order == 'DESC' else "ascending"
        self.report({'INFO'}, f"Sorted by {self.sort_by} ({order_text})")
        
        return {'FINISHED'}


# =====================================================
# STATISTICS OPERATOR
# =====================================================

class ASSETMANAGER_OT_show_statistics(bpy.types.Operator):
    """Show database statistics"""
    bl_idname = "assetmanager.show_statistics"
    bl_label = "Asset Statistics"
    bl_description = "View statistics about asset library"
    
    def invoke(self, context, event):
        from ..core.database import db_get_statistics
        self.stats = db_get_statistics()
        return context.window_manager.invoke_popup(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        stats = getattr(self, 'stats', {})
        
        # Total assets
        box = layout.box()
        box.label(text="Library Overview", icon='ASSET_MANAGER')
        row = box.row()
        row.label(text=f"Total Assets: {stats.get('total_assets', 0):,}")
        
        # By category
        box = layout.box()
        box.label(text="By Category", icon='BOOKMARKS')
        by_cat = stats.get('by_category', {})
        for cat, count in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            row = box.row()
            row.label(text=f"{cat}:")
            row.label(text=f"{count:,}")
        
        # File sizes
        box = layout.box()
        box.label(text="Storage", icon='FILE_FOLDER')
        size_stats = stats.get('size', {})
        total_mb = size_stats.get('total_bytes', 0) / (1024 * 1024)
        avg_mb = size_stats.get('avg_bytes', 0) / (1024 * 1024)
        box.label(text=f"Total: {total_mb:.2f} MB")
        box.label(text=f"Average: {avg_mb:.2f} MB")
        
        # Polygon stats
        box = layout.box()
        box.label(text="Geometry", icon='MESH_CUBE')
        poly_stats = stats.get('polygons', {})
        total_polys = poly_stats.get('total', 0)
        avg_polys = poly_stats.get('average', 0)
        box.label(text=f"Total Polygons: {total_polys:,}")
        box.label(text=f"Average: {avg_polys:,.0f}")
    
    def execute(self, context):
        return {'FINISHED'}


# =====================================================
# BATCH OPERATIONS
# =====================================================

class ASSETMANAGER_OT_select_all(bpy.types.Operator):
    """Select all assets on current page"""
    bl_idname = "assetmanager.select_all"
    bl_label = "Select All"
    bl_description = "Select all visible assets"
    
    def execute(self, context):
        # This would require adding a 'selected' property to AssetItem
        # For now, just report
        scene = context.scene
        count = len(scene.asset_items)
        self.report({'INFO'}, f"Would select {count} assets (feature coming soon)")
        return {'FINISHED'}


class ASSETMANAGER_OT_deselect_all(bpy.types.Operator):
    """Deselect all assets"""
    bl_idname = "assetmanager.deselect_all"
    bl_label = "Deselect All"
    bl_description = "Deselect all assets"
    
    def execute(self, context):
        self.report({'INFO'}, "Deselected all (feature coming soon)")
        return {'FINISHED'}


# =====================================================
# CLASSES TO REGISTER
# =====================================================

classes = (
    ASSETMANAGER_OT_next_page,
    ASSETMANAGER_OT_previous_page,
    ASSETMANAGER_OT_first_page,
    ASSETMANAGER_OT_last_page,
    ASSETMANAGER_OT_go_to_page,
    ASSETMANAGER_OT_apply_filters,
    ASSETMANAGER_OT_clear_filters,
    ASSETMANAGER_OT_refresh_assets,
    ASSETMANAGER_OT_change_page_size,
    ASSETMANAGER_OT_change_sort,
    ASSETMANAGER_OT_show_statistics,
    ASSETMANAGER_OT_select_all,
    ASSETMANAGER_OT_deselect_all,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)