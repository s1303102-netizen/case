"""
Run inside Blender. Builds a segmented plywood panel model for the internal
umbrella trough surface in 第一版.blend.

This version targets the concave internal bowl/trough surface, not the exterior
side-profile curve. Numeric units are treated as centimeters.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path("/Users/alissachang/大專")
SOURCE_BLEND = ROOT / "第一版.blend"
OUTPUT_BLEND = ROOT / "umbrella_trough_wood_structure.blend"
OUTPUT_CSV = ROOT / "內部圓弧木板板件尺寸.csv"
OUTPUT_STATUS = ROOT / "內部圓弧木板建模完成.txt"

COLLECTION_NAME = "內部容傘圓弧木板結構"
WOOD_THICKNESS_CM = 0.9
SEAM_OFFSET_CM = 0.035


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = color[3]
        bsdf.inputs["Roughness"].default_value = 0.72
    mat.blend_method = "BLEND"
    return mat


def clear_collection() -> bpy.types.Collection:
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    return collection


def link_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    collection.objects.link(obj)
    for col in list(obj.users_collection):
        if col != collection:
            col.objects.unlink(obj)


def largest_mesh_object() -> bpy.types.Object:
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("找不到 mesh 物件。")
    return max(meshes, key=lambda obj: obj.dimensions.x * obj.dimensions.y * obj.dimensions.z)


def world_poly_points(obj: bpy.types.Object, poly: bpy.types.MeshPolygon) -> list[Vector]:
    return [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]


def poly_normal(points: list[Vector]) -> Vector:
    if len(points) < 3:
        return Vector((0, 1, 0))
    normal = (points[1] - points[0]).cross(points[2] - points[0])
    if normal.length < 1e-8:
        return Vector((0, 1, 0))
    normal.normalize()
    return normal


def is_trough_face(points: list[Vector], normal: Vector) -> bool:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    xspan = max(xs) - min(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)

    # The internal umbrella trough is a compound curved bowl centered in X,
    # facing toward +Y. The exterior side curve has much longer strip faces,
    # so xspan filters it out.
    return (
        normal.y > 0.20
        and xspan <= 8.5
        and -18.0 < cy < 18.0
        and 8.0 < cz < 122.0
    )


def create_panel(
    name: str,
    points: list[Vector],
    normal: Vector,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    front = [p + normal * SEAM_OFFSET_CM for p in points]
    back = [p + normal * SEAM_OFFSET_CM - normal * WOOD_THICKNESS_CM for p in points]
    verts = [tuple(p) for p in front + back]
    n = len(points)
    faces: list[tuple[int, ...]] = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        faces.append((i, (i + 1) % n, n + (i + 1) % n, n + i))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    link_to_collection(obj, collection)
    return obj


def create_edge_lines(
    name: str,
    panel_faces: list[list[Vector]],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    verts: list[tuple[float, float, float]] = []
    edges: list[tuple[int, int]] = []
    edge_seen: set[tuple[tuple[float, float, float], tuple[float, float, float]]] = set()

    def key(point: Vector) -> tuple[float, float, float]:
        return (round(point.x, 3), round(point.y, 3), round(point.z, 3))

    for points in panel_faces:
        for p0, p1 in zip(points, points[1:] + points[:1]):
            a, b = key(p0), key(p1)
            edge_key = tuple(sorted((a, b)))
            if edge_key in edge_seen:
                continue
            edge_seen.add(edge_key)
            i = len(verts)
            verts.extend([tuple(p0), tuple(p1)])
            edges.append((i, i + 1))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    obj.show_in_front = True
    link_to_collection(obj, collection)
    return obj


def polygon_area(points: list[Vector]) -> float:
    if len(points) < 3:
        return 0.0
    origin = points[0]
    area = 0.0
    for i in range(1, len(points) - 1):
        area += (points[i] - origin).cross(points[i + 1] - origin).length / 2.0
    return area


def edge_lengths(points: list[Vector]) -> list[float]:
    return [(points[(i + 1) % len(points)] - points[i]).length for i in range(len(points))]


def add_label(
    name: str,
    text: str,
    location: Vector,
    size: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
) -> None:
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = (math.radians(65), 0, 0)
    obj.data.materials.append(mat)
    link_to_collection(obj, collection)


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = [
        "piece",
        "source_face",
        "vertex_count",
        "area_cm2",
        "edge_lengths_cm",
        "centroid_x_cm",
        "centroid_y_cm",
        "centroid_z_cm",
        "normal_x",
        "normal_y",
        "normal_z",
        "corner_xyz_cm",
        "note",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def setup_view(target_points: list[Vector]) -> None:
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "CENTIMETERS"
    xs = [p.x for p in target_points]
    ys = [p.y for p in target_points]
    zs = [p.z for p in target_points]
    center = Vector((
        (min(xs) + max(xs)) / 2,
        (min(ys) + max(ys)) / 2,
        (min(zs) + max(zs)) / 2,
    ))

    cam = bpy.data.objects.get("Camera")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.object
    bpy.context.scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 155
    cam.data.clip_end = 5000
    cam.location = center + Vector((120, -150, 95))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

    if not bpy.data.objects.get("Trough_Structure_Light"):
        bpy.ops.object.light_add(type="AREA", location=(center.x, center.y - 90, center.z + 130))
        light = bpy.context.object
        light.name = "Trough_Structure_Light"
        light.data.energy = 650
        light.data.size = 90


def main() -> None:
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != SOURCE_BLEND.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))

    collection = clear_collection()
    mat_original = material("原始外殼_透明參考", (0.18, 0.45, 0.95, 0.16))
    mat_panel_a = material("9mm木板_內部圓弧A", (0.78, 0.50, 0.24, 1.0))
    mat_panel_b = material("9mm木板_內部圓弧B", (0.92, 0.68, 0.38, 1.0))
    mat_seam = material("木板接縫線_深色", (0.12, 0.08, 0.04, 1.0))
    mat_text = material("尺寸標註_黑", (0.02, 0.03, 0.04, 1.0))

    target = largest_mesh_object()
    target.name = "原始外殼_透明參考"
    target.data.materials.clear()
    target.data.materials.append(mat_original)
    target.show_transparent = True
    target.display_type = "TEXTURED"

    bpy.context.view_layer.update()
    selected: list[tuple[int, list[Vector], Vector]] = []
    for poly in target.data.polygons:
        points = world_poly_points(target, poly)
        normal = poly_normal(points)
        if is_trough_face(points, normal):
            selected.append((poly.index, points, normal))

    if not selected:
        raise RuntimeError("沒有抓到內部容傘圓弧面，請檢查模型或調整選面條件。")

    rows: list[dict[str, object]] = []
    all_points: list[Vector] = []
    panel_faces: list[list[Vector]] = []
    for piece_index, (face_index, points, normal) in enumerate(selected, start=1):
        mat = mat_panel_a if piece_index % 2 else mat_panel_b
        create_panel(f"TroughPanel_{piece_index:03d}_F{face_index}", points, normal, mat, collection)
        panel_faces.append(points)
        all_points.extend(points)

        centroid = sum(points, Vector()) / len(points)
        lengths = edge_lengths(points)
        rows.append({
            "piece": f"T{piece_index:03d}",
            "source_face": face_index,
            "vertex_count": len(points),
            "area_cm2": round(polygon_area(points), 3),
            "edge_lengths_cm": ";".join(f"{length:.2f}" for length in lengths),
            "centroid_x_cm": round(centroid.x, 3),
            "centroid_y_cm": round(centroid.y, 3),
            "centroid_z_cm": round(centroid.z, 3),
            "normal_x": round(normal.x, 5),
            "normal_y": round(normal.y, 5),
            "normal_z": round(normal.z, 5),
            "corner_xyz_cm": " | ".join(f"({p.x:.2f},{p.y:.2f},{p.z:.2f})" for p in points),
            "note": "內部容傘圓弧面分片；此板件依第一版.blend原始面片建立。",
        })

    create_edge_lines("TroughPanel_Seams", panel_faces, mat_seam, collection)

    xs = [p.x for p in all_points]
    ys = [p.y for p in all_points]
    zs = [p.z for p in all_points]
    add_label(
        "Trough_Title",
        (
            "內部容傘圓弧木板分片結構\\n"
            f"來源：第一版.blend 原始內部凹槽面\\n"
            f"木板片數：{len(selected)}，板厚：{WOOD_THICKNESS_CM:.1f}cm"
        ),
        Vector(((min(xs) + max(xs)) / 2, min(ys) - 12, max(zs) + 10)),
        4.0,
        mat_text,
        collection,
    )

    setup_view(all_points)
    write_csv(rows)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), compress=True)
    OUTPUT_STATUS.write_text(
        f"完成：{OUTPUT_BLEND}\\n尺寸表：{OUTPUT_CSV}\\n木板片數：{len(selected)}\\n",
        encoding="utf-8",
    )
    print("DONE umbrella trough wood structure")
    print(OUTPUT_BLEND)
    print(OUTPUT_CSV)


if __name__ == "__main__":
    main()
