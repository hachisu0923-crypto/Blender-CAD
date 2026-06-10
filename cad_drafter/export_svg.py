import math
from xml.sax.saxutils import escape

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from .properties import get_settings


class CAD_OT_export_svg(bpy.types.Operator, ExportHelper):
    """可視メッシュの辺を縮尺どおりの寸法でSVGに書き出す（真上から見た平面図）"""
    bl_idname = "cad.export_svg"
    bl_label = "SVGで図面を出力"

    filename_ext = ".svg"
    filter_glob: StringProperty(default="*.svg", options={'HIDDEN'})
    selected_only: BoolProperty(name="選択オブジェクトのみ", default=False)
    draw_border: BoolProperty(name="図枠を描く", default=True)
    draw_scale_note: BoolProperty(name="縮尺を記入", default=True)

    def execute(self, context):
        s = get_settings(context)
        denom = s.scale_denominator()
        pw, ph = s.paper_mm()
        k = 1000.0 / denom  # ワールド(m) → 紙面(mm)

        def to_paper(v):
            # SVGはY軸が下向き
            return (v.x * k, ph - v.y * k)

        depsgraph = context.evaluated_depsgraph_get()
        main_lines = []
        dim_lines = []
        texts = []
        objects = context.selected_objects if self.selected_only else context.visible_objects
        for obj in objects:
            if obj.get("cad_sheet"):
                continue
            if obj.type == 'FONT' and obj.get("cad_dim_text"):
                texts.append(obj)
                continue
            if obj.type != 'MESH':
                continue
            target = dim_lines if obj.get("cad_dim") else main_lines
            ev = obj.evaluated_get(depsgraph)
            mesh = ev.to_mesh()
            mw = ev.matrix_world
            for e in mesh.edges:
                v1 = to_paper(mw @ mesh.vertices[e.vertices[0]].co)
                v2 = to_paper(mw @ mesh.vertices[e.vertices[1]].co)
                target.append((v1, v2))
            ev.to_mesh_clear()

        out = []
        out.append('<?xml version="1.0" encoding="UTF-8"?>')
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{pw:g}mm" height="{ph:g}mm" viewBox="0 0 {pw:g} {ph:g}">'
        )
        out.append(f'<rect x="0" y="0" width="{pw:g}" height="{ph:g}" fill="white"/>')

        margin = 10.0
        if self.draw_border:
            out.append(
                f'<rect x="{margin:g}" y="{margin:g}" '
                f'width="{pw - 2 * margin:g}" height="{ph - 2 * margin:g}" '
                f'fill="none" stroke="black" stroke-width="{s.line_width_mm:g}"/>'
            )

        def emit_lines(group, width):
            if not group:
                return
            out.append(
                f'<g stroke="black" stroke-width="{width:g}" '
                f'stroke-linecap="round" fill="none">'
            )
            for (x1, y1), (x2, y2) in group:
                out.append(
                    f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"/>'
                )
            out.append('</g>')

        emit_lines(main_lines, s.line_width_mm)
        emit_lines(dim_lines, s.line_width_mm * 0.5)

        for tobj in texts:
            loc = tobj.matrix_world.translation
            x, y = to_paper(loc)
            angle = -math.degrees(tobj.rotation_euler.z)
            body = escape(tobj.data.body)
            out.append(
                f'<text x="{x:.3f}" y="{y:.3f}" font-size="{s.text_height_mm:g}" '
                f'font-family="sans-serif" text-anchor="middle" '
                f'transform="rotate({angle:.2f} {x:.3f} {y:.3f})">{body}</text>'
            )

        if self.draw_scale_note:
            orientation = "横" if s.landscape else "縦"
            note = f"SCALE 1:{denom:g}  {s.paper}{orientation}"
            out.append(
                f'<text x="{pw - margin - 2:g}" y="{ph - margin - 2:g}" '
                f'font-size="3.5" font-family="sans-serif" '
                f'text-anchor="end">{escape(note)}</text>'
            )

        out.append('</svg>')

        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(out))

        self.report(
            {'INFO'},
            f"SVGを書き出しました: {self.filepath}"
            f"（線 {len(main_lines)} / 寸法線 {len(dim_lines)} / 文字 {len(texts)}）",
        )
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CAD_OT_export_svg)


def unregister():
    bpy.utils.unregister_class(CAD_OT_export_svg)
