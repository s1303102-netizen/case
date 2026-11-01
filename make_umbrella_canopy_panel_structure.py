import csv
import importlib.util
import math
import pathlib
import struct
import zlib

import numpy as np


ROOT = pathlib.Path("/Users/alissachang/大專")
OUT_OBJ = ROOT / "內部圓弧傘面木板結構.obj"
OUT_MTL = ROOT / "內部圓弧傘面木板結構.mtl"
OUT_CSV = ROOT / "內部圓弧傘面板件尺寸.csv"
OUT_SVG = ROOT / "內部圓弧傘面正視分片圖.svg"
OUT_PNG = ROOT / "內部圓弧傘面正視分片圖.png"

SECTORS = 12
RING_RATIOS = [0.0, 0.50, 0.75, 1.0]
WOOD_THICKNESS_CM = 0.9
SURFACE_OFFSET_CM = 0.035

spec = importlib.util.spec_from_file_location("pom", ROOT / "parse_original_mesh.py")
pom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pom)


def load_original_mesh():
    raw = pom.decompress_blend(pom.BLEND)
    blocks = pom.parse_blocks(raw)
    structs = pom.parse_dna(next(b for b in blocks if b["code"] == "DNA1")["data"])
    by = pom.block_by_old(blocks)
    mesh_i = pom.get_struct_index(structs, "Mesh")
    obj_i = pom.get_struct_index(structs, "Object")
    mesh_block = [b for b in blocks if b["sdna"] == mesh_i and b["code"].startswith("ME")][0]
    mesh = mesh_block["data"]
    obj_block = next(
        b for b in blocks
        if b["sdna"] == obj_i and b["code"].startswith("OB") and pom.read_ptr(b["data"], 560) == mesh_block["oldptr"]
    )
    loc = pom.read_f32x3(obj_block["data"], 744)
    scale = pom.read_f32x3(obj_block["data"], 768)
    totvert = pom.read_i32(mesh, 432)
    totpoly = pom.read_i32(mesh, 440)
    totloop = pom.read_i32(mesh, 444)
    attrs_block = by[pom.read_ptr(mesh, 456)]
    attrs = {}
    for i in range(pom.read_i32(mesh, 464)):
        d = attrs_block["data"][i * 24:i * 24 + 24]
        name = pom.read_cstring(by[pom.read_ptr(d, 0)]["data"])
        holder = by[pom.read_ptr(d, 16)]["data"]
        attrs[name] = by[pom.read_ptr(holder, 0)]["data"]

    verts = []
    for i in range(totvert):
        x, y, z = struct.unpack_from("<fff", attrs["position"], i * 12)
        verts.append(np.array([loc[0] + x * scale[0], loc[1] + y * scale[1], loc[2] + z * scale[2]], dtype=float))

    corners = [struct.unpack_from("<i", attrs[".corner_vert"], i * 4)[0] for i in range(totloop)]
    offsets_raw = by[pom.read_ptr(mesh, 448)]["data"]
    offsets = [struct.unpack_from("<i", offsets_raw, i * 4)[0] for i in range(totpoly + 1)]
    faces = [corners[offsets[i]:offsets[i + 1]] for i in range(totpoly)]
    return verts, faces


def normal(points):
    if len(points) < 3:
        return np.array([0.0, 1.0, 0.0])
    n = np.cross(points[1] - points[0], points[2] - points[0])
    length = np.linalg.norm(n)
    if length < 1e-8:
        return np.array([0.0, 1.0, 0.0])
    return n / length


def is_trough_face(points, n):
    arr = np.array(points)
    xspan = arr[:, 0].max() - arr[:, 0].min()
    cy = arr[:, 1].mean()
    cz = arr[:, 2].mean()
    return n[1] > 0.20 and xspan <= 8.5 and -18 < cy < 18 and 8 < cz < 122


def fit_sphere(points):
    p = np.array(points)
    a = np.column_stack([p[:, 0], p[:, 1], p[:, 2], np.ones(len(p))])
    b = -(p[:, 0] ** 2 + p[:, 1] ** 2 + p[:, 2] ** 2)
    coef, *_ = np.linalg.lstsq(a, b, rcond=None)
    center = -coef[:3] / 2
    radius = math.sqrt(float(np.dot(center, center) - coef[3]))
    radial = np.linalg.norm(p - center, axis=1)
    rms = float(np.sqrt(np.mean((radial - radius) ** 2)))
    return center, radius, rms


def angle_delta(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


def boundary_radii(projected_points, center_x, center_z):
    values = []
    sector_step = 2 * math.pi / SECTORS
    spoke_offset = math.pi / 2 - sector_step / 2
    for i in range(SECTORS):
        theta = spoke_offset + i * sector_step
        candidates = []
        for x, z in projected_points:
            dx = x - center_x
            dz = z - center_z
            rho = math.hypot(dx, dz)
            if rho < 1:
                continue
            if abs(angle_delta(math.atan2(dz, dx), theta)) <= sector_step * 0.72:
                candidates.append(rho)
        if candidates:
            values.append(max(candidates))
        else:
            values.append(max(math.hypot(x - center_x, z - center_z) for x, z in projected_points))
    # Use the lower half's widest radius for every vertex of the regular dodecagon.
    smoothed = []
    for i, value in enumerate(values):
        smoothed.append((values[i - 1] + value * 2 + values[(i + 1) % SECTORS]) / 4)
    lower_radii = [
        value for i, value in enumerate(smoothed)
        if math.sin(spoke_offset + i * sector_step) < 0
    ]
    return [max(lower_radii)] * SECTORS, spoke_offset


def surface_point(center, radius, x, z):
    dx = x - center[0]
    dz = z - center[2]
    inside = max(0.0, radius * radius - dx * dx - dz * dz)
    y = center[1] - math.sqrt(inside)
    return np.array([x, y, z], dtype=float)


def unit(v):
    length = float(np.linalg.norm(v))
    if length < 1e-8:
        return np.array([0.0, 1.0, 0.0])
    return v / length


def create_panel_vertices(points, sphere_center):
    centroid = sum(points) / len(points)
    face_normal = unit(sphere_center - centroid)
    front = [p + face_normal * SURFACE_OFFSET_CM for p in points]
    back = [p + face_normal * (SURFACE_OFFSET_CM - WOOD_THICKNESS_CM) for p in points]
    return front + back


def edge_lengths(points):
    return [float(np.linalg.norm(points[(i + 1) % len(points)] - points[i])) for i in range(len(points))]


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    origin = points[0]
    area = 0.0
    for i in range(1, len(points) - 1):
        area += float(np.linalg.norm(np.cross(points[i] - origin, points[i + 1] - origin))) / 2
    return area


def flat_cut_coordinates(points):
    lengths = edge_lengths(points)
    if len(points) == 3:
        a = lengths[0]
        b = lengths[1]
        c = lengths[2]
        x2 = (a * a + c * c - b * b) / (2 * a) if a else 0
        y2 = math.sqrt(max(0.0, c * c - x2 * x2))
        return [(0.0, 0.0), (a, 0.0), (x2, y2)]

    p0, p1, p2, p3 = points
    a = float(np.linalg.norm(p1 - p0))
    b = float(np.linalg.norm(p2 - p1))
    c = float(np.linalg.norm(p3 - p2))
    d = float(np.linalg.norm(p0 - p3))
    diag = float(np.linalg.norm(p2 - p0))
    x2 = (a * a + diag * diag - b * b) / (2 * a) if a else 0
    y2 = math.sqrt(max(0.0, diag * diag - x2 * x2))
    # Place p3 by intersecting circles around p0 and p2.
    if diag < 1e-8:
        x3, y3 = 0.0, d
    else:
        ex = np.array([x2, y2]) / diag
        ey = np.array([-ex[1], ex[0]])
        along = (d * d + diag * diag - c * c) / (2 * diag)
        height = math.sqrt(max(0.0, d * d - along * along))
        candidate = ex * along + ey * height
        if candidate[1] < 0:
            candidate = ex * along - ey * height
        x3, y3 = float(candidate[0]), float(candidate[1])
    return [(0.0, 0.0), (a, 0.0), (x2, y2), (x3, y3)]


def build_panels(center, radius, boundary, spoke_offset):
    rings = []
    for ratio in RING_RATIOS:
        ring = []
        if ratio == 0:
            ring.append(surface_point(center, radius, center[0], center[2]))
        else:
            for i, b in enumerate(boundary):
                theta = spoke_offset + i * 2 * math.pi / SECTORS
                x = center[0] + math.cos(theta) * b * ratio
                z = center[2] + math.sin(theta) * b * ratio
                ring.append(surface_point(center, radius, x, z))
        rings.append(ring)

    panels = []
    for sector in range(SECTORS):
        panels.append({
            "piece": f"C{sector + 1:02d}",
            "type": "中心三角形",
            "ring": 0,
            "sector": sector + 1,
            "points": [rings[0][0], rings[1][sector], rings[1][(sector + 1) % SECTORS]],
        })

    for ring_index in range(1, len(RING_RATIOS) - 1):
        inner = rings[ring_index]
        outer = rings[ring_index + 1]
        for sector in range(SECTORS):
            panels.append({
                "piece": f"R{ring_index:02d}-{sector + 1:02d}",
                "type": "梯形/近梯形",
                "ring": ring_index,
                "sector": sector + 1,
                "points": [
                    inner[sector],
                    inner[(sector + 1) % SECTORS],
                    outer[(sector + 1) % SECTORS],
                    outer[sector],
                ],
            })
    return rings, panels


def write_obj(panels, center):
    OUT_MTL.write_text(
        "\n".join([
            "newmtl panel_a", "Kd 0.78 0.50 0.24",
            "newmtl panel_b", "Kd 0.92 0.68 0.38",
            "newmtl seam", "Kd 0.08 0.06 0.04",
            "",
        ]),
        encoding="utf-8",
    )
    lines = [f"mtllib {OUT_MTL.name}", "o umbrella_canopy_faceted_wood"]
    vertex_index = 1
    for idx, panel in enumerate(panels):
        points = panel["points"]
        solid = create_panel_vertices(points, center)
        count = len(points)
        lines.append(f"g {panel['piece']}_{panel['type']}")
        lines.append("usemtl panel_a" if idx % 2 == 0 else "usemtl panel_b")
        for v in solid:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        front = list(range(vertex_index, vertex_index + count))
        back = list(range(vertex_index + count, vertex_index + count * 2))
        lines.append("f " + " ".join(str(i) for i in front))
        lines.append("f " + " ".join(str(i) for i in reversed(back)))
        for i in range(count):
            lines.append(f"f {front[i]} {front[(i + 1) % count]} {back[(i + 1) % count]} {back[i]}")
        vertex_index += count * 2

    lines.append("g seam_lines")
    lines.append("usemtl seam")
    edge_map = {}
    for panel in panels:
        pts = panel["points"]
        for p0, p1 in zip(pts, pts[1:] + pts[:1]):
            key = tuple(sorted((tuple(round(v, 3) for v in p0), tuple(round(v, 3) for v in p1))))
            edge_map[key] = (p0, p1)
    for p0, p1 in edge_map.values():
        lines.append(f"v {p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}")
        lines.append(f"v {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f}")
        lines.append(f"l {vertex_index} {vertex_index + 1}")
        vertex_index += 2

    OUT_OBJ.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(panels):
    fields = [
        "piece",
        "type",
        "ring",
        "sector",
        "vertex_count",
        "area_cm2",
        "edge_lengths_cm",
        "diagonals_cm",
        "cut_xy_cm",
        "centroid_xyz_cm",
        "corner_xyz_cm",
        "note",
    ]
    rows = []
    for panel in panels:
        pts = panel["points"]
        centroid = sum(pts) / len(pts)
        diag = []
        if len(pts) == 4:
            diag = [float(np.linalg.norm(pts[2] - pts[0])), float(np.linalg.norm(pts[3] - pts[1]))]
        cut = flat_cut_coordinates(pts)
        rows.append({
            "piece": panel["piece"],
            "type": panel["type"],
            "ring": panel["ring"],
            "sector": panel["sector"],
            "vertex_count": len(pts),
            "area_cm2": round(polygon_area(pts), 3),
            "edge_lengths_cm": ";".join(f"{v:.2f}" for v in edge_lengths(pts)),
            "diagonals_cm": ";".join(f"{v:.2f}" for v in diag),
            "cut_xy_cm": " | ".join(f"({x:.2f},{y:.2f})" for x, y in cut),
            "centroid_xyz_cm": f"({centroid[0]:.2f},{centroid[1]:.2f},{centroid[2]:.2f})",
            "corner_xyz_cm": " | ".join(f"({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})" for p in pts),
            "note": "正視圖為傘面式多邊形分片；3D位置貼合第一版.blend內部圓弧擬合曲面。",
        })
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_svg(rings, panels, center, boundary, spoke_offset):
    width, height = 1400, 1200
    margin = 95
    xs = [p[0] for ring in rings[1:] for p in ring]
    zs = [p[2] for ring in rings[1:] for p in ring]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    scale = min((width - 2 * margin) / (max_x - min_x), (height - 2 * margin - 180) / (max_z - min_z))

    def pt3(p):
        return (
            margin + (p[0] - min_x) * scale,
            margin + (max_z - p[2]) * scale,
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif;fill:#0f172a}.title{font-size:34px;font-weight:800}.label{font-size:18px}.tiny{font-size:13px}</style>',
        '<text class="title" x="70" y="55">內部圓弧槽：傘面式木板分片正視圖</text>',
        f'<text class="label" x="70" y="88">{SECTORS}放射區 x {len(RING_RATIOS) - 1}層分帶，共{len(panels)}片；由中心向外徑向比例 2:1:1，外圈為正{SECTORS}邊形。</text>',
    ]
    for i, panel in enumerate(panels):
        coords = [pt3(p) for p in panel["points"]]
        color = "#d6a15f" if i % 2 == 0 else "#efc37a"
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
        parts.append(f'<polygon points="{points}" fill="{color}" stroke="#334155" stroke-width="1.8"/>')

    # Bold spoke and ring seams.
    for ring in rings[1:]:
        coords = [pt3(p) for p in ring]
        d = " ".join(("M" if i == 0 else "L") + f"{x:.2f},{y:.2f}" for i, (x, y) in enumerate(coords)) + " Z"
        parts.append(f'<path d="{d}" fill="none" stroke="#1f2937" stroke-width="2.2"/>')
    for sector in range(SECTORS):
        line = [rings[i][0] if i == 0 else rings[i][sector] for i in range(len(rings))]
        coords = [pt3(p) for p in line]
        d = " ".join(("M" if i == 0 else "L") + f"{x:.2f},{y:.2f}" for i, (x, y) in enumerate(coords))
        parts.append(f'<path d="{d}" fill="none" stroke="#1f2937" stroke-width="2.2"/>')

    # Label rings/sectors lightly.
    for panel in panels:
        p = sum(panel["points"]) / len(panel["points"])
        x, y = pt3(p)
        if panel["ring"] in (0, 2, len(RING_RATIOS) - 2):
            parts.append(f'<text class="tiny" x="{x:.2f}" y="{y:.2f}" text-anchor="middle">{panel["piece"]}</text>')

    parts.extend([
        f'<text class="label" x="70" y="{height - 72}">輸出：{OUT_OBJ.name} / {OUT_CSV.name}</text>',
        f'<text class="label" x="70" y="{height - 42}">板厚 {WOOD_THICKNESS_CM:.1f}cm；每片 CSV 內含邊長、對角線與平面裁切座標。</text>',
        "</svg>",
    ])
    OUT_SVG.write_text("\n".join(parts), encoding="utf-8")


def write_png_from_svg_like(rings, panels):
    # Minimal PNG raster for quick preview without external converters.
    W, H = 1400, 1200
    img = bytearray([248, 250, 252] * W * H)
    xs = [p[0] for ring in rings[1:] for p in ring]
    zs = [p[2] for ring in rings[1:] for p in ring]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    scale = min((W - 190) / (max_x - min_x), (H - 320) / (max_z - min_z))

    def pxy(p):
        return (95 + (p[0] - min_x) * scale, 115 + (max_z - p[2]) * scale)

    def blend(x, y, color, alpha=1.0):
        x, y = int(x), int(y)
        if not (0 <= x < W and 0 <= y < H):
            return
        idx = (y * W + x) * 3
        for k in range(3):
            img[idx + k] = int(img[idx + k] * (1 - alpha) + color[k] * alpha)

    def line(a, b, color):
        x0, y0 = map(round, a)
        x1, y1 = map(round, b)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    blend(x0 + ox, y0 + oy, color, 1)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill(poly, color, alpha):
        ymin = max(0, int(math.floor(min(y for _, y in poly))))
        ymax = min(H - 1, int(math.ceil(max(y for _, y in poly))))
        for y in range(ymin, ymax + 1):
            nodes = []
            j = len(poly) - 1
            for i in range(len(poly)):
                xi, yi = poly[i]
                xj, yj = poly[j]
                if (yi < y <= yj) or (yj < y <= yi):
                    nodes.append(xi + (y - yi) / (yj - yi) * (xj - xi))
                j = i
            nodes.sort()
            for a, b in zip(nodes[0::2], nodes[1::2]):
                for x in range(max(0, int(a)), min(W - 1, int(b)) + 1):
                    blend(x, y, color, alpha)

    for i, panel in enumerate(panels):
        poly = [pxy(p) for p in panel["points"]]
        fill(poly, (214, 161, 95) if i % 2 == 0 else (239, 195, 122), 0.95)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            line(a, b, (31, 41, 55))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    rows = b"".join(b"\x00" + bytes(img[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 6))
        + chunk(b"IEND", b"")
    )
    OUT_PNG.write_bytes(png)


def main():
    verts, faces = load_original_mesh()
    target_points = []
    for face in faces:
        points = [verts[i] for i in face]
        n = normal(points)
        if is_trough_face(points, n):
            target_points.extend(points)

    unique = []
    seen = set()
    for p in target_points:
        key = tuple(round(float(v), 4) for v in p)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    center, radius, rms = fit_sphere(unique)
    projected = [(float(p[0]), float(p[2])) for p in unique]
    boundary, spoke_offset = boundary_radii(projected, center[0], center[2])
    rings, panels = build_panels(center, radius, boundary, spoke_offset)

    write_obj(panels, center)
    write_csv(panels)
    write_svg(rings, panels, center, boundary, spoke_offset)
    write_png_from_svg_like(rings, panels)

    print(f"sphere_center=({center[0]:.3f},{center[1]:.3f},{center[2]:.3f}) radius={radius:.3f} rms={rms:.4f}cm")
    print(f"panels={len(panels)} sectors={SECTORS} rings={len(RING_RATIOS)-1}")
    print(OUT_OBJ)
    print(OUT_CSV)
    print(OUT_SVG)
    print(OUT_PNG)


if __name__ == "__main__":
    main()
