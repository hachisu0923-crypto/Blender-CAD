import bpy

from .properties import get_settings


class CAD_PT_main(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CAD"
    bl_label = "CAD Drafter"

    def draw(self, context):
        s = get_settings(context)
        layout = self.layout

        box = layout.box()
        box.label(text="縮尺と用紙", icon='FILE_BLANK')
        box.prop(s, "scale")
        if s.scale == 'CUSTOM':
            box.prop(s, "custom_scale")
        row = box.row(align=True)
        row.prop(s, "paper", text="")
        row.prop(s, "landscape", toggle=True)
        box.operator("cad.setup_sheet", icon='MESH_PLANE')
        box.operator("cad.setup_camera", icon='CAMERA_DATA')

        box = layout.box()
        box.label(text="作図（実寸で入力）", icon='GREASEPENCIL')
        box.operator("cad.add_line", icon='IPO_LINEAR')
        box.operator("cad.add_rect", icon='MOD_LATTICE')

        box = layout.box()
        box.label(text="寸法", icon='DRIVER_DISTANCE')
        box.prop(s, "text_height_mm")
        box.prop(s, "dim_offset_mm")
        box.prop(s, "dim_precision")
        box.operator("cad.add_dimension", icon='ARROW_LEFTRIGHT')
        box.operator("cad.refresh_dimensions", icon='FILE_REFRESH')

        box = layout.box()
        box.label(text="出力", icon='OUTPUT')
        box.prop(s, "line_width_mm")
        box.prop(s, "dpi")
        box.operator("cad.export_svg", icon='EXPORT')


def register():
    bpy.utils.register_class(CAD_PT_main)


def unregister():
    bpy.utils.unregister_class(CAD_PT_main)
