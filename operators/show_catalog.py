import bpy

class ASSETMANAGER_OT_show_catalog(bpy.types.Operator):
    """Show asset catalog in popup window"""
    bl_idname = "assetmanager.show_catalog"
    bl_label = "Asset Catalog"
    bl_description = "View assets in grid layout"
    
    # Pagination
    current_page: bpy.props.IntProperty(default=0)
    page_size: bpy.props.IntProperty(default=20)
    
    # Filter
    category_filter: bpy.props.EnumProperty(
        name="Category",
        items=[
            ('ALL', 'All Categories', ''),
            ('model', 'Models', ''),
            ('character', 'Characters', ''),
            ('environment', 'Environment', ''),
            ('props', 'Props', ''),
        ],
        default='ALL'
    )
    
    def invoke(self, context, event):
        """Load assets and show popup."""
        from ..core.database import db_get_paginated
        from ..core.preview import load_preview_for_single_asset
        
        # Get assets for current page
        self.assets, self.total = db_get_paginated(
            page=self.current_page,
            page_size=self.page_size,
            category=self.category_filter
        )
        
        # Load previews
        self.previews = {}
        for asset in self.assets:
            preview = load_preview_for_single_asset(asset)
            if preview:
                self.previews[f"asset_{asset['uuid']}"] = preview
        
        # Calculate window width
        cols = min(4, len(self.assets))
        width = 200 + (cols * 150)
        
        return context.window_manager.invoke_popup(self, width=min(width, 1000))
    
    def draw(self, context):
        """Draw catalog grid."""
        layout = self.layout
        
        # Header
        total_pages = (self.total + self.page_size - 1) // self.page_size
        
        row = layout.row()
        row.label(text=f"Asset Catalog - Page {self.current_page + 1}/{total_pages}", icon='ASSET_MANAGER')
        
        # Category filter
        row = layout.row()
        row.prop(self, "category_filter", text="")
        
        layout.separator()
        
        if not self.assets:
            layout.label(text="No assets found", icon='INFO')
            return
        
        # Grid of assets
        cols = min(4, len(self.assets))
        grid = layout.grid_flow(columns=cols, even_columns=True, align=True)
        
        for asset in self.assets:
            box = grid.box()
            
            # Preview
            key = f"asset_{asset['uuid']}"
            if key in self.previews:
                icon_id = self.previews[key].icon_id
                box.template_icon(icon_value=icon_id, scale=5.0)
            else:
                box.label(text="[No Preview]", icon='IMAGE_DATA')
            
            # Name
            box.label(text=asset['name'])
            
            # Info
            size_mb = asset['file_size'] / (1024 * 1024)
            info = f"{asset['category']} | {size_mb:.1f}MB"
            box.label(text=info)
            
            # Load button
            op = box.operator("assetmanager.load_from_db", text="Load", icon='IMPORT')
            op.asset_id = asset['id']
        
        # Pagination
        if total_pages > 1:
            layout.separator()
            row = layout.row(align=True)
            
            if self.current_page > 0:
                prev = row.operator("assetmanager.show_catalog", text="< Prev")
                prev.current_page = self.current_page - 1
                prev.category_filter = self.category_filter
            
            row.label(text=f"{self.current_page + 1}/{total_pages}")
            
            if self.current_page < total_pages - 1:
                next_op = row.operator("assetmanager.show_catalog", text="Next >")
                next_op.current_page = self.current_page + 1
                next_op.category_filter = self.category_filter
    
    def execute(self, context):
        """Re-invoke to refresh."""
        return self.invoke(context, None)