import bpy
from ..core.database import db_get_all
from ..core.preview import load_previews_for_assets

class ASSETMANAGER_OT_show_catalog(bpy.types.Operator):
    bl_idname = "assetmanager.show_catalog"
    bl_label = "3D Asset Catalog"
    bl_description = "View All 3D Assets"
    selected_asset: bpy.props.IntProperty(name="Selected Asset ID", default=-1)
    
    def invoke(self, context, event):
        self.assets = db_get_all() 
        self.previews = load_previews_for_assets(self.assets)
        
        asset_count = len(self.assets)

        if asset_count <= 1:
                width = 260
        elif asset_count <= 2:
               width = 420 
        elif asset_count <= 4:
                width = 650 
        elif asset_count <= 8:
                width = 800 
        else:
                width = 1000
                
        return context.window_manager.invoke_popup(self, width=width) # kalo mau pake cancel ok pake props_dialog

    def draw(self, context):
        layout = self.layout
        
        assets = getattr(self, "assets", [])
        previews = getattr(self, "previews", {})
        layout.label(text=f"Total Assets: {len(self.assets)}", icon='ASSET_MANAGER')

        if not self.assets:
            layout.label(text="Tidak ada asset di database.")
            return

                   
        grid = layout.grid_flow(columns=4, even_columns=True, even_rows=True, align=True)
    
        for a in self.assets:
            box = grid.box()
            key = f"asset_{a['id']}"
            icon_id = 0
            try:
                if key in self.previews:
                    icon_id = self.previews[key].icon_id
            except Exception:
                pass

            row = box.row()
            if icon_id:
                row.template_icon(icon_value=icon_id, scale=8.0)
            else:
                row.label(text="[no preview]")

            box.label(text=a['name'])


#            row = box.row()
#            op_load = row.operator("assetmanager.load_from_db", text="Load", icon='IMPORT')
#            op_load.asset_id = a['id']
#        

    def execute(self, context):
        return {'FINISHED'}