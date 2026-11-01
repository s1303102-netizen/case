import csv
import json
import math
import pathlib
import re
import struct
from collections import defaultdict

import zstandard as zstd


ROOT = pathlib.Path("/Users/alissachang/大專")
BLEND = ROOT / "第一版.blend"
OUT_JSON = ROOT / "第一版_mesh解析.json"
OUT_CSV = ROOT / "第一版_曲面候選邊.csv"


def align4(offset):
    return (offset + 3) & ~3


def read_cstring(data, offset=0):
    end = data.find(b"\0", offset)
    if end < 0:
        end = len(data)
    return data[offset:end].decode("utf-8", "replace")


def cstring_table(data, offset, count):
    items = []
    pos = offset
    for _ in range(count):
        end = data.index(b"\0", pos)
        items.append(data[pos:end].decode("utf-8", "replace"))
        pos = end + 1
    return items, align4(pos)


def array_count(name):
    count = 1
    for value in re.findall(r"\[([0-9]+)\]", name):
        count *= int(value)
    return count


def decompress_blend(path):
    with zstd.ZstdDecompressor().stream_reader(path.open("rb")) as reader:
        chunks = []
        while True:
            chunk = reader.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def parse_dna(data):
    pos = 0
    assert data[pos:pos + 4] == b"SDNA"
    pos += 4
    assert data[pos:pos + 4] == b"NAME"
    pos += 4
    name_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    names, pos = cstring_table(data, pos, name_count)
    assert data[pos:pos + 4] == b"TYPE"
    pos += 4
    type_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    types, pos = cstring_table(data, pos, type_count)
    assert data[pos:pos + 4] == b"TLEN"
    pos += 4
    tlens = list(struct.unpack_from("<" + "H" * type_count, data, pos))
    pos = align4(pos + 2 * type_count)
    assert data[pos:pos + 4] == b"STRC"
    pos += 4
    struct_count = struct.unpack_from("<I", data, pos)[0]
    pos += 4

    type_size = dict(zip(types, tlens))
    structs = []
    for _ in range(struct_count):
        type_idx, field_count = struct.unpack_from("<HH", data, pos)
        pos += 4
        fields = []
        offset = 0
        for _ in range(field_count):
            field_type_idx, name_idx = struct.unpack_from("<HH", data, pos)
            pos += 4
            field_type = types[field_type_idx]
            name = names[name_idx]
            size = (8 if "*" in name else type_size[field_type]) * array_count(name)
            fields.append({"offset": offset, "type": field_type, "name": name, "size": size})
            offset += size
        structs.append({"type": types[type_idx], "size": tlens[type_idx], "fields": fields})
    return structs


def parse_blocks(raw):
    blocks = []
    offset = 17
    while offset + 32 <= len(raw):
        code = raw[offset:offset + 4].decode("ascii", "replace").rstrip("\0")
        sdna = struct.unpack_from("<I", raw, offset + 4)[0]
        oldptr = struct.unpack_from("<Q", raw, offset + 8)[0]
        size = struct.unpack_from("<I", raw, offset + 16)[0]
        count = struct.unpack_from("<I", raw, offset + 24)[0]
        data_offset = offset + 32
        blocks.append({
            "offset": offset,
            "code": code,
            "sdna": sdna,
            "oldptr": oldptr,
            "size": size,
            "count": count,
            "data_offset": data_offset,
            "data": raw[data_offset:data_offset + size],
        })
        offset = data_offset + size
        if code == "ENDB":
            break
    return blocks


def block_by_old(blocks):
    return {block["oldptr"]: block for block in blocks if block["oldptr"]}


def read_ptr(data, offset):
    return struct.unpack_from("<Q", data, offset)[0]


def read_i32(data, offset):
    return struct.unpack_from("<i", data, offset)[0]


def read_f32x3(data, offset):
    return struct.unpack_from("<fff", data, offset)


def get_struct_index(structs, name):
    for i, dna_struct in enumerate(structs):
        if dna_struct["type"] == name:
            return i
    raise KeyError(name)


def main():
    raw = decompress_blend(BLEND)
    blocks = parse_blocks(raw)
    dna_block = next(block for block in blocks if block["code"] == "DNA1")
    structs = parse_dna(dna_block["data"])
    by_old = block_by_old(blocks)

    mesh_index = get_struct_index(structs, "Mesh")
    object_index = get_struct_index(structs, "Object")
    mesh_blocks = [block for block in blocks if block["sdna"] == mesh_index and block["code"].startswith("ME")]
    object_blocks = [block for block in blocks if block["sdna"] == object_index and block["code"].startswith("OB")]
    if not mesh_blocks:
        raise RuntimeError("No Mesh block found")
    mesh_block = mesh_blocks[0]
    mesh = mesh_block["data"]

    object_block = None
    for candidate in object_blocks:
        if read_ptr(candidate["data"], 560) == mesh_block["oldptr"]:
            object_block = candidate
            break
    if object_block is None:
        raise RuntimeError("No Object block linked to Mesh")

    loc = read_f32x3(object_block["data"], 744)
    scale = read_f32x3(object_block["data"], 768)
    totvert = read_i32(mesh, 432)
    totpoly = read_i32(mesh, 440)
    totloop = read_i32(mesh, 444)
    poly_offsets_ptr = read_ptr(mesh, 448)

    attrs_ptr = read_ptr(mesh, 456)
    attrs_num = read_i32(mesh, 464)
    attrs_block = by_old[attrs_ptr]
    attrs = []
    for i in range(attrs_num):
        offset = i * 24
        attr_data = attrs_block["data"][offset:offset + 24]
        name_ptr = read_ptr(attr_data, 0)
        data_type = struct.unpack_from("<h", attr_data, 8)[0]
        domain = struct.unpack_from("<b", attr_data, 10)[0]
        storage_type = struct.unpack_from("<b", attr_data, 11)[0]
        data_ptr = read_ptr(attr_data, 16)
        name = read_cstring(by_old[name_ptr]["data"]) if name_ptr in by_old else f"<name:{name_ptr:x}>"
        attrs.append({
            "name": name,
            "data_type": data_type,
            "domain": domain,
            "storage_type": storage_type,
            "data_ptr": data_ptr,
        })

    attr_arrays = {}
    for attr in attrs:
        data_holder = by_old.get(attr["data_ptr"])
        if not data_holder:
            continue
        holder = data_holder["data"]
        if len(holder) >= 32:
            raw_ptr = read_ptr(holder, 0)
            size = struct.unpack_from("<q", holder, 16)[0]
            is_single = struct.unpack_from("<b", holder, 24)[0]
            attr_arrays[attr["name"]] = {
                **attr,
                "array_ptr": raw_ptr,
                "array_size": size,
                "is_single": is_single,
                "raw": by_old[raw_ptr]["data"] if raw_ptr in by_old else b"",
            }

    positions_attr = attr_arrays.get("position")
    corner_vert_attr = attr_arrays.get(".corner_vert")
    corner_edge_attr = attr_arrays.get(".corner_edge")
    if not positions_attr or not corner_vert_attr:
        raise RuntimeError(f"Missing required mesh attributes: {list(attr_arrays)}")

    verts = []
    for i in range(totvert):
        x, y, z = struct.unpack_from("<fff", positions_attr["raw"], i * 12)
        verts.append((loc[0] + x * scale[0], loc[1] + y * scale[1], loc[2] + z * scale[2]))

    corner_verts = [struct.unpack_from("<i", corner_vert_attr["raw"], i * 4)[0] for i in range(totloop)]
    poly_offsets_raw = by_old[poly_offsets_ptr]["data"]
    poly_offsets = [struct.unpack_from("<i", poly_offsets_raw, i * 4)[0] for i in range(totpoly + 1)]
    faces = []
    for i in range(totpoly):
        start, end = poly_offsets[i], poly_offsets[i + 1]
        faces.append(corner_verts[start:end])

    bbox_min = [min(v[i] for v in verts) for i in range(3)]
    bbox_max = [max(v[i] for v in verts) for i in range(3)]

    # Candidate curved surfaces: long faces whose vertices span the full X length.
    long_edges = []
    for face_index, face in enumerate(faces):
        pts = [verts[i] for i in face]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        zs = [p[2] for p in pts]
        if max(xs) - min(xs) < 100:
            continue
        # A board strip generated from a curved surface will usually have one
        # short edge in the YZ section and the full machine length in X.
        yz_pairs = sorted({(round(p[1], 6), round(p[2], 6)) for p in pts})
        if len(yz_pairs) != 2:
            continue
        (y0, z0), (y1, z1) = yz_pairs
        width = math.hypot(y1 - y0, z1 - z0)
        if width < 0.05 or width > 20:
            continue
        cy = (y0 + y1) / 2
        cz = (z0 + z1) / 2
        angle = math.degrees(math.atan2(z1 - z0, y1 - y0))
        long_edges.append({
            "face": face_index,
            "y0": y0,
            "z0": z0,
            "y1": y1,
            "z1": z1,
            "cy": cy,
            "cz": cz,
            "width": width,
            "angle": angle,
            "x_min": min(xs),
            "x_max": max(xs),
        })

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["face", "x_min", "x_max", "y0", "z0", "y1", "z1", "cy", "cz", "width", "angle"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in sorted(long_edges, key=lambda r: (r["cz"], r["cy"], r["face"])):
            writer.writerow(row)

    summary = {
        "mesh_oldptr": hex(mesh_block["oldptr"]),
        "object_oldptr": hex(object_block["oldptr"]),
        "loc": loc,
        "scale": scale,
        "totvert": totvert,
        "totpoly": totpoly,
        "totloop": totloop,
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "attributes": attrs,
        "attribute_arrays": {
            name: {k: v for k, v in attr.items() if k != "raw"}
            for name, attr in attr_arrays.items()
        },
        "long_curve_candidate_count": len(long_edges),
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
