"""Generate an editable Blender concept model for an umbrella shaft clamp/drive.

Coordinate system and units:
    X = horizontal in the supplied front view
    Y = wheel axle / mechanism depth
    Z = vertical in the supplied front view
    Blender units are millimetres.

The source drawing does not specify overall dimensions.  The purchased caster
envelope (27 x 11.4 x 13 mm) is therefore used as the scale reference.  The
nominal umbrella shaft is intentionally represented only by a hidden Empty.
"""

from __future__ import annotations

import math
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path("/Users/alissachang/大專/夾傘機構")
OUTPUT_BLEND = ROOT / "夾傘旋轉機構_3D.blend"
FRONT_RENDER = ROOT / "夾傘旋轉機構_正視預覽.png"
ISO_RENDER = ROOT / "夾傘旋轉機構_立體預覽.png"
CASTER_RENDER = ROOT / "定向滾輪_尺寸修正版_近照.png"
VALIDATION_REPORT = ROOT / "定向滾輪_尺寸檢查.json"

# Design parameters in millimetres.
SHAFT_DIAMETER = 10.0
SHAFT_CENTER = Vector((0.0, 0.0, 24.5))
CASTER_WHEEL_RADIUS = 6.0
CASTER_WHEEL_WIDTH = 9.0
CASTER_PLATE_LENGTH = 27.0
CASTER_PLATE_WIDTH = 11.4
CASTER_PLATE_THICKNESS = 0.8  # Estimated sheet gauge: not specified by the product.
CASTER_INSTALL_HEIGHT = 13.0
CASTER_CHEEK_THICKNESS = 0.8
CASTER_HOLE_DIAMETER = 4.0
CASTER_HOLE_SPACING = 18.0
DRIVE_RADIUS = 38.0
DRIVE_WIDTH = 18.0
DRIVE_CENTER_Z = SHAFT_CENTER.z - SHAFT_DIAMETER / 2 - DRIVE_RADIUS


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def make_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def move_to_collection(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    col.objects.link(obj)


def make_material(name: str, rgba: tuple[float, float, float, float],
                  metallic: float = 0.0, roughness: float = 0.4) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def bevelled_box(name: str, location, dimensions, material, collection,
                  bevel=1.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("邊角_R", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def cyl_y(name: str, location, radius: float, depth: float, material, collection,
          vertices=64, bevel=0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=location, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        mod = obj.modifiers.new("邊緣_R", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def cyl_x(name: str, location, radius: float, depth: float, material, collection,
          vertices=48, bevel=0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=location, rotation=(0, math.pi / 2, 0))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        mod = obj.modifiers.new("邊緣_R", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def apply_boolean(target, cutter) -> None:
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("實際穿孔", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def extrude_profile(name, profile, lower, upper, axis, material, collection):
    """Extrude a 2D outline into a solid; axis is the extrusion coordinate."""
    def xyz(p, coord):
        return (coord, p[0], p[1]) if axis == "X" else (p[0], coord, p[1])
    vertices = [xyz(p, lower) for p in profile] + [xyz(p, upper) for p in profile]
    n = len(profile)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return obj


def add_edge_bevel(obj, width):
    mod = obj.modifiers.new("沖壓邊緣圓角", "BEVEL")
    mod.width = width
    mod.segments = 3
    mod.limit_method = "ANGLE"


def add_caster(side: int, materials, parent_collection) -> bpy.types.Object:
    label = "左" if side < 0 else "右"
    col = make_collection(f"{label}側定向滾輪_27x11.4x13mm", parent_collection)
    root = bpy.data.objects.new(f"{label}側定向滾輪_總成", None)
    col.objects.link(root)
    # Keep the original contact layout. u measures from mounting surface inward.
    center_z = SHAFT_CENTER.z + math.sqrt(
        (SHAFT_DIAMETER / 2 + CASTER_WHEEL_RADIUS) ** 2 - 8.0 ** 2)
    wheel_center = Vector((side * 8.0, 0.0, center_z))
    surface_x = side * (8.0 + CASTER_INSTALL_HEIGHT - CASTER_WHEEL_RADIUS)
    def x_of(u):
        return surface_x - side * u

    # Rounded 27 x 11.4 mm mounting plate, with real bore geometry.
    outline = []
    radius = 3.0
    half_y, half_z = CASTER_PLATE_WIDTH / 2, CASTER_PLATE_LENGTH / 2
    for cy, cz, start in ((half_y-radius, half_z-radius, 0),
                          (-half_y+radius, half_z-radius, 90),
                          (-half_y+radius, -half_z+radius, 180),
                          (half_y-radius, -half_z+radius, 270)):
        for step in range(13):
            angle = math.radians(start + step * 90 / 12)
            outline.append((cy + radius * math.cos(angle),
                            center_z + cz + radius * math.sin(angle)))
    plate = extrude_profile(f"{label}_固定片_27x11.4mm_雙4mm穿孔", outline,
                            min(x_of(0), x_of(CASTER_PLATE_THICKNESS)),
                            max(x_of(0), x_of(CASTER_PLATE_THICKNESS)),
                            "X", materials["steel"], col)
    for dz in (-CASTER_HOLE_SPACING / 2, CASTER_HOLE_SPACING / 2):
        cutter = cyl_x("孔切削工具", (x_of(0.4), 0, center_z + dz),
                       CASTER_HOLE_DIAMETER / 2, 4, materials["steel"], col, 96)
        apply_boolean(plate, cutter)
    # The rectangular crown opening visible above the orange wheel in the photo.
    window = bevelled_box("輪架中央開口工具", (x_of(0.4), 0, center_z),
                          (4, 8.7, 11.0), materials["steel"], col, 0)
    apply_boolean(plate, window)
    add_edge_bevel(plate, 0.08)
    plate["dimensions_mm"] = "length 27; width 11.4; sheet thickness 0.8 (estimated)"
    plate["mounting_holes_mm"] = "diameter 4; center spacing 18; centered at +/-9"

    # Compact solid stamped fork plates; curved axle end instead of long beams.
    local_profile = [(0.65, 8.3), (1.7, 8.0)]
    for step in range(25):
        angle = math.radians(60 - step * 120 / 24)
        local_profile.append((7 + 3.1 * math.cos(angle), 3.1 * math.sin(angle)))
    local_profile += [(1.7, -8.0), (0.65, -8.3)]
    fork_profile = [(x_of(u), center_z + z) for u, z in local_profile]
    for cheek_side in (-1, 1):
        y = cheek_side * (CASTER_PLATE_WIDTH / 2 - CASTER_CHEEK_THICKNESS / 2)
        cheek = extrude_profile(f"{label}_沖壓輪架_{'前' if y < 0 else '後'}",
                                fork_profile, y - CASTER_CHEEK_THICKNESS / 2,
                                y + CASTER_CHEEK_THICKNESS / 2, "Y",
                                materials["steel"], col)
        bore = cyl_y("輪軸孔切削工具", wheel_center, 1.6, 15,
                     materials["steel"], col, 64)
        apply_boolean(cheek, bore)
        add_edge_bevel(cheek, 0.12)

    wheel = cyl_y(f"{label}_橘色尼龍輪_直徑12_寬9mm", wheel_center,
                  CASTER_WHEEL_RADIUS, CASTER_WHEEL_WIDTH,
                  materials["orange"], col, 128, 0)
    wheel_bore = cyl_y("尼龍輪軸孔切削工具", wheel_center, 1.55, 15,
                      materials["steel"], col, 64)
    apply_boolean(wheel, wheel_bore)
    add_edge_bevel(wheel, 0.28)
    wheel["diameter_mm"] = 12.0
    wheel["width_mm"] = 9.0
    axle = cyl_y(f"{label}_輪軸_直徑3mm", wheel_center, 1.5, 11.5,
                 materials["fastener"], col, 64, 0.05)
    for pin_side in (-1, 1):
        cap_y = pin_side * 5.85
        cap = cyl_y(f"{label}_輪軸鉚釘頭_{pin_side}",
                    (wheel_center.x, cap_y, center_z), 2.45, 0.3,
                    materials["fastener"], col, 64, 0)
        recess = cyl_y("鉚釘中心凹槽工具", (wheel_center.x, pin_side * 6.03, center_z),
                       1.0, 0.15, materials["steel"], col, 6)
        apply_boolean(cap, recess)
        add_edge_bevel(cap, 0.07)
    for obj in col.objects:
        if obj != root:
            obj.parent = root
    root["installation_height_mm"] = 13.0
    root["mounting_surface_x_mm"] = surface_x
    root["wheel_center_xyz_mm"] = list(wheel_center)
    root["measured_spec_mm"] = "wheel D12 x W9; plate 27 x 11.4; pitch 18; bore D4; height 13"
    root["estimated_details"] = "0.8 mm sheet; corner radius 3; axle diameter 3; fork contour from photograph"
    wheel.keyframe_insert("rotation_euler", index=1, frame=1)
    # All three external-contact wheels turn in the same direction around the
    # central shaft, with equal nominal peripheral speeds.
    wheel.rotation_euler[1] = 2 * math.pi * DRIVE_RADIUS / CASTER_WHEEL_RADIUS
    wheel.keyframe_insert("rotation_euler", index=1, frame=120)
    return root


def add_drive_wheel(materials, parent_collection) -> bpy.types.Object:
    col = make_collection("下方驅動輪_圓柱替代", parent_collection)
    center = (0, 0, DRIVE_CENTER_Z)
    wheel = cyl_y("驅動輪_基本圓柱", center, DRIVE_RADIUS, DRIVE_WIDTH,
                  materials["drive"], col, 96, 1.3)
    axle = cyl_y("驅動輪軸", center, 4.0, 34.0,
                 materials["fastener"], col, 48, 0.3)
    hub_a = cyl_y("驅動輪輪毂_前", (0, -DRIVE_WIDTH / 2 - 0.8, DRIVE_CENTER_Z),
                  9, 1.6, materials["dark"], col, 64, 0.3)
    hub_b = cyl_y("驅動輪輪毂_後", (0, DRIVE_WIDTH / 2 + 0.8, DRIVE_CENTER_Z),
                  9, 1.6, materials["dark"], col, 64, 0.3)
    root = bpy.data.objects.new("驅動輪_總成", None)
    col.objects.link(root)
    for obj in (wheel, axle, hub_a, hub_b):
        obj.parent = root
    wheel["placeholder"] = "basic cylinder; replace with final drive wheel"
    wheel.keyframe_insert("rotation_euler", index=1, frame=1)
    wheel.rotation_euler[1] = 2 * math.pi
    wheel.keyframe_insert("rotation_euler", index=1, frame=120)
    return root


def add_reference_empty(parent_collection) -> None:
    col = make_collection("參考定位_不輸出傘", parent_collection)
    empty = bpy.data.objects.new("傘柄中心_參考_直徑10mm", None)
    empty.empty_display_type = "CIRCLE"
    empty.empty_display_size = SHAFT_DIAMETER / 2
    empty.location = SHAFT_CENTER
    empty.rotation_euler = (math.pi / 2, 0, 0)
    empty.hide_render = True
    empty["note"] = "Reference only. No umbrella or shaft geometry is generated."
    col.objects.link(empty)


def look_at(obj: bpy.types.Object, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera_and_lights(materials) -> tuple[bpy.types.Object, bpy.types.Object]:
    scene_col = bpy.context.scene.collection
    cam_data = bpy.data.cameras.new("正視鏡頭_data")
    front = bpy.data.objects.new("正視鏡頭", cam_data)
    scene_col.objects.link(front)
    front.location = (0, -260, -3)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 124
    look_at(front, (0, 0, -3))

    iso_data = bpy.data.cameras.new("立體鏡頭_data")
    iso = bpy.data.objects.new("立體鏡頭", iso_data)
    scene_col.objects.link(iso)
    iso.location = (155, -210, 125)
    iso_data.type = "ORTHO"
    iso_data.ortho_scale = 125
    look_at(iso, (0, 0, 5))

    for name, loc, energy, size in (
        ("主燈", (-95, -130, 160), 65000, 90),
        ("補燈", (120, -70, 70), 42000, 70),
        ("輪廓燈", (0, 120, 120), 52000, 60),
    ):
        data = bpy.data.lights.new(name + "_data", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        scene_col.objects.link(obj)
        look_at(obj, (0, 0, 5))
    for name, position, strength in (
        ("柔光主日光", (-80, -120, 140), 3.0),
        ("柔光補日光", (100, -80, 30), 1.2),
    ):
        data = bpy.data.lights.new(name, "SUN")
        data.energy = strength
        data.angle = math.radians(25)
        light = bpy.data.objects.new(name, data)
        scene_col.objects.link(light)
        light.location = position
        look_at(light, (0, 0, 5))
    return front, iso


def setup_scene() -> dict[str, bpy.types.Material]:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001
    scene.frame_start = 1
    scene.frame_end = 120
    # Blender 5.2 exposes Eevee under the legacy enum identifier.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.world.use_nodes = True
    world_bg = scene.world.node_tree.nodes.get("Background")
    world_bg.inputs["Color"].default_value = (0.72, 0.77, 0.84, 1)
    world_bg.inputs["Strength"].default_value = 0.8
    return {
        "steel": make_material("鍍鋅鋼", (0.62, 0.66, 0.70, 1), 0.65, 0.3),
        "fastener": make_material("不鏽鋼螺絲", (0.62, 0.67, 0.72, 1), 0.9, 0.18),
        "orange": make_material("橘色尼龍", (1.0, 0.19, 0.025, 1), 0.0, 0.38),
        "drive": make_material("驅動輪橡膠", (0.075, 0.13, 0.19, 1), 0.0, 0.30),
        "dark": make_material("軸承深灰", (0.10, 0.125, 0.15, 1), 0.58, 0.25),
        "aluminum": make_material("陽極鋁合金", (0.26, 0.32, 0.39, 1), 0.7, 0.27),
    }


def world_bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        points.extend(evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box)
    lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return lower, upper


def validate_dimensions():
    report = {"units": "mm", "casters": [], "frame_removed": True,
              "estimated_dimensions": {"sheet_thickness": 0.8, "axle_diameter": 3.0},
              "source_width_note": "Use drawing width 11.4; product table rounds to 11."}
    bpy.context.view_layer.update()
    for side, label in ((-1, "左"), (1, "右")):
        col = bpy.data.collections[f"{label}側定向滾輪_27x11.4x13mm"]
        plate = bpy.data.objects[f"{label}_固定片_27x11.4mm_雙4mm穿孔"]
        wheel = bpy.data.objects[f"{label}_橘色尼龍輪_直徑12_寬9mm"]
        root = bpy.data.objects[f"{label}側定向滾輪_總成"]
        pl, pu = world_bounds([plate])
        wl, wu = world_bounds([wheel])
        al, au = world_bounds([o for o in col.objects if o.type == "MESH"])
        plate_size, wheel_size = pu - pl, wu - wl
        height = au.x - al.x
        for actual, expected in ((plate_size.y, 11.4), (plate_size.z, 27),
                                 (wheel_size.x, 12), (wheel_size.y, 9),
                                 (wheel_size.z, 12), (height, 13)):
            assert abs(actual - expected) < 0.015, (label, actual, expected)
        center = Vector(root["wheel_center_xyz_mm"])
        center_distance = (center - SHAFT_CENTER).length
        assert abs(center_distance - 11) < 0.001
        # Verify both mounting bores are genuinely open and the surrounding
        # plate still contains solid material; cosmetic disks cannot pass this.
        holes = []
        for dz in (-9, 9):
            hole = Vector((side * 17, 0, center.z + dz))
            direction = Vector((-side, 0, 0))
            open_bore = not plate.ray_cast(hole, direction, distance=5)[0]
            surrounding_solid = plate.ray_cast(hole + Vector((0, 0, 2.5)),
                                             direction, distance=5)[0]
            assert open_bore and surrounding_solid, (label, dz, "mounting hole")
            holes.append({"center_z_mm": center.z + dz, "diameter_mm": 4,
                          "through_hole_verified": open_bore})
        report["casters"].append({
            "side": label, "wheel_diameter_mm": round(wheel_size.x, 4),
            "wheel_width_mm": round(wheel_size.y, 4),
            "plate_length_mm": round(plate_size.z, 4),
            "plate_width_mm": round(plate_size.y, 4),
            "installation_height_mm": round(height, 4),
            "hole_spacing_mm": holes[1]["center_z_mm"] - holes[0]["center_z_mm"],
            "mounting_holes": holes, "nominal_shaft_contact_gap_mm": center_distance - 11,
        })
    assert not any("骨架" in obj.name or "橫樑" in obj.name or "背襯" in obj.name
                   for obj in bpy.data.objects)
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print("DIMENSION_VALIDATION_PASSED", json.dumps(report, ensure_ascii=False))


def setup_viewport():
    from mathutils import Quaternion
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.clip_end = 2000
                space.shading.type = "SOLID"
                space.shading.color_type = "MATERIAL"
                space.overlay.show_floor = False
                space.region_3d.view_distance = 145
                space.region_3d.view_location = Vector((0, 0, 2))
                space.region_3d.view_rotation = Quaternion((0.91, 0.35, 0.12, 0.19)).normalized()
    bpy.ops.object.select_all(action="DESELECT")


def main() -> None:
    reset_scene()
    materials = setup_scene()
    mechanism = make_collection("夾傘旋轉機構")
    add_caster(-1, materials, mechanism)
    add_caster(1, materials, mechanism)
    add_drive_wheel(materials, mechanism)
    add_reference_empty(mechanism)
    front, iso = add_camera_and_lights(materials)

    scene = bpy.context.scene
    scene.frame_set(1)
    scene["design_note"] = (
        "Concept model scaled from the 27 x 11.4 x 13 mm reference caster. "
        "Nominal shaft diameter 10 mm; umbrella geometry intentionally omitted."
    )
    scene["contact_layout_mm"] = (
        f"shaft center=(0,0,{SHAFT_CENTER.z}); drive radius={DRIVE_RADIUS}; "
        f"caster radius={CASTER_WHEEL_RADIUS}"
    )
    scene.camera = front
    scene.render.filepath = str(FRONT_RENDER)
    bpy.ops.render.render(write_still=True)
    scene.camera = iso
    scene.render.filepath = str(ISO_RENDER)
    bpy.ops.render.render(write_still=True)
    # A separate close-up shows the real mounting holes and the stamped fork.
    left_col = bpy.data.collections["左側定向滾輪_27x11.4x13mm"]
    hidden = [obj for obj in scene.objects
              if obj.type == "MESH" and obj not in list(left_col.objects)]
    for obj in hidden:
        obj.hide_render = True
    close_data = bpy.data.cameras.new("定向滾輪特寫_data")
    close = bpy.data.objects.new("定向滾輪特寫", close_data)
    scene.collection.objects.link(close)
    target = Vector((-10, 0, 32.05))
    close.location = target + Vector((-42, -62, 38))
    close_data.type = "ORTHO"
    close_data.ortho_scale = 36
    look_at(close, target)
    scene.camera = close
    scene.render.filepath = str(CASTER_RENDER)
    bpy.ops.render.render(write_still=True)
    for obj in hidden:
        obj.hide_render = False
    scene.camera = iso
    setup_viewport()
    validate_dimensions()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    print(f"SAVED_BLEND={OUTPUT_BLEND}")
    print(f"FRONT_RENDER={FRONT_RENDER}")
    print(f"ISO_RENDER={ISO_RENDER}")


if __name__ == "__main__":
    main()
