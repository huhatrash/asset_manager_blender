import bpy
from ..core.preview import get_preview_collection


class ASSETMANAGER_UL_list(bpy.types.UIList):

    def draw_item(
        self, context, layout, data, item,
        icon, active_data, active_propname
    ):

        row = layout.row(align=True)

        pcoll = get_preview_collection()

        if item.preview_icon in pcoll:
            row.label(
                icon_value=pcoll[item.preview_icon].icon_id
            )
        else:
            row.label(icon='OBJECT_DATA')

        row.label(text=item.name)
