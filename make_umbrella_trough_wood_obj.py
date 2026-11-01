import csv
import importlib.util
import math
import pathlib
import struct


ROOT = pathlib.Path("/Users/alissachang/大專")
OUT_OBJ = ROOT / "內部圓弧木板結構預覽.obj"
OUT_MTL = ROOT / "內部圓弧木板結構預覽.mtl"
OUT_CSV = ROOT / "內部圓弧木板板件尺寸.csv"
WOOD_THICKNESS_CM = 0.9
SEAM_OFFSET_CM = 0.035

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


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def normalize(a):
    l = length(a) or 1
    return (a[0] / l, a[1] / l, a[2] / l)


def normal(points):
    if len(points) < 3:
        return (0, 1, 0)
    return normalize(cross(sub(points[1], points[0]), sub(points[2], points[0])))


def is_trough_face(points, n):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    xspan = max(xs) - min(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)
    return n[1] > 0.20 and xspan <= 8.5 and -18 < cy < 18 and 8 < cz < 122


def poly_area(points):
    if len(points) < 3:
        return 0
    origin = points[0]
    area = 0
    for i in range(1, len(points) - 1):
        area += length(cross(sub(points[i], origin), sub(points[i + 1], origin))) / 2
    return area


def edge_lengths(points):
    return [length(sub(points[(i + 1) % len(points)], points[i])) for i in range(len(points))]


def main():
    verts, faces = load_mesh()
    target = []
    for face_index, face in enumerate(faces):
        points = [verts[i] for i in face]
        n = normal(points)
        if is_trough_face(points, n):
            target.append((face_index, points, n))

    OUT_MTL.write_text(
        "newmtl wood_a\nKd 0.78 0.50 0.24\nnewmtl wood_b\nKd 0.92 0.68 0.38\n",
        encoding="utf-8",
    )

    obj_lines = [f"mtllib {OUT_MTL.name}", "o umbrella_trough_wood_panels"]
    rows = []
    vertex_offset = 1
    for piece_index, (face_index, points, n) in enumerate(target, start=1):
        front = [add(p, mul(n, SEAM_OFFSET_CM)) for p in points]
        back = [add(p, mul(n, SEAM_OFFSET_CM - WOOD_THICKNESS_CM)) for p in points]
        panel_vertices = front + back
        obj_lines.append(f"g TroughPanel_{piece_index:03d}_F{face_index}")
        obj_lines.append("usemtl wood_a" if piece_index % 2 else "usemtl wood_b")
        for v in panel_vertices:
            obj_lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
        count = len(points)
        front_idx = list(range(vertex_offset, vertex_offset + count))
        back_idx = list(range(vertex_offset + count, vertex_offset + count * 2))
        obj_lines.append("f " + " ".join(str(i) for i in front_idx))
        obj_lines.append("f " + " ".join(str(i) for i in reversed(back_idx)))
        for i in range(count):
            a = front_idx[i]
            b = front_idx[(i + 1) % count]
            c = back_idx[(i + 1) % count]
            d = back_idx[i]
            obj_lines.append(f"f {a} {b} {c} {d}")
        vertex_offset += count * 2

        cx = sum(p[0] for p in points) / count
        cy = sum(p[1] for p in points) / count
        cz = sum(p[2] for p in points) / count
        rows.append({
            "piece": f"T{piece_index:03d}",
            "source_face": face_index,
            "vertex_count": count,
            "area_cm2": round(poly_area(points), 3),
            "edge_lengths_cm": ";".join(f"{v:.2f}" for v in edge_lengths(points)),
            "centroid_x_cm": round(cx, 3),
            "centroid_y_cm": round(cy, 3),
            "centroid_z_cm": round(cz, 3),
            "normal_x": round(n[0], 5),
            "normal_y": round(n[1], 5),
            "normal_z": round(n[2], 5),
            "corner_xyz_cm": " | ".join(f"({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})" for p in points),
            "note": "內部容傘圓弧面分片；此板件依第一版.blend原始面片建立。",
        })

    OUT_OBJ.write_text("\n".join(obj_lines) + "\n", encoding="utf-8")

    fields = [
        "piece", "source_face", "vertex_count", "area_cm2", "edge_lengths_cm",
        "centroid_x_cm", "centroid_y_cm", "centroid_z_cm",
        "normal_x", "normal_y", "normal_z", "corner_xyz_cm", "note",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"panels={len(target)}")
    print(OUT_OBJ)
    print(OUT_CSV)


if __name__ == "__main__":
    main()
