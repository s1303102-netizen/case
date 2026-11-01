from pathlib import Path
import csv
import math

import bpy
from mathutils import Vector


ROOT = Path("/Users/alissachang/大專")
OBJ = ROOT / "內部圓弧傘面木板結構.obj"
CSV = ROOT / "內部圓弧傘面板件尺寸.csv"
OUT_BLEND = ROOT / "內部圓弧傘面木板結構.blend"


def clear_scene():
    for obj in list(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def main():
    clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "CENTIMETERS"

    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(OBJ))
    else:
        bpy.ops.import_scene.obj(filepath=str(OBJ))

    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    all_corners = []
    for obj in objects:
        for corner in obj.bound_box:
            all_corners.append(obj.matrix_world @ Vector(corner))
    if all_corners:
        mn = Vector((min(p[i] for p in all_corners) for i in range(3)))
        mx = Vector((max(p[i] for p in all_corners) for i in range(3)))
        center = (mn + mx) / 2
        dims = mx - mn
    else:
        center = Vector((0, 0, 0))
        dims = Vector((140, 80, 120))

    bpy.ops.object.light_add(type="AREA", location=(center.x, center.y - 110, center.z + 130))
    light = bpy.context.object
    light.name = "Umbrella_Canopy_Area_Light"
    light.data.energy = 650
    light.data.size = 80

    bpy.ops.object.camera_add(location=(center.x + 105, center.y - 155, center.z + 95))
    cam = bpy.context.object
    cam.name = "Umbrella_Canopy_Camera"
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(dims.x, dims.z) * 1.35
    cam.data.clip_end = 5000
    bpy.context.scene.camera = cam

    bpy.ops.object.text_add(location=(center.x, center.y - 18, mx.z + 10), rotation=(math.radians(65), 0, 0))
    text = bpy.context.object
    text.name = "Title"
    with CSV.open(newline="", encoding="utf-8-sig") as f:
        panels = list(csv.DictReader(f))
    sectors = {row["sector"] for row in panels}
    rings = {row["ring"] for row in panels}
    text.data.body = f"內部圓弧傘面木板結構\n{len(sectors)}放射區 x {len(rings)}層分帶，共{len(panels)}片"
    text.data.align_x = "CENTER"
    text.data.align_y = "CENTER"
    text.data.size = 4

    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), compress=True)
    print(f"Saved {OUT_BLEND}")


if __name__ == "__main__":
    main()
