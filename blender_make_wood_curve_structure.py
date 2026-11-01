"""
Run this script inside Blender. It reads the mesh in 第一版.blend, extracts the
side-profile curve from the original geometry, then builds a segmented plywood
construction model with boards, ribs, backer strips, labels, and a dimension CSV.

The file's numeric units are treated as centimeters because the source model is
140 x 50 x 125 for a real 140cm x 50cm x 125cm shell.
"""

from __future__ import annotations

import csv
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path("/Users/alissachang/大專")
SOURCE_BLEND = ROOT / "第一版.blend"
OUTPUT_BLEND = ROOT / "木板曲面結構_精準分段.blend"
OUTPUT_CSV = ROOT / "木板曲面板件尺寸.csv"
OUTPUT_SVG = ROOT / "木板曲面剖面尺寸圖.svg"

WOOD_THICKNESS_CM = 0.9
RIB_THICKNESS_CM = 1.2
BACKER_WIDTH_CM = 3.0
BACKER_DEPTH_CM = 1.8
RIB_SPACING_CM = 28.0
SEGMENT_EPS_CM = 0.02

GENERATED_PREFIXES = (
    "WoodPanel_",
    "Rib_",
    "Backer_",
    "DimLabel_",
    "CurvePoint_",
    "CurveRef_",
    "OriginalProfile_",
)
GENERATED_COLLECTION = "木板分段曲面結構"


def remove_generated_objects() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(GENERATED_PREFIXES):
            bpy.data.objects.remove(obj, do_unlink=True)
    old = bpy.data.collections.get(GENERATED_COLLECTION)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)


def ensure_collection() -> bpy.types.Collection:
    remove_generated_objects()
    collection = bpy.data.collections.new(GENERATED_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = color[3]
        bsdf.inputs["Roughness"].default_value = 0.68
    mat.blend_method = "BLEND"
    mat.use_screen_refraction = True
    return mat


def link_obj(collection: bpy.types.Collection, obj: bpy.types.Object) -> None:
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    for col in list(obj.users_collection):
        if col != collection and obj.name in col.objects:
            col.objects.unlink(obj)


def largest_mesh_object() -> bpy.types.Object:
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("找不到 mesh 物件。請確認已開啟 第一版.blend。")

    def volume(obj: bpy.types.Object) -> float:
        dims = obj.dimensions
        return abs(dims.x * dims.y * dims.z)

    return max(meshes, key=volume)


def ordered_boundary_loops(edges: list[tuple[int, int]]) -> list[list[int]]:
    unused = {tuple(sorted(edge)) for edge in edges}
    adj: dict[int, set[int]] = defaultdict(set)
    for a, b in unused:
        adj[a].add(b)
        adj[b].add(a)

    loops: list[list[int]] = []
    while unused:
        start_edge = min(unused)
        start, nxt = start_edge
        loop = [start]
        prev = None
        cur = start
        next_vertex = nxt

        while True:
            edge = tuple(sorted((cur, next_vertex)))
            unused.discard(edge)
            prev, cur = cur, next_vertex
            if cur == start:
                break
            loop.append(cur)
            candidates = sorted(adj[cur] - ({prev} if prev is not None else set()))
            if not candidates:
                break
            next_vertex = candidates[0]

        if len(loop) >= 3:
            loops.append(loop)
    return loops


def polygon_area_yz(points: list[Vector]) -> float:
    area = 0.0
    for i, p0 in enumerate(points):
        p1 = points[(i + 1) % len(points)]
        area += p0.y * p1.z - p1.y * p0.z
    return area / 2.0


def loop_length_yz(points: list[Vector]) -> float:
    total = 0.0
    for i, p0 in enumerate(points):
        p1 = points[(i + 1) % len(points)]
        total += math.hypot(p1.y - p0.y, p1.z - p0.z)
    return total


def get_end_profile(obj: bpy.types.Object) -> tuple[list[Vector], float, float, float, float]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    try:
        world = obj.matrix_world
        verts = [world @ v.co for v in mesh.vertices]
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        zs = [v.z for v in verts]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        z_min, z_max = min(zs), max(zs)
        tol = max(x_max - x_min, y_max - y_min, z_max - z_min) * 1e-5

        best_loop: list[int] | None = None
        best_plane_x = x_min
        best_score = -1.0

        for plane_x in (x_min, x_max):
            cap_faces = [
                poly for poly in mesh.polygons
                if all(abs(verts[i].x - plane_x) <= tol for i in poly.vertices)
            ]
            edge_counts: Counter[tuple[int, int]] = Counter()
            for poly in cap_faces:
                ids = list(poly.vertices)
                for a, b in zip(ids, ids[1:] + ids[:1]):
                    edge_counts[tuple(sorted((a, b)))] += 1
            boundary_edges = [edge for edge, count in edge_counts.items() if count == 1]
            loops = ordered_boundary_loops(boundary_edges)
            for loop in loops:
                pts = [verts[i] for i in loop]
                score = abs(polygon_area_yz(pts)) + loop_length_yz(pts) * 0.01
                if score > best_score:
                    best_score = score
                    best_loop = loop
                    best_plane_x = plane_x

        if not best_loop:
            raise RuntimeError("無法從端面找出封閉剖面輪廓。")

        profile = [verts[i].copy() for i in best_loop]
        if polygon_area_yz(profile) < 0:
            profile.reverse()

        return profile, x_min, x_max, y_min, y_max
    finally:
        eval_obj.to_mesh_clear()


def consecutive_groups(flags: list[bool]) -> list[list[int]]:
    n = len(flags)
    if not any(flags):
        return []
    if all(flags):
        return [list(range(n))]

    start = next(i for i, flag in enumerate(flags) if not flag)
    groups: list[list[int]] = []
    current: list[int] = []
    for step in range(1, n + 1):
        i = (start + step) % n
        if flags[i]:
            current.append(i)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def extract_main_curve(profile: list[Vector]) -> list[Vector]:
    n = len(profile)
    lengths: list[float] = []
    flags: list[bool] = []
    for i, p0 in enumerate(profile):
        p1 = profile[(i + 1) % n]
        dy = abs(p1.y - p0.y)
        dz = abs(p1.z - p0.z)
        length = math.hypot(dy, dz)
        lengths.append(length)
        flags.append(dy > SEGMENT_EPS_CM and dz > SEGMENT_EPS_CM and length > SEGMENT_EPS_CM)

    groups = consecutive_groups(flags)
    if not groups:
        raise RuntimeError("找不到同時改變 Y/Z 的曲面段。請確認模型端面包含曲線。")

    def group_score(group: list[int]) -> float:
        total_len = sum(lengths[i] for i in group)
        pts = [profile[group[0]]] + [profile[(i + 1) % n] for i in group]
        vertical_drop = abs(pts[-1].z - pts[0].z)
        return total_len + vertical_drop * 0.35

    group = max(groups, key=group_score)
    curve = [profile[group[0]].copy()]
    for i in group:
        curve.append(profile[(i + 1) % n].copy())

    if curve[0].z < curve[-1].z:
        curve.reverse()
    return curve


def outward_normal_yz(profile: list[Vector], p0: Vector, p1: Vector) -> Vector:
    centroid = Vector((
        0.0,
        sum(p.y for p in profile) / len(profile),
        sum(p.z for p in profile) / len(profile),
    ))
    dy = p1.y - p0.y
    dz = p1.z - p0.z
    length = math.hypot(dy, dz)
    if length == 0:
        return Vector((0, 1, 0))
    n1 = Vector((0.0, dz / length, -dy / length))
    mid = (p0 + p1) * 0.5
    if (mid + n1 - centroid).length >= (mid - n1 - centroid).length:
        return n1
    return -n1


def create_mesh_object(
    name: str,
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    link_obj(collection, obj)
    return obj


def create_curve_board(
    name: str,
    x_min: float,
    x_max: float,
    p0: Vector,
    p1: Vector,
    normal: Vector,
    thickness: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    offset = normal * 0.03
    inner = normal * -thickness
    v = [
        Vector((x_min, p0.y, p0.z)) + offset,
        Vector((x_min, p1.y, p1.z)) + offset,
        Vector((x_max, p1.y, p1.z)) + offset,
        Vector((x_max, p0.y, p0.z)) + offset,
        Vector((x_min, p0.y, p0.z)) + offset + inner,
        Vector((x_min, p1.y, p1.z)) + offset + inner,
        Vector((x_max, p1.y, p1.z)) + offset + inner,
        Vector((x_max, p0.y, p0.z)) + offset + inner,
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    return create_mesh_object(name, [tuple(pt) for pt in v], faces, mat, collection)


def create_rib(
    name: str,
    x_center: float,
    thickness: float,
    profile: list[Vector],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    half = thickness / 2.0
    left = [(x_center - half, p.y, p.z) for p in profile]
    right = [(x_center + half, p.y, p.z) for p in profile]
    n = len(profile)
    faces: list[tuple[int, ...]] = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        faces.append((i, (i + 1) % n, n + (i + 1) % n, n + i))
    return create_mesh_object(name, left + right, faces, mat, collection)


def create_backer(
    name: str,
    x_min: float,
    x_max: float,
    joint: Vector,
    tangent: Vector,
    outward: Vector,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    tangent_yz = Vector((0.0, tangent.y, tangent.z))
    if tangent_yz.length < 1e-6:
        tangent_yz = Vector((0, 1, 0))
    tangent_yz.normalize()
    inward = -Vector((0.0, outward.y, outward.z))
    if inward.length < 1e-6:
        inward = Vector((0, 0, -1))
    inward.normalize()

    center = Vector((0.0, joint.y, joint.z)) + inward * (WOOD_THICKNESS_CM + BACKER_DEPTH_CM * 0.5)
    a = tangent_yz * (BACKER_WIDTH_CM / 2.0)
    b = inward * (BACKER_DEPTH_CM / 2.0)
    yz = [center - a - b, center + a - b, center + a + b, center - a + b]

    verts = []
    for x in (x_min, x_max):
        verts.extend((x, p.y, p.z) for p in yz)
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    return create_mesh_object(name, verts, faces, mat, collection)


def create_polyline(
    name: str,
    points: list[Vector],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    x: float,
) -> bpy.types.Object:
    verts = [(x, p.y, p.z) for p in points]
    edges = [(i, i + 1) for i in range(len(points) - 1)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    obj.show_in_front = True
    link_obj(collection, obj)
    return obj


def add_label(
    name: str,
    body: str,
    location: tuple[float, float, float],
    size: float,
    collection: bpy.types.Collection,
    mat: bpy.types.Material | None = None,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = (math.radians(65), 0, 0)
    if mat:
        obj.data.materials.append(mat)
    link_obj(collection, obj)
    return obj


def create_rib_positions(x_min: float, x_max: float) -> list[float]:
    length = x_max - x_min
    count = max(2, int(math.ceil(length / RIB_SPACING_CM)) + 1)
    if count == 2:
        return [x_min, x_max]
    return [x_min + length * i / (count - 1) for i in range(count)]


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = [
        "piece",
        "type",
        "qty",
        "length_cm",
        "width_cm",
        "thickness_cm",
        "start_y_cm",
        "start_z_cm",
        "end_y_cm",
        "end_z_cm",
        "install_angle_deg",
        "note",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_svg(profile: list[Vector], curve: list[Vector], rows: list[dict[str, object]]) -> None:
    all_points = profile + curve
    min_y = min(p.y for p in all_points)
    max_y = max(p.y for p in all_points)
    min_z = min(p.z for p in all_points)
    max_z = max(p.z for p in all_points)
    width, height = 1400, 950
    margin = 85
    scale = min((width - 2 * margin) / (max_y - min_y), 520 / (max_z - min_z))

    def pt(p: Vector) -> tuple[float, float]:
        x = margin + (p.y - min_y) * scale
        y = margin + (max_z - p.z) * scale
        return x, y

    profile_path = " ".join(
        ("M" if i == 0 else "L") + f"{pt(p)[0]:.2f},{pt(p)[1]:.2f}"
        for i, p in enumerate(profile)
    ) + " Z"
    curve_path = " ".join(
        ("M" if i == 0 else "L") + f"{pt(p)[0]:.2f},{pt(p)[1]:.2f}"
        for i, p in enumerate(curve)
    )

    panel_lines = []
    for i in range(len(curve) - 1):
        x0, y0 = pt(curve[i])
        x1, y1 = pt(curve[i + 1])
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        panel_lines.append(
            f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
            f'stroke="#b45309" stroke-width="8" stroke-linecap="round"/>'
            f'<text x="{mx + 12:.2f}" y="{my:.2f}" class="tiny">P{i + 1:02d}</text>'
        )

    table_rows = []
    y = 690
    for row in rows[:20]:
        table_rows.append(
            f'<text x="90" y="{y}" class="tiny">{row["piece"]}: '
            f'{float(row["length_cm"]):.1f} x {float(row["width_cm"]):.2f} cm, '
            f'角度 {float(row["install_angle_deg"]):.1f}°</text>'
        )
        y += 24

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .title {{ font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 34px; font-weight: 800; fill: #0f172a; }}
    .label {{ font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 18px; fill: #334155; }}
    .tiny {{ font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", sans-serif; font-size: 15px; fill: #0f172a; }}
  </style>
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="70" y="58" class="title">分段木板曲面剖面尺寸圖</text>
  <text x="70" y="92" class="label">灰色為第一版.blend原始端面；棕色 P01... 為依原始曲面邊線分段的木板。</text>
  <path d="{profile_path}" fill="#e2e8f0" stroke="#475569" stroke-width="2"/>
  <path d="{curve_path}" fill="none" stroke="#dc2626" stroke-width="2" stroke-dasharray="8 7"/>
  {''.join(panel_lines)}
  <text x="90" y="650" class="label">板件裁切尺寸，單位 cm，板厚 {WOOD_THICKNESS_CM:.1f}cm</text>
  {''.join(table_rows)}
</svg>'''
    OUTPUT_SVG.write_text(svg, encoding="utf-8")


def setup_scene_camera(x_min: float, x_max: float, y_min: float, y_max: float, z_max: float) -> None:
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "CENTIMETERS"

    cam = bpy.data.objects.get("Camera")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.object
    bpy.context.scene.camera = cam
    center = Vector(((x_min + x_max) / 2, (y_min + y_max) / 2, z_max / 2))
    direction = Vector((1.3, -1.2, 0.9)).normalized()
    cam.location = center + direction * 260
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 185
    cam.data.clip_end = 5000

    if not bpy.data.objects.get("Structure_Area_Light"):
        bpy.ops.object.light_add(type="AREA", location=(center.x - 40, center.y - 80, z_max + 120))
        light = bpy.context.object
        light.name = "Structure_Area_Light"
        light.data.energy = 550
        light.data.size = 80


def main() -> None:
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != SOURCE_BLEND.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))

    collection = ensure_collection()

    mat_original = material("原始外殼參考_透明藍", (0.2, 0.45, 0.95, 0.18))
    mat_panel = material("9mm木板_曲面分段", (0.78, 0.50, 0.23, 1.0))
    mat_panel_alt = material("9mm木板_曲面分段_交錯", (0.92, 0.68, 0.37, 1.0))
    mat_rib = material("12mm肋板", (0.42, 0.24, 0.10, 1.0))
    mat_backer = material("內側背襯條", (0.55, 0.32, 0.12, 1.0))
    mat_curve = material("原始曲線紅色", (0.9, 0.08, 0.08, 1.0))
    mat_text = material("尺寸標註黑", (0.02, 0.03, 0.04, 1.0))

    target = largest_mesh_object()
    target.name = "原始外殼參考"
    target.data.materials.clear()
    target.data.materials.append(mat_original)
    target.show_transparent = True
    target.display_type = "TEXTURED"

    profile, x_min, x_max, y_min, y_max = get_end_profile(target)
    curve = extract_main_curve(profile)
    z_min = min(p.z for p in profile)
    z_max = max(p.z for p in profile)

    create_polyline("CurveRef_原始曲面邊線", curve, mat_curve, collection, x_max + 1.8)
    create_polyline("OriginalProfile_端面輪廓", profile + [profile[0]], mat_text, collection, x_max + 1.4)

    length_cm = x_max - x_min
    rows: list[dict[str, object]] = []

    for i in range(len(curve) - 1):
        p0 = curve[i]
        p1 = curve[i + 1]
        normal = outward_normal_yz(profile, p0, p1)
        mat = mat_panel if i % 2 == 0 else mat_panel_alt
        obj = create_curve_board(
            f"WoodPanel_P{i + 1:02d}",
            x_min,
            x_max,
            p0,
            p1,
            normal,
            WOOD_THICKNESS_CM,
            mat,
            collection,
        )
        chord = math.hypot(p1.y - p0.y, p1.z - p0.z)
        angle = math.degrees(math.atan2(p1.z - p0.z, p1.y - p0.y))
        mid = Vector(((x_min + x_max) / 2, (p0.y + p1.y) / 2, (p0.z + p1.z) / 2)) + normal * 4.0
        add_label(
            f"DimLabel_P{i + 1:02d}",
            f"P{i + 1:02d}\\n{length_cm:.1f} x {chord:.2f}cm",
            (mid.x, mid.y, mid.z),
            2.4,
            collection,
            mat_text,
        )
        rows.append({
            "piece": f"P{i + 1:02d}",
            "type": "曲面外板",
            "qty": 1,
            "length_cm": round(length_cm, 3),
            "width_cm": round(chord, 3),
            "thickness_cm": WOOD_THICKNESS_CM,
            "start_y_cm": round(p0.y, 3),
            "start_z_cm": round(p0.z, 3),
            "end_y_cm": round(p1.y, 3),
            "end_z_cm": round(p1.z, 3),
            "install_angle_deg": round(angle, 3),
            "note": "外板端點取自第一版.blend原始曲面邊線；以直板弦段施工。",
        })

    for i in range(1, len(curve) - 1):
        prev_pt = curve[i - 1]
        joint = curve[i]
        next_pt = curve[i + 1]
        tangent = next_pt - prev_pt
        normal_a = outward_normal_yz(profile, prev_pt, joint)
        normal_b = outward_normal_yz(profile, joint, next_pt)
        outward = normal_a + normal_b
        if outward.length < 1e-6:
            outward = normal_a
        outward.normalize()
        create_backer(
            f"Backer_J{i:02d}",
            x_min,
            x_max,
            joint,
            tangent,
            outward,
            mat_backer,
            collection,
        )

    rib_positions = create_rib_positions(x_min, x_max)
    for i, x in enumerate(rib_positions):
        rib = create_rib(f"Rib_{i + 1:02d}", x, RIB_THICKNESS_CM, profile, mat_rib, collection)
        rib.show_in_front = i in (0, len(rib_positions) - 1)

    add_label(
        "DimLabel_Title",
        (
            "木板分段曲面結構\\n"
            f"來源：第一版.blend；模型單位以 cm 讀取\\n"
            f"曲面外板 {len(curve) - 1} 片，肋板 {len(rib_positions)} 片，長度 {length_cm:.1f}cm"
        ),
        ((x_min + x_max) / 2, y_min - 18, z_max + 12),
        4.0,
        collection,
        mat_text,
    )

    rows.append({
        "piece": "RIB",
        "type": "側面肋板",
        "qty": len(rib_positions),
        "length_cm": "",
        "width_cm": "",
        "thickness_cm": RIB_THICKNESS_CM,
        "start_y_cm": round(y_min, 3),
        "start_z_cm": round(z_min, 3),
        "end_y_cm": round(y_max, 3),
        "end_z_cm": round(z_max, 3),
        "install_angle_deg": "",
        "note": f"肋板沿X方向位置：{', '.join(f'{x:.1f}' for x in rib_positions)} cm；外輪廓取自第一版.blend端面。",
    })
    rows.append({
        "piece": "BACKER",
        "type": "內側背襯條",
        "qty": max(0, len(curve) - 2),
        "length_cm": round(length_cm, 3),
        "width_cm": BACKER_WIDTH_CM,
        "thickness_cm": BACKER_DEPTH_CM,
        "start_y_cm": "",
        "start_z_cm": "",
        "end_y_cm": "",
        "end_z_cm": "",
        "install_angle_deg": "",
        "note": "每個曲面板接縫內側一條，建議搭配PU膠和白鐵螺絲。",
    })

    write_csv(rows)
    write_svg(profile, curve, rows)
    setup_scene_camera(x_min, x_max, y_min, y_max, z_max)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    print("DONE")
    print(f"輸出 Blender 檔：{OUTPUT_BLEND}")
    print(f"輸出尺寸表：{OUTPUT_CSV}")
    print(f"輸出剖面圖：{OUTPUT_SVG}")


if __name__ == "__main__":
    main()
