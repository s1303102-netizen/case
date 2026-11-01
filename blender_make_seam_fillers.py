from pathlib import Path
import csv
import math

import bpy


ROOT = Path("/Users/alissachang/大專")
OUT_BLEND = ROOT / "傘面板件接縫填充_五款.blend"
OUT_PREVIEW = ROOT / "傘面板件接縫填充_五款預覽.png"
OUT_CSV = ROOT / "傘面板件接縫填充_五款尺寸.csv"
OUT_STL_DIR = ROOT / "接縫填充_STL"

WOOD_THICKNESS_MM = 9.0

# Angles come from the adjacent panel-plane normals in the final canopy OBJ.
FILLERS = [
    {
        "code": "F01",
        "name": "中心三角板放射縫",
        "angle_deg": 6.465188,
        "length_mm": 300.0,
        "source_length_mm": 315.922728,
        "qty": 12,
        "color": (0.91, 0.31, 0.22, 1.0),
    },
    {
        "code": "F02",
        "name": "內圈梯形放射縫",
        "angle_deg": 15.831256,
        "length_mm": 180.634475,
        "source_length_mm": 180.634475,
        "qty": 12,
        "color": (0.95, 0.62, 0.16, 1.0),
    },
    {
        "code": "F03",
        "name": "外圈梯形放射縫",
        "angle_deg": 22.119904,
        "length_mm": 225.752158,
        "source_length_mm": 225.752158,
        "qty": 12,
        "color": (0.22, 0.61, 0.48, 1.0),
    },
    {
        "code": "F04",
        "name": "三角板與內圈交界",
        "angle_deg": 19.562605,
        "length_mm": 159.859480,
        "source_length_mm": 159.859480,
        "qty": 12,
        "color": (0.19, 0.47, 0.75, 1.0),
    },
    {
        "code": "F05",
        "name": "內圈與外圈交界",
        "angle_deg": 15.686829,
        "length_mm": 239.789220,
        "source_length_mm": 239.789220,
        "qty": 12,
        "color": (0.48, 0.35, 0.70, 1.0),
    },
]


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.38
    return material


def make_triangular_prism(spec, collection):
    angle = math.radians(spec["angle_deg"])
    length = spec["length_mm"]

    # One 9 mm leg lies on Z=0 for a stable, support-free print orientation.
    section = [
        (0.0, 0.0),
        (WOOD_THICKNESS_MM, 0.0),
        (WOOD_THICKNESS_MM * math.cos(angle), WOOD_THICKNESS_MM * math.sin(angle)),
    ]
    center_y = (min(p[0] for p in section) + max(p[0] for p in section)) / 2
    section = [(y - center_y, z) for y, z in section]

    vertices = []
    for x in (-length / 2, length / 2):
        vertices.extend((x, y, z) for y, z in section)

    faces = [
        (0, 2, 1),
        (3, 4, 5),
        (0, 1, 4, 3),
        (1, 2, 5, 4),
        (2, 0, 3, 5),
    ]
    mesh = bpy.data.meshes.new(f"{spec['code']}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(f"{spec['code']}_{spec['name']}", mesh)
    collection.objects.link(obj)

    material = make_material(f"{spec['code']}_Material", spec["color"])
    obj.data.materials.append(material)
    obj["接縫位置"] = spec["name"]
    obj["縫隙尖角_deg"] = spec["angle_deg"]
    obj["板面內夾角_deg"] = 180.0 - spec["angle_deg"]
    obj["木板厚度_mm"] = WOOD_THICKNESS_MM
    obj["模型長度_mm"] = spec["length_mm"]
    obj["原始接縫長度_mm"] = spec["source_length_mm"]
    obj["需求數量"] = spec["qty"]
    obj["三角截面底邊_mm"] = 2 * WOOD_THICKNESS_MM * math.sin(angle / 2)
    return obj


def add_text(body, location, size, collection, align="LEFT"):
    curve = bpy.data.curves.new(f"Label_{body[:8]}", type="FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = 0.0
    obj = bpy.data.objects.new(f"Label_{body[:8]}", curve)
    obj.location = location
    collection.objects.link(obj)
    material = make_material(f"Text_{len(bpy.data.materials):02d}", (0.035, 0.045, 0.06, 1.0))
    obj.data.materials.append(material)
    return obj


def export_stl(obj, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    saved_location = obj.location.copy()
    obj.location = (0.0, 0.0, 0.0)

    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(
            filepath=str(filepath),
            export_selected_objects=True,
            apply_modifiers=True,
            global_scale=1.0,
        )
    else:
        bpy.ops.export_mesh.stl(
            filepath=str(filepath),
            use_selection=True,
            global_scale=1.0,
            use_scene_unit=False,
        )

    obj.location = saved_location
    obj.select_set(False)


def write_dimensions_csv():
    fields = [
        "code",
        "name",
        "qty",
        "gap_angle_deg",
        "panel_included_angle_deg",
        "wood_thickness_mm",
        "length_mm",
        "source_length_mm",
        "triangle_base_mm",
        "triangle_height_mm",
        "note",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for spec in FILLERS:
            angle = math.radians(spec["angle_deg"])
            writer.writerow({
                "code": spec["code"],
                "name": spec["name"],
                "qty": spec["qty"],
                "gap_angle_deg": f"{spec['angle_deg']:.6f}",
                "panel_included_angle_deg": f"{180.0 - spec['angle_deg']:.6f}",
                "wood_thickness_mm": f"{WOOD_THICKNESS_MM:.2f}",
                "length_mm": f"{spec['length_mm']:.3f}",
                "source_length_mm": f"{spec['source_length_mm']:.3f}",
                "triangle_base_mm": f"{2 * WOOD_THICKNESS_MM * math.sin(angle / 2):.3f}",
                "triangle_height_mm": f"{WOOD_THICKNESS_MM * math.sin(angle):.3f}",
                "note": "F01依3D列印尺寸限制縮短為300mm" if spec["code"] == "F01" else "依實際接縫長度",
            })


def setup_preview(objects, labels_collection):
    row_gap = 28.0
    y_start = row_gap * 2
    for index, (spec, obj) in enumerate(zip(FILLERS, objects)):
        y = y_start - index * row_gap
        obj.location.y = y
        add_text(
            (
                f"{spec['code']}  {spec['name']}  {spec['angle_deg']:.2f} deg  "
                f"L={spec['length_mm']:.1f} mm  數量 {spec['qty']} 件"
            ),
            (0.0, y + 9.0, 0.2),
            5.0,
            labels_collection,
            align="CENTER",
        )

    add_text(
        "9 mm panel seam fillers - five exact profiles",
        (0.0, 88.0, 0.2),
        8.0,
        labels_collection,
        align="CENTER",
    )

    bpy.ops.object.camera_add(location=(0.0, 0.0, 420.0))
    camera = bpy.context.object
    camera.name = "Preview_Camera"
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 360.0
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.0, 250.0))
    light = bpy.context.object
    light.name = "Preview_Area_Light"
    light.data.energy = 900.0
    light.data.shape = "RECTANGLE"
    light.data.size = 360.0
    light.data.size_y = 180.0

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT_PREVIEW)
    scene.render.film_transparent = False
    scene.world.color = (0.93, 0.95, 0.97)


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001

    model_collection = bpy.data.collections.new("9mm接縫填充模型")
    label_collection = bpy.data.collections.new("尺寸標示")
    scene.collection.children.link(model_collection)
    scene.collection.children.link(label_collection)

    objects = [make_triangular_prism(spec, model_collection) for spec in FILLERS]
    setup_preview(objects, label_collection)
    write_dimensions_csv()

    OUT_STL_DIR.mkdir(exist_ok=True)
    for spec, obj in zip(FILLERS, objects):
        filename = f"{spec['code']}_{spec['name']}_{spec['angle_deg']:.2f}deg_{spec['length_mm']:.1f}mm.stl"
        export_stl(obj, OUT_STL_DIR / filename)

    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), compress=True)
    scene.render.filepath = str(OUT_PREVIEW)
    bpy.ops.render.render(write_still=True)

    print(f"Saved: {OUT_BLEND}")
    print(f"Preview: {OUT_PREVIEW}")
    print(f"STL directory: {OUT_STL_DIR}")
    print(f"Dimensions: {OUT_CSV}")


if __name__ == "__main__":
    main()
