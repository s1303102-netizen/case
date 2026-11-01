import importlib.util
import math
import pathlib
import struct
import zlib


ROOT = pathlib.Path("/Users/alissachang/大專")
OUT = ROOT / "第一版_mesh投影檢查.png"

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
        verts.append((loc[0] + x * scale[0], loc[1] + y * scale[1], loc[2] + z * scale[2]))
    corners = [struct.unpack_from("<i", attrs[".corner_vert"], i * 4)[0] for i in range(totloop)]
    offsets_raw = by[pom.read_ptr(mesh, 448)]["data"]
    offsets = [struct.unpack_from("<i", offsets_raw, i * 4)[0] for i in range(totpoly + 1)]
    faces = [corners[offsets[i]:offsets[i + 1]] for i in range(totpoly)]
    return verts, faces


W, H = 1800, 1200
img = bytearray([248, 250, 252] * W * H)


def blend_pixel(x, y, color, alpha=1.0):
    if x < 0 or x >= W or y < 0 or y >= H:
        return
    i = (y * W + x) * 3
    for k in range(3):
        img[i + k] = int(img[i + k] * (1 - alpha) + color[k] * alpha)


def draw_line(x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = map(int, map(round, (x0, y0, x1, y1)))
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        blend_pixel(x0, y0, color, alpha)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def fill_poly(poly, color, alpha):
    if len(poly) < 3:
        return
    ymin = max(0, int(math.floor(min(y for _, y in poly))))
    ymax = min(H - 1, int(math.ceil(max(y for _, y in poly))))
    for y in range(ymin, ymax + 1):
        nodes = []
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi < y <= yj) or (yj < y <= yi):
                x = xi + (y - yi) / (yj - yi) * (xj - xi)
                nodes.append(x)
            j = i
        nodes.sort()
        for a, b in zip(nodes[0::2], nodes[1::2]):
            xa = max(0, int(math.floor(a)))
            xb = min(W - 1, int(math.ceil(b)))
            for x in range(xa, xb + 1):
                blend_pixel(x, y, color, alpha)


def rect(x, y, w, h, color):
    for xx in range(x, x + w):
        blend_pixel(xx, y, color, 1)
        blend_pixel(xx, y + h, color, 1)
    for yy in range(y, y + h):
        blend_pixel(x, yy, color, 1)
        blend_pixel(x + w, yy, color, 1)


def normal(points):
    if len(points) < 3:
        return (0, 0, 0)
    ax, ay, az = (points[1][i] - points[0][i] for i in range(3))
    bx, by, bz = (points[2][i] - points[0][i] for i in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    return nx / length, ny / length, nz / length


verts, faces = load_mesh()
min_x, max_x = min(v[0] for v in verts), max(v[0] for v in verts)
min_y, max_y = min(v[1] for v in verts), max(v[1] for v in verts)
min_z, max_z = min(v[2] for v in verts), max(v[2] for v in verts)


def project(points, mode, ox, oy, w, h):
    if mode == "top":
        values = [(p[0], p[1]) for p in points]
        umin, umax, vmin, vmax = min_x, max_x, min_y, max_y
    elif mode == "front":
        values = [(p[0], p[2]) for p in points]
        umin, umax, vmin, vmax = min_x, max_x, min_z, max_z
    else:
        values = [(p[1], p[2]) for p in points]
        umin, umax, vmin, vmax = min_y, max_y, min_z, max_z
    return [
        (
            ox + (u - umin) / (umax - umin) * w,
            oy + h - (v - vmin) / (vmax - vmin) * h,
        )
        for u, v in values
    ]


def face_color(points, n):
    cy = sum(p[1] for p in points) / len(points)
    cz = sum(p[2] for p in points) / len(points)
    xspan = max(p[0] for p in points) - min(p[0] for p in points)
    # Red is the current hypothesis for the interior concave umbrella trough:
    # non-flat curved/bowl faces, facing toward +Y, away from exterior plates.
    if n[1] > 0.35 and -18 < cy < 18 and 8 < cz < 122 and xspan < 80:
        return (239, 68, 68), 0.72
    if abs(n[2]) > 0.85:
        return (147, 197, 253), 0.30
    if abs(n[1]) > 0.85:
        return (167, 243, 208), 0.28
    if abs(n[0]) > 0.85:
        return (221, 214, 254), 0.28
    return (251, 191, 36), 0.36


views = [
    ("top", 60, 90, 760, 300),
    ("front", 60, 460, 760, 620),
    ("side", 930, 90, 760, 990),
]
for mode, ox, oy, w, h in views:
    rect(ox, oy, w, h, (203, 213, 225))
    if mode == "top":
        key = lambda face: sum(verts[i][2] for i in face) / len(face)
    elif mode == "front":
        key = lambda face: sum(verts[i][1] for i in face) / len(face)
    else:
        key = lambda face: sum(verts[i][0] for i in face) / len(face)
    for face in sorted(faces, key=key):
        pts = [verts[i] for i in face]
        n = normal(pts)
        color, alpha = face_color(pts, n)
        poly = project(pts, mode, ox, oy, w, h)
        fill_poly(poly, color, alpha)
        for p0, p1 in zip(poly, poly[1:] + poly[:1]):
            draw_line(p0[0], p0[1], p1[0], p1[1], (51, 65, 85), 0.28)


def png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)


raw_rows = b"".join(b"\x00" + bytes(img[y * W * 3:(y + 1) * W * 3]) for y in range(H))
png = (
    b"\x89PNG\r\n\x1a\n"
    + png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    + png_chunk(b"IDAT", zlib.compress(raw_rows, 6))
    + png_chunk(b"IEND", b"")
)
OUT.write_bytes(png)
print(OUT)
