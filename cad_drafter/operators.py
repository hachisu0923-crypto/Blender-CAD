import math

import bpy
from bpy.props import BoolProperty, FloatProperty
from mathutils import Vector

from .properties import get_settings

SHEET_COLLECTION = "CAD_Sheet"
DIM_COLLECTION = "CAD_Dimensions"


def ensure_collection(scene, name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if name not in scene.collection.children:
        try:
            scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


class CAD_OT_setup_sheet(bpy.types.Operator):
    """縮尺に合わせた用紙枠をワールド原点に作成し、単位・グリッド・スナップを設定する"""
    bl_idname = "cad.setup_sheet"
    bl_label = "用紙枠を作成"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = get_settings(context)
        scene = context.scene
        denom = s.scale_denominator()
        pw_mm, ph_mm = s.paper_mm()
        # 用紙が縮尺どおりにカバーする実空間の大きさ
        w = pw_mm * denom / 1000.0
        h = ph_mm * denom / 1000.0

        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1.0
        try:
            scene.unit_settings.length_unit = 'MILLIMETERS'
        except TypeError:
            pass

        coll = ensure_collection(scene, SHEET_COLLECTION)
        for obj in list(coll.objects):
            if obj.get("cad_sheet"):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)

        mesh = bpy.data.meshes.new("CAD_PaperFrame")
        verts = [(0, 0, 0), (w, 0, 0), (w, h, 0), (0, h, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        mesh.from_pydata(verts, edges, [])
        obj = bpy.data.objects.new("CAD_PaperFrame", mesh)
        obj["cad_sheet"] = True
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        coll.objects.link(obj)

        ts = scene.tool_settings
        ts.use_snap = True
        try:
            ts.snap_elements = {'VERTEX', 'EDGE', 'EDGE_MIDPOINT'}
        except Exception:
            pass

        # グリッド1マス = 紙面10mm相当
        spacing = 10.0 * s.mm_world()
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.grid_scale = spacing

        orientation = "横" if s.landscape else "縦"
        self.report(
            {'INFO'},
            f"{s.paper}{orientation} / 1:{denom:g} の用紙枠を作成しました"
            f"（実空間 {w:g}m × {h:g}m）",
        )
        return {'FINISHED'}


class CAD_OT_setup_camera(bpy.types.Operator):
    """用紙枠にぴったり一致する平行投影カメラと印刷解像度を設定する"""
    bl_idname = "cad.setup_camera"
    bl_label = "図面カメラを設定"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = get_settings(context)
        scene = context.scene
        denom = s.scale_denominator()
        pw_mm, ph_mm = s.paper_mm()
        w = pw_mm * denom / 1000.0
        h = ph_mm * denom / 1000.0

        cam_obj = bpy.data.objects.get("CAD_Camera")
        if cam_obj is None or cam_obj.type != 'CAMERA':
            cam_data = bpy.data.cameras.new("CAD_Camera")
            cam_obj = bpy.data.objects.new("CAD_Camera", cam_data)
        cam_data = cam_obj.data
        cam_data.type = 'ORTHO'
        cam_data.sensor_fit = 'HORIZONTAL'
        cam_data.ortho_scale = w
        cam_data.clip_start = 0.1
        cam_data.clip_end = max(w, h) * 10.0 + 100.0
        cam_obj.location = (w / 2.0, h / 2.0, max(w, h))
        cam_obj.rotation_euler = (0.0, 0.0, 0.0)

        coll = ensure_collection(scene, SHEET_COLLECTION)
        if cam_obj.name not in coll.objects:
            try:
                coll.objects.link(cam_obj)
            except RuntimeError:
                pass

        scene.camera = cam_obj
        scene.render.resolution_x = round(pw_mm / 25.4 * s.dpi)
        scene.render.resolution_y = round(ph_mm / 25.4 * s.dpi)
        scene.render.resolution_percentage = 100

        self.report(
            {'INFO'},
            f"カメラを設定しました（{scene.render.resolution_x}×{scene.render.resolution_y}px, {s.dpi}dpi）",
        )
        return {'FINISHED'}


class CAD_OT_add_line(bpy.types.Operator):
    """3Dカーソル位置から指定した長さ・角度の線分を実寸で作成する"""
    bl_idname = "cad.add_line"
    bl_label = "線分を作図"
    bl_options = {'REGISTER', 'UNDO'}

    length: FloatProperty(name="長さ", unit='LENGTH', default=1.0, min=1e-6)
    angle: FloatProperty(name="角度", subtype='ANGLE', default=0.0)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        start = context.scene.cursor.location.copy()
        direction = Vector((math.cos(self.angle), math.sin(self.angle), 0.0))
        end = start + direction * self.length
        mesh = bpy.data.meshes.new("CAD_Line")
        mesh.from_pydata([start, end], [(0, 1)], [])
        obj = bpy.data.objects.new("CAD_Line", mesh)
        context.collection.objects.link(obj)
        if context.mode == 'OBJECT':
            for o in context.selected_objects:
                o.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


class CAD_OT_add_rect(bpy.types.Operator):
    """3Dカーソルを左下角として指定サイズの矩形を実寸で作成する"""
    bl_idname = "cad.add_rect"
    bl_label = "矩形を作図"
    bl_options = {'REGISTER', 'UNDO'}

    width: FloatProperty(name="幅 (X)", unit='LENGTH', default=1.0, min=1e-6)
    height: FloatProperty(name="奥行 (Y)", unit='LENGTH', default=1.0, min=1e-6)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        c = context.scene.cursor.location.copy()
        w, h = self.width, self.height
        verts = [c, c + Vector((w, 0, 0)), c + Vector((w, h, 0)), c + Vector((0, h, 0))]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        mesh = bpy.data.meshes.new("CAD_Rect")
        mesh.from_pydata(verts, edges, [])
        obj = bpy.data.objects.new("CAD_Rect", mesh)
        context.collection.objects.link(obj)
        if context.mode == 'OBJECT':
            for o in context.selected_objects:
                o.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


def dim_geometry(p1, p2, offset_mm, s):
    """2点間の寸法線（引出線・寸法線・チック・文字）をJIS建築風に計算する。

    寸法はXY平面（平面図）に投影して測る。
    """
    mm = s.mm_world()
    z = (p1.z + p2.z) / 2.0
    a0 = Vector((p1.x, p1.y, z))
    b0 = Vector((p2.x, p2.y, z))
    d = b0 - a0
    length = d.length
    if length < 1e-9:
        return None
    direction = d / length
    normal = Vector((-direction.y, direction.x, 0.0))
    side = 1.0 if offset_mm >= 0 else -1.0

    off = offset_mm * mm
    a = a0 + normal * off
    b = b0 + normal * off
    gap = normal * (1.0 * mm * side)
    over = normal * (2.0 * mm * side)
    tick = (direction + normal).normalized() * (1.2 * mm)

    verts = []
    edges = []

    def add_edge(v1, v2):
        i = len(verts)
        verts.extend([v1, v2])
        edges.append((i, i + 1))

    add_edge(a0 + gap, a + over)   # 引出線
    add_edge(b0 + gap, b + over)
    add_edge(a, b)                 # 寸法線本体
    add_edge(a - tick, a + tick)   # 端部チック
    add_edge(b - tick, b + tick)

    # 文字は読み取り方向（左→右、下→上）に揃える
    tdir, tnorm = direction, normal
    if tdir.x < -1e-6 or (abs(tdir.x) <= 1e-6 and tdir.y < 0):
        tdir, tnorm = -direction, -normal
    text_pos = (a + b) / 2.0 + tnorm * (0.8 * mm)
    text_angle = math.atan2(tdir.y, tdir.x)
    value_mm = length * 1000.0
    text = f"{value_mm:.{s.dim_precision}f}"

    return {
        "verts": verts,
        "edges": edges,
        "text": text,
        "text_pos": text_pos,
        "text_angle": text_angle,
    }


def create_dimension(context, p1, p2, offset_mm):
    s = get_settings(context)
    geo = dim_geometry(p1, p2, offset_mm, s)
    if geo is None:
        return None
    coll = ensure_collection(context.scene, DIM_COLLECTION)

    mesh = bpy.data.meshes.new("CAD_Dim")
    mesh.from_pydata(geo["verts"], geo["edges"], [])
    obj = bpy.data.objects.new("CAD_Dim", mesh)
    obj["cad_dim"] = True
    obj["cad_p1"] = list(p1)
    obj["cad_p2"] = list(p2)
    obj["cad_offset_mm"] = offset_mm
    obj.show_in_front = True
    coll.objects.link(obj)

    curve = bpy.data.curves.new("CAD_DimText", type='FONT')
    curve.body = geo["text"]
    curve.size = s.text_height_mm * s.mm_world()
    curve.align_x = 'CENTER'
    curve.align_y = 'BOTTOM_BASELINE'
    tobj = bpy.data.objects.new("CAD_DimText", curve)
    tobj["cad_dim_text"] = True
    tobj.location = geo["text_pos"]
    tobj.rotation_euler = (0.0, 0.0, geo["text_angle"])
    tobj.parent = obj
    tobj.show_in_front = True
    coll.objects.link(tobj)
    return obj


class CAD_OT_add_dimension(bpy.types.Operator):
    """編集モードで選択した2頂点間の寸法線を作成する（XY平面に投影して測定）"""
    bl_idname = "cad.add_dimension"
    bl_label = "寸法線を追加"
    bl_options = {'REGISTER', 'UNDO'}

    offset_mm: FloatProperty(
        name="オフセット (mm)",
        description="測定点から寸法線までの紙面上の距離",
        default=8.0,
    )
    flip: BoolProperty(name="反対側に配置", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        self.offset_mm = get_settings(context).dim_offset_mm
        return self.execute(context)

    def execute(self, context):
        obj = context.edit_object
        obj.update_from_editmode()
        mw = obj.matrix_world
        verts = [mw @ v.co for v in obj.data.vertices if v.select]
        if len(verts) != 2:
            self.report({'ERROR'}, "頂点をちょうど2つ選択してください")
            return {'CANCELLED'}
        offset = -self.offset_mm if self.flip else self.offset_mm
        if create_dimension(context, verts[0], verts[1], offset) is None:
            self.report({'ERROR'}, "2点がXY平面上で同じ位置にあるため寸法を作成できません")
            return {'CANCELLED'}
        return {'FINISHED'}


class CAD_OT_refresh_dimensions(bpy.types.Operator):
    """縮尺・文字サイズなど設定の変更を既存のすべての寸法線に反映する"""
    bl_idname = "cad.refresh_dimensions"
    bl_label = "寸法線を再構築"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        coll = bpy.data.collections.get(DIM_COLLECTION)
        if coll is None:
            self.report({'INFO'}, "寸法線はまだありません")
            return {'CANCELLED'}
        dims = [
            (Vector(o["cad_p1"]), Vector(o["cad_p2"]), float(o["cad_offset_mm"]))
            for o in coll.objects
            if o.get("cad_dim")
        ]
        for o in list(coll.objects):
            if o.get("cad_dim") or o.get("cad_dim_text"):
                data = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if data and data.users == 0:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data, bpy.types.Curve):
                        bpy.data.curves.remove(data)
        for p1, p2, off in dims:
            create_dimension(context, p1, p2, off)
        self.report({'INFO'}, f"{len(dims)}本の寸法線を再構築しました")
        return {'FINISHED'}


classes = (
    CAD_OT_setup_sheet,
    CAD_OT_setup_camera,
    CAD_OT_add_line,
    CAD_OT_add_rect,
    CAD_OT_add_dimension,
    CAD_OT_refresh_dimensions,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
