bl_info = {
    "name": "CAD Drafter",
    "author": "Blender-CAD project",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "3Dビューポート > サイドバー(N) > CAD",
    "description": "縮尺に合わせた図面作成（用紙枠・図面カメラ・寸法線・DXF/SVG出力）",
    "category": "3D View",
}

if "bpy" in locals():
    import importlib
    importlib.reload(dxf_writer)
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(export_dxf)
    importlib.reload(export_svg)
    importlib.reload(ui)
else:
    from . import dxf_writer  # noqa: F401  (export_dxfから利用)
    from . import properties, operators, export_dxf, export_svg, ui

import bpy  # noqa: F401  (リロード判定用)

_modules = (properties, operators, export_dxf, export_svg, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
