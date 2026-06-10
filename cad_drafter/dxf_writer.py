"""DXF R12 (AC1009) ASCII書き出し。bpyに依存しないのでBlender外で単体検証できる。

DXFは「グループコード」と「値」を交互に並べたテキスト形式。
線1本は LINE エンティティ:

    0           ← エンティティ種別の開始
    LINE
    8           ← レイヤー名
    OUTLINE
    10 / 20 / 30  ← 始点 X / Y / Z
    11 / 21 / 31  ← 終点 X / Y / Z

文字は TEXT エンティティ（40=文字高さ, 1=文字列, 50=回転角度[度・CCW],
72=水平整列 0:左 1:中央 2:右, 73=垂直整列 0:ベースライン, 11/21=整列点）。
"""

# (レイヤー名, ACI色番号): 7=白/黒, 1=赤, 3=緑
LAYERS = (
    ("OUTLINE", 7),
    ("DIM", 1),
    ("FRAME", 3),
)


def build_dxf(lines_by_layer, texts):
    """DXF R12のファイル内容を文字列として組み立てる。

    lines_by_layer: {レイヤー名: [((x1, y1), (x2, y2)), ...]}
    texts: [{"x", "y", "height", "angle", "body", "layer", "halign"}, ...]
    座標・高さの単位は呼び出し側で揃えておく(mm)。角度は度(反時計回り)。
    """
    tags = []

    def tag(code, value):
        tags.append(str(code))
        tags.append(str(value))

    # --- HEADER ---
    tag(0, "SECTION")
    tag(2, "HEADER")
    tag(9, "$ACADVER")
    tag(1, "AC1009")
    tag(0, "ENDSEC")

    # --- TABLES ---
    tag(0, "SECTION")
    tag(2, "TABLES")

    tag(0, "TABLE")
    tag(2, "LTYPE")
    tag(70, 1)
    tag(0, "LTYPE")
    tag(2, "CONTINUOUS")
    tag(70, 64)
    tag(3, "Solid line")
    tag(72, 65)
    tag(73, 0)
    tag(40, "0.0")
    tag(0, "ENDTAB")

    tag(0, "TABLE")
    tag(2, "LAYER")
    tag(70, len(LAYERS))
    for name, color in LAYERS:
        tag(0, "LAYER")
        tag(2, name)
        tag(70, 0)
        tag(62, color)
        tag(6, "CONTINUOUS")
    tag(0, "ENDTAB")

    tag(0, "TABLE")
    tag(2, "STYLE")
    tag(70, 1)
    tag(0, "STYLE")
    tag(2, "STANDARD")
    tag(70, 0)
    tag(40, "0.0")
    tag(41, "1.0")
    tag(50, "0.0")
    tag(71, 0)
    tag(42, "2.5")
    tag(3, "txt")
    tag(4, "")
    tag(0, "ENDTAB")

    tag(0, "ENDSEC")

    # --- ENTITIES ---
    tag(0, "SECTION")
    tag(2, "ENTITIES")
    for layer, lines in lines_by_layer.items():
        for (x1, y1), (x2, y2) in lines:
            tag(0, "LINE")
            tag(8, layer)
            tag(10, f"{x1:.3f}")
            tag(20, f"{y1:.3f}")
            tag(30, "0.0")
            tag(11, f"{x2:.3f}")
            tag(21, f"{y2:.3f}")
            tag(31, "0.0")
    for tx in texts:
        tag(0, "TEXT")
        tag(8, tx["layer"])
        tag(10, f"{tx['x']:.3f}")
        tag(20, f"{tx['y']:.3f}")
        tag(30, "0.0")
        tag(40, f"{tx['height']:.3f}")
        tag(1, tx["body"])
        tag(50, f"{tx.get('angle', 0.0):.2f}")
        tag(72, tx.get("halign", 1))
        tag(11, f"{tx['x']:.3f}")
        tag(21, f"{tx['y']:.3f}")
        tag(31, "0.0")
        tag(73, 0)
    tag(0, "ENDSEC")
    tag(0, "EOF")
    return "\n".join(tags) + "\n"
