import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

# 用紙サイズ (mm, 縦置き基準の 幅×高さ)
PAPER_SIZES = {
    'A4': (210.0, 297.0),
    'A3': (297.0, 420.0),
    'A2': (420.0, 594.0),
    'A1': (594.0, 841.0),
    'A0': (841.0, 1189.0),
}

SCALE_ITEMS = [
    ('1', "1:1", "原寸"),
    ('2', "1:2", ""),
    ('5', "1:5", ""),
    ('10', "1:10", ""),
    ('20', "1:20", ""),
    ('50', "1:50", ""),
    ('100', "1:100", ""),
    ('200', "1:200", ""),
    ('500', "1:500", ""),
    ('CUSTOM', "カスタム", "任意の縮尺分母を指定"),
]


class CADDrafterSettings(bpy.types.PropertyGroup):
    scale: EnumProperty(
        name="縮尺",
        description="図面の縮尺（モデルは常に実寸で作図し、出力時にこの縮尺が適用される）",
        items=SCALE_ITEMS,
        default='100',
    )
    custom_scale: FloatProperty(
        name="縮尺分母",
        description="カスタム縮尺 1:N の N",
        default=100.0,
        min=0.001,
    )
    paper: EnumProperty(
        name="用紙",
        items=[(k, k, "") for k in PAPER_SIZES],
        default='A3',
    )
    landscape: BoolProperty(
        name="横置き",
        default=True,
    )
    dpi: IntProperty(
        name="DPI",
        description="レンダリング解像度（印刷時の解像度）",
        default=300,
        min=72,
        max=1200,
    )
    text_height_mm: FloatProperty(
        name="文字高さ (mm)",
        description="印刷したときの寸法文字の高さ",
        default=3.0,
        min=0.5,
        max=20.0,
    )
    line_width_mm: FloatProperty(
        name="線幅 (mm)",
        description="SVG出力時の外形線の太さ",
        default=0.35,
        min=0.05,
        max=2.0,
    )
    dim_offset_mm: FloatProperty(
        name="寸法線オフセット (mm)",
        description="測定点から寸法線までの紙面上の距離",
        default=8.0,
    )
    dim_precision: IntProperty(
        name="寸法の小数桁",
        description="寸法値(mm)の小数点以下の桁数",
        default=0,
        min=0,
        max=3,
    )

    def scale_denominator(self):
        if self.scale == 'CUSTOM':
            return max(self.custom_scale, 0.001)
        return float(self.scale)

    def paper_mm(self):
        w, h = PAPER_SIZES[self.paper]
        return (h, w) if self.landscape else (w, h)

    def mm_world(self):
        """紙面上の1mmに相当するワールド距離(m)"""
        return self.scale_denominator() / 1000.0


def get_settings(context):
    return context.scene.cad_drafter


def register():
    bpy.utils.register_class(CADDrafterSettings)
    bpy.types.Scene.cad_drafter = bpy.props.PointerProperty(type=CADDrafterSettings)


def unregister():
    del bpy.types.Scene.cad_drafter
    bpy.utils.unregister_class(CADDrafterSettings)
