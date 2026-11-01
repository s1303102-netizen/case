import csv
import html
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_CSV = ROOT / "內部圓弧傘面板件尺寸.csv"
OUT_SVG = ROOT / "雷射切割四次排版預覽.svg"
DXF_NAMES = [
    "雷射切割_01_90x60cm.dxf",
    "雷射切割_02_90x60cm.dxf",
    "雷射切割_03_45x60cm.dxf",
    "雷射切割_04_90x60cm.dxf",
]

SCALE = 8.0
CANVAS_W = 2440
CANVAS_H = 1010
SHEET_TOP = 165
ORANGE = "#f28c00"


def load_shapes():
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    by_ring = {}
    for row in rows:
        by_ring.setdefault(int(row["ring"]), row)

    triangle = by_ring[0]
    inner = by_ring[1]
    outer = by_ring[2]

    triangle_edges = [float(value) for value in triangle["edge_lengths_cm"].split(";")]
    triangle_base = min(triangle_edges)
    triangle_height = 2 * float(triangle["area_cm2"]) / triangle_base

    def trapezoid(row):
        edges = [float(value) for value in row["edge_lengths_cm"].split(";")]
        short_base, long_base = edges[0], edges[2]
        height = 2 * float(row["area_cm2"]) / (short_base + long_base)
        return {
            "short": short_base,
            "long": long_base,
            "leg": edges[1],
            "height": height,
            "area": float(row["area_cm2"]),
        }

    return {
        "triangle": {
            "base": triangle_base,
            "side": max(triangle_edges),
            "height": triangle_height,
            "area": float(triangle["area_cm2"]),
        },
        "inner": trapezoid(inner),
        "outer": trapezoid(outer),
    }


def trapezoid_pair(shape):
    short_base = shape["short"]
    long_base = shape["long"]
    height = shape["height"]
    shift = (short_base + long_base) / 2

    upright = [
        (-short_base / 2, 0),
        (short_base / 2, 0),
        (long_base / 2, height),
        (-long_base / 2, height),
    ]
    inverted = [
        (-long_base / 2 + shift, 0),
        (long_base / 2 + shift, 0),
        (short_base / 2 + shift, height),
        (-short_base / 2 + shift, height),
    ]
    return normalize([upright, inverted])


def triangle_chain(shape, count):
    base = shape["base"]
    height = shape["height"]
    pieces = []
    for index in range(count):
        pair_index = index // 2
        if index % 2 == 0:
            pieces.append([
                (pair_index * base, 0),
                ((pair_index + 1) * base, 0),
                ((pair_index + 0.5) * base, height),
            ])
        else:
            pieces.append([
                ((pair_index + 0.5) * base, height),
                ((pair_index + 1.5) * base, height),
                ((pair_index + 1) * base, 0),
            ])
    return pieces


def normalize(groups):
    points = [point for group in groups for point in group]
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    return [[(x - min_x, y - min_y) for x, y in group] for group in groups]


def rotate(groups, degrees):
    angle = math.radians(degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    rotated = [
        [(x * cosine - y * sine, x * sine + y * cosine) for x, y in group]
        for group in groups
    ]
    return normalize(rotated)


def translate(groups, dx, dy):
    return [[(x + dx, y + dy) for x, y in group] for group in groups]


def bounds(groups):
    points = [point for group in groups for point in group]
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def center_of(poly):
    return (
        sum(point[0] for point in poly) / len(poly),
        sum(point[1] for point in poly) / len(poly),
    )


def add_group(target, groups, dx, dy, prefix, first_index):
    moved = translate(groups, dx, dy)
    for offset, polygon in enumerate(moved):
        target.append((polygon, f"{prefix}{first_index + offset:02d}"))


def build_layouts(shapes):
    outer_pair = trapezoid_pair(shapes["outer"])
    inner_pair_vertical = rotate(trapezoid_pair(shapes["inner"]), 90)
    outer_height = bounds(outer_pair)[3]
    outer_width = bounds(outer_pair)[2]
    inner_pair_width = bounds(inner_pair_vertical)[2]
    inner_pair_height = bounds(inner_pair_vertical)[3]

    cut_1 = []
    row_gap = 0.0
    y_margin = (90 - (4 * outer_height + 3 * row_gap)) / 2
    x_margin = (60 - outer_width) / 2
    for row in range(4):
        add_group(cut_1, outer_pair, x_margin, y_margin + row * (outer_height + row_gap), "O", row * 2 + 1)

    cut_2 = []
    col_gap = 0.0
    inner_width = 3 * inner_pair_width + 2 * col_gap
    inner_x = (60 - inner_width) / 2
    inner_y = 0.0
    for column in range(3):
        add_group(cut_2, inner_pair_vertical, inner_x + column * (inner_pair_width + col_gap), inner_y, "I", column * 2 + 1)
    outer_y = inner_pair_height
    for row in range(2):
        add_group(cut_2, outer_pair, x_margin, outer_y + row * (outer_height + row_gap), "O", 9 + row * 2)

    cut_3 = []
    inner_x = (60 - inner_width) / 2
    inner_y = (45 - inner_pair_height) / 2
    for column in range(3):
        add_group(cut_3, inner_pair_vertical, inner_x + column * (inner_pair_width + col_gap), inner_y, "I", 7 + column * 2)

    cut_4 = []
    lower_chain = triangle_chain(shapes["triangle"], 10)
    lower_bounds = bounds(lower_chain)
    lower_x = (90 - lower_bounds[2]) / 2
    add_group(cut_4, lower_chain, lower_x, 29.15, "T", 1)

    upper_pair = rotate(triangle_chain(shapes["triangle"], 2), 90)
    upper_bounds = bounds(upper_pair)
    upper_x = 90 - upper_bounds[2]
    add_group(cut_4, upper_pair, upper_x, 0.0, "T", 11)

    return [
        {"title": "切割 1", "size": (60, 90), "nominal": "90 × 60 cm", "pieces": cut_1},
        {"title": "切割 2", "size": (60, 90), "nominal": "90 × 60 cm", "pieces": cut_2},
        {"title": "切割 3", "size": (60, 45), "nominal": "45 × 60 cm", "pieces": cut_3},
        {"title": "切割 4", "size": (90, 60), "nominal": "90 × 60 cm", "pieces": cut_4},
    ]


def verify_layouts(layouts):
    expected = {"O": 12, "I": 12, "T": 12}
    actual = {key: 0 for key in expected}
    for layout in layouts:
        width, height = layout["size"]
        for polygon, label in layout["pieces"]:
            actual[label[0]] += 1
            for x, y in polygon:
                if not (-1e-6 <= x <= width + 1e-6 and -1e-6 <= y <= height + 1e-6):
                    raise ValueError(f"{layout['title']} 的 {label} 超出切割範圍：({x:.3f}, {y:.3f})")
    if actual != expected:
        raise ValueError(f"板件數量不符：{actual}")


def merged_cut_segments(pieces):
    grouped = {}
    for polygon, _ in pieces:
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            ux, uy = dx / length, dy / length
            if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0):
                ux, uy = -ux, -uy
            nx, ny = -uy, ux
            offset = start[0] * nx + start[1] * ny
            t0 = start[0] * ux + start[1] * uy
            t1 = end[0] * ux + end[1] * uy
            if t0 > t1:
                t0, t1 = t1, t0
            key = (round(ux, 7), round(uy, 7), round(offset, 6))
            grouped.setdefault(key, []).append((t0, t1))

    result = []
    for (ux, uy, offset), intervals in grouped.items():
        intervals.sort()
        merged = []
        for start, end in intervals:
            if merged and start <= merged[-1][1] + 1e-6:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        nx, ny = -uy, ux
        for start, end in merged:
            result.append((
                (ux * start + nx * offset, uy * start + ny * offset),
                (ux * end + nx * offset, uy * end + ny * offset),
            ))
    return result


def write_dxf(layout, filename):
    width_cm, height_cm = layout["size"]
    segments = merged_cut_segments(layout["pieces"])
    lines = [
        "0", "SECTION", "2", "HEADER",
        "9", "$ACADVER", "1", "AC1009",
        "9", "$INSUNITS", "70", "4",
        "9", "$MEASUREMENT", "70", "1",
        "9", "$EXTMIN", "10", "0.0", "20", "0.0", "30", "0.0",
        "9", "$EXTMAX", "10", f"{width_cm * 10:.6f}", "20", f"{height_cm * 10:.6f}", "30", "0.0",
        "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES",
        "0", "TABLE", "2", "LAYER", "70", "1",
        "0", "LAYER", "2", "CUT", "70", "0", "62", "1", "6", "CONTINUOUS",
        "0", "ENDTAB", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES",
    ]
    for (x1, y1), (x2, y2) in segments:
        # DXF uses a bottom-left origin; preview coordinates use top-left.
        lines.extend([
            "0", "LINE", "8", "CUT", "62", "1",
            "10", f"{x1 * 10:.6f}",
            "20", f"{(height_cm - y1) * 10:.6f}",
            "30", "0.0",
            "11", f"{x2 * 10:.6f}",
            "21", f"{(height_cm - y2) * 10:.6f}",
            "31", "0.0",
        ])
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    filename.write_text("\n".join(lines) + "\n", encoding="ascii")
    return segments


def svg_polygon(points, sheet_x, sheet_y):
    return " ".join(
        f"{sheet_x + x * SCALE:.2f},{sheet_y + y * SCALE:.2f}"
        for x, y in points
    )


def write_svg(layouts, shapes):
    sheet_xs = [35, 585, 1135, 1685]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
        '<rect width="100%" height="100%" fill="#f5f7fa"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif;fill:#172033;letter-spacing:0}.title{font-size:30px;font-weight:750}.subtitle{font-size:18px}.sheet-title{font-size:21px;font-weight:750}.piece{font-size:13px;font-weight:750;fill:#121826}.legend{font-size:17px}.small{font-size:14px;fill:#526070}</style>',
        '<text x="35" y="45" class="title">木板雷射切割四次排版預覽</text>',
        '<text x="35" y="78" class="subtitle">按實際板件尺寸等比例排列｜共 36 片：三角形 12、內圈梯形 12、外圈梯形 12｜單位：cm</text>',
        '<line x1="35" y1="103" x2="2405" y2="103" stroke="#c7cdd6" stroke-width="1"/>',
    ]

    for layout, sheet_x in zip(layouts, sheet_xs):
        sheet_width, sheet_height = layout["size"]
        sheet_y = SHEET_TOP + (90 - sheet_height) * SCALE / 2
        parts.append(f'<text x="{sheet_x}" y="137" class="sheet-title">{html.escape(layout["title"])} · {html.escape(layout["nominal"])}</text>')
        if sheet_width != 90 or sheet_height != 60:
            shown = f"預覽方向 {sheet_width} × {sheet_height}"
            parts.append(f'<text x="{sheet_x}" y="158" class="small">{shown}</text>')
        parts.append(
            f'<rect x="{sheet_x}" y="{sheet_y:.2f}" width="{sheet_width * SCALE:.2f}" height="{sheet_height * SCALE:.2f}" '
            'fill="#ffffff" stroke="#141b26" stroke-width="3"/>'
        )
        for polygon, label in layout["pieces"]:
            points = svg_polygon(polygon, sheet_x, sheet_y)
            parts.append(f'<polygon points="{points}" fill="{ORANGE}" stroke="#ffffff" stroke-width="2.2" stroke-linejoin="round"/>')
            cx, cy = center_of(polygon)
            parts.append(
                f'<text x="{sheet_x + cx * SCALE:.2f}" y="{sheet_y + cy * SCALE + 5:.2f}" '
                f'class="piece" text-anchor="middle">{label}</text>'
            )
        parts.append(
            f'<rect x="{sheet_x}" y="{sheet_y:.2f}" width="{sheet_width * SCALE:.2f}" height="{sheet_height * SCALE:.2f}" '
            'fill="none" stroke="#141b26" stroke-width="3"/>'
        )

    triangle = shapes["triangle"]
    inner = shapes["inner"]
    outer = shapes["outer"]
    legend_y = 930
    parts.extend([
        f'<line x1="35" y1="{legend_y - 33}" x2="2405" y2="{legend_y - 33}" stroke="#c7cdd6" stroke-width="1"/>',
        f'<text x="35" y="{legend_y}" class="legend"><tspan font-weight="750">T 三角形</tspan>：12 片｜三邊 {triangle["side"]:.2f}、{triangle["side"]:.2f}、{triangle["base"]:.2f}｜高 {triangle["height"]:.2f}</text>',
        f'<text x="790" y="{legend_y}" class="legend"><tspan font-weight="750">I 內圈梯形</tspan>：12 片｜平行邊 {inner["short"]:.2f}、{inner["long"]:.2f}｜腰 {inner["leg"]:.2f}｜高 {inner["height"]:.2f}</text>',
        f'<text x="35" y="{legend_y + 36}" class="legend"><tspan font-weight="750">O 外圈梯形</tspan>：12 片｜平行邊 {outer["short"]:.2f}、{outer["long"]:.2f}｜腰 {outer["leg"]:.2f}｜高 {outer["height"]:.2f}</text>',
        f'<text x="790" y="{legend_y + 36}" class="small">橘色為保留板件；白線為裁切線。此圖尚未加入雷射機安全邊距、切縫補償與定位標記。</text>',
        '</svg>',
    ])
    OUT_SVG.write_text("\n".join(parts), encoding="utf-8")


def main():
    shapes = load_shapes()
    layouts = build_layouts(shapes)
    verify_layouts(layouts)
    write_svg(layouts, shapes)
    print(OUT_SVG)
    for layout, dxf_name in zip(layouts, DXF_NAMES):
        segments = write_dxf(layout, ROOT / dxf_name)
        counts = {key: 0 for key in "OIT"}
        for _, label in layout["pieces"]:
            counts[label[0]] += 1
        print(layout["title"], layout["nominal"], counts, f"cut_segments={len(segments)}", dxf_name)


if __name__ == "__main__":
    main()
