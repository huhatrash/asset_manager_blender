import bpy
from ..core.database import db_get_all
from ..core.preview import load_previews_for_assets

class ASSETMANAGER_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        row = layout.row(align=True)

        previews = load_previews_for_assets(db_get_all())
        if previews and item.preview_icon in previews:
            row.label(icon_value=previews[item.preview_icon].icon_id)
        else:
            row.label(icon='OBJECT_DATA')

        row.label(text=item.name)