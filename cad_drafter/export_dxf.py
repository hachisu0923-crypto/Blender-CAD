import math

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from .dxf_writer import build_dxf
from .properties import get_settings


class CAD_OT_export_dxf(bpy.types.Operator, ExportHelper):
    """可視メッシュの辺をDXF (R12) のLINEエンティティとして書き出す（真上から見た平面図）"""
    bl_idname = "cad.export_dxf"
    bl_label = "DXFで図面を出力"

    filename_ext = ".dxf"
    filter_glob: StringProperty(default="*.dxf", options={'HIDDEN'})
    selected_only: BoolProperty(name="選択オブジェクトのみ", default=False)
    unit_mode: EnumProperty(
        name="出力単位",
        items=[
            ('REAL', "実寸 (mm)",
             "1 DXF単位 = 実寸1mm。CADの流儀で、縮尺は開いた側の印刷時に適用する"),
            ('PAPER', "紙面寸法 (mm)",
             "縮尺を適用した印刷サイズで出力する（SVG出力と同じ）"),
        ],
        default='REAL',
    )
    draw_frame: BoolProperty(
        name="用紙枠を出力",
        description="用紙の範囲をFRAMEレイヤーに出力する",
        default=True,
    )
    draw_scale_note: BoolProperty(name="縮尺を記入", default=True)

    def execute(self, context):
        s = get_settings(context)
        denom = s.scale_denominator()
        pw, ph = s.paper_mm()
        # ワールド(m) → DXF単位(mm) の係数
        f = 1000.0 if self.unit_mode == 'REAL' else 1000.0 / denom
        # 紙面1mm相当のDXF単位（実寸モードでは縮尺分母、紙面モードでは1）
        unit = s.mm_world() * f
        text_height = s.text_height_mm * unit

        depsgraph = context.evaluated_depsgraph_get()
        lines = {"OUTLINE": [], "DIM": [], "FRAME": []}
        texts = []
        objects = context.selected_objects if self.selected_only else context.visible_objects
        for obj in objects:
            if obj.get("cad_sheet"):
                continue
            if obj.type == 'FONT' and obj.get("cad_dim_text"):
                loc = obj.matrix_world.translation
                texts.append({
                    "x": loc.x * f,
                    "y": loc.y * f,
                    "height": text_height,
                    "angle": math.degrees(obj.rotation_euler.z),
                    "body": obj.data.body,
                    "layer": "DIM",
                    "halign": 1,
                })
                continue
            if obj.type != 'MESH':
                continue
            layer = "DIM" if obj.get("cad_dim") else "OUTLINE"
            ev = obj.evaluated_get(depsgraph)
            mesh = ev.to_mesh()
            mw = ev.matrix_world
            for e in mesh.edges:
                v1 = mw @ mesh.vertices[e.vertices[0]].co
                v2 = mw @ mesh.vertices[e.vertices[1]].co
                lines[layer].append(((v1.x * f, v1.y * f), (v2.x * f, v2.y * f)))
            ev.to_mesh_clear()

        # 用紙枠（ワールド上の用紙範囲をそのまま係数変換）
        w = pw * unit
        h = ph * unit
        if self.draw_frame:
            corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
            for i in range(4):
                lines["FRAME"].append((corners[i], corners[(i + 1) % 4]))

        if self.draw_scale_note:
            # R12の文字コード問題を避けるためASCIIに留める
            texts.append({
                "x": w - 10.0 * unit,
                "y": 10.0 * unit,
                "height": 3.5 * unit,
                "angle": 0.0,
                "body": f"SCALE 1:{denom:g}  {s.paper}",
                "layer": "FRAME",
                "halign": 2,
            })

        content = build_dxf(lines, texts)
        with open(self.filepath, 'w', encoding='ascii', errors='replace') as fh:
            fh.write(content)

        n_lines = sum(len(v) for v in lines.values())
        self.report(
            {'INFO'},
            f"DXFを書き出しました: {self.filepath}"
            f"（LINE {n_lines} / TEXT {len(texts)} / "
            f"単位: {'実寸mm' if self.unit_mode == 'REAL' else '紙面mm'}）",
        )
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CAD_OT_export_dxf)


def unregister():
    bpy.utils.unregister_class(CAD_OT_export_dxf)
