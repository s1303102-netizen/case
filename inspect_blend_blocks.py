import collections
import json
import pathlib
import struct


PATH = pathlib.Path("/Users/alissachang/大專/第一版_decompressed.blend")


def align4(offset):
    return (offset + 3) & ~3


def cstring_table(data, offset, count):
    items = []
    pos = offset
    for _ in range(count):
        end = data.index(b"\0", pos)
        items.append(data[pos:end].decode("utf-8", "replace"))
        pos = end + 1
    return items, align4(pos)


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
    structs = []
    for _ in range(struct_count):
        type_idx, field_count = struct.unpack_from("<HH", data, pos)
        pos += 4
        fields = []
        for _ in range(field_count):
            field_type, name_idx = struct.unpack_from("<HH", data, pos)
            pos += 4
            fields.append((types[field_type], names[name_idx], tlens[field_type]))
        structs.append({"type": types[type_idx], "fields": fields, "size": tlens[type_idx]})
    return {"names": names, "types": types, "tlens": tlens, "structs": structs}


raw = PATH.read_bytes()
header_len = 17
block_header = 32
blocks = []
off = header_len
while off + block_header <= len(raw):
    code = raw[off:off + 4].decode("ascii", "replace")
    size = struct.unpack_from("<I", raw, off + 16)[0]
    sdna = struct.unpack_from("<I", raw, off + 20)[0]
    count = struct.unpack_from("<I", raw, off + 24)[0]
    oldptr = struct.unpack_from("<Q", raw, off + 8)[0]
    data_off = off + block_header
    blocks.append({"off": off, "code": code, "size": size, "sdna": sdna, "count": count, "oldptr": oldptr, "data_off": data_off})
    off = data_off + size
    if code == "ENDB":
        break

dna_block = next(b for b in blocks if b["code"] == "DNA1")
dna = parse_dna(raw[dna_block["data_off"]:dna_block["data_off"] + dna_block["size"]])
type_by_sdna = {i: s["type"] for i, s in enumerate(dna["structs"])}

counts = collections.Counter(type_by_sdna.get(b["sdna"], "?") for b in blocks)
print("blocks", len(blocks))
print("top types")
for typ, cnt in counts.most_common(40):
    print(cnt, typ)

print("\nselected blocks")
for b in blocks:
    typ = type_by_sdna.get(b["sdna"], "?")
    if b["code"] in {"DATA", "OB  ", "ME  ", "DNA1"} or typ in {"Mesh", "Object", "MVert", "MPoly", "MLoop", "MEdge", "float3", "vec3f", "CustomDataLayer", "ID"}:
        print(b["off"], b["code"], "type", typ, "size", b["size"], "count", b["count"], "old", hex(b["oldptr"]))

for typ in ["Mesh", "Object", "ID", "CustomData", "CustomDataLayer", "float3", "vec3f", "MVert", "MPoly", "MLoop", "MEdge"]:
    for i, s in enumerate(dna["structs"]):
        if s["type"] == typ:
            print("\nSTRUCT", i, typ, "size", s["size"])
            for ftyp, name, flen in s["fields"][:120]:
                print(" ", ftyp, name, flen)
            break
