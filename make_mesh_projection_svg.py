import importlib.util
import math
import pathlib
import struct


ROOT = pathlib.Path("/Users/alissachang/大專")
OUT = ROOT / "第一版_mesh投影檢查.svg"

spec = importlib.util.spec_from_file_location("pom", ROOT / "parse_original_mesh.py")
pom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pom)


def load_mesh():
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
    attrs_ptr = pom.read_ptr(mesh, 456)
    attrs_num = pom.read_i32(mesh, 464)
    attrs_block = by[attrs_ptr]
    attrs = {}
    for i in range(attrs_num):
        d = attrs_block["data"][i * 24:i * 24 + 24]
        name = pom.read_cstring(by[pom.read_ptr(d, 0)]["data"])
        data_ptr = pom.read_ptr(d, 16)
        holder = by[data_ptr]["data"]
        attrs[name] = by[pom.read_ptr(holder, 0)]["data"]
    verts = []
    for i in range(totvert):
        x, y, z = struct.unpack_from("<fff", attrs["position"], i * 12)
        verts.append((loc[0] + x * scale[0], loc[1] + y * scale[1], loc[2] + z * scale[2]))
    corners = [struct.unpack_from("<i", attrs[".corner_vert"], i * 4)[0] for i in range(totloop)]
    offsets_raw = by[pom.read_ptr(mesh, 448)]["data"]
    offsets = [struct.unpack_from("<i", offsets_raw, i * 4)[0] for i in range(totpoly + 1)]
    faces = [corners[offsets[i]:offsets[i + 1]] for i in range(totpoly)]
    return verts, faces


def normal(points):
    if len(points) < 3:
        return (0, 0, 0)
    ax = points[1][0] - points[0][0]
    ay = points[1][1] - points[0][1]
    az = points[1][2] - points[0][2]
    bx = points[2][0] - points[0][0]
    by = points[2][1] - points[0][1]
    bz = points[2][2] - points[0][2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    return nx / length, ny / length, nz / length


verts, faces = load_mesh()
min_x, max_x = min(v[0] for v in verts), max(v[0] for v in verts)
min_y, max_y = min(v[1] for v in verts), max(v[1] for v in verts)
min_z, max_z = min(v[2] for v in verts), max(v[2] for v in verts)


def project(points, mode, ox, oy, w, h):
    if mode == "top":
        uvals = [p[0] for p in points]
        vvals = [p[1] for p in points]
        umin, umax, vmin, vmax = min_x, max_x, min_y, max_y
    elif mode == "front":
        uvals = [p[0] for p in points]
        vvals = [p[2] for p in points]
        umin, umax, vmin, vmax = min_x, max_x, min_z, max_z
    else:
        uvals = [p[1] for p in points]
        vvals = [p[2] for p in points]
        umin, umax, vmin, vmax = min_y, max_y, min_z, max_z
    return [
        (
            ox + (u - umin) / (umax - umin) * w,
            oy + h - (v - vmin) / (vmax - vmin) * h,
        )
        for u, v in zip(uvals, vvals)
    ]


def color_for(points, n):
    cz = sum(p[2] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    if n[1] > 0.45 and -18 < cy < 18 and 5 < cz < 122:
        return "#ef4444", 0.72
    if abs(n[2]) > 0.85:
        return "#93c5fd", 0.38
    if abs(n[1]) > 0.85:
        return "#a7f3d0", 0.34
    if abs(n[0]) > 0.85:
        return "#ddd6fe", 0.32
    return "#fbbf24", 0.42


parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1200" viewBox="0 0 1800 1200">',
    '<rect width="100%" height="100%" fill="#f8fafc"/>',
    '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif;fill:#0f172a}.title{font-size:28px;font-weight:800}.label{font-size:18px}</style>',
    '<text class="title" x="60" y="48">第一版.blend mesh 投影檢查：紅色為可能的內部凹圓弧面候選</text>',
]
views = [("top", 60, 90, 760, 300, "俯視 X-Y"), ("front", 60, 460, 760, 620, "正視 X-Z"), ("side", 930, 90, 760, 990, "側視 Y-Z")]
for mode, ox, oy, w, h, label in views:
    parts.append(f'<text class="label" x="{ox}" y="{oy - 16}">{label}</text>')
    parts.append(f'<rect x="{ox}" y="{oy}" width="{w}" height="{h}" fill="#fff" stroke="#cbd5e1"/>')
    # Sort approximately back-to-front by average hidden axis.
    if mode == "top":
        key = lambda fp: sum(verts[i][2] for i in fp) / len(fp)
    elif mode == "front":
        key = lambda fp: sum(verts[i][1] for i in fp) / len(fp)
    else:
        key = lambda fp: sum(verts[i][0] for i in fp) / len(fp)
    for face in sorted(faces, key=key):
        pts = [verts[i] for i in face]
        n = normal(pts)
        fill, opacity = color_for(pts, n)
        poly = project(pts, mode, ox, oy, w, h)
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in poly)
        parts.append(f'<polygon points="{d}" fill="{fill}" fill-opacity="{opacity}" stroke="#334155" stroke-opacity="0.35" stroke-width="0.5"/>')
parts.append("</svg>")
OUT.write_text("\n".join(parts), encoding="utf-8")
print(OUT)
