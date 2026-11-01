import json
import math
import os

import bpy
from mathutils import Vector


OUT = "/Users/alissachang/大專/curve_profile_extract.json"
EPS = 1e-4

bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("No mesh objects found")

obj = meshes[0]
verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
xs = sorted({round(v.x, 6) for v in verts})
ys = sorted({round(v.y, 6) for v in verts})
zs = sorted({round(v.z, 6) for v in verts})

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)
min_z, max_z = min(zs), max(zs)

# For an extruded shell the side profile is visible at the two length ends.
end_profiles = {}
for label, target_x in [("x_min", min_x), ("x_max", max_x)]:
    pts = sorted(
        {(round(v.y, 6), round(v.z, 6)) for v in verts if abs(v.x - target_x) < EPS},
        key=lambda p: (p[1], p[0]),
    )
    end_profiles[label] = pts

# Also summarize the outer envelope in yz space over the full model.
yz_pairs = sorted({(round(v.y, 6), round(v.z, 6)) for v in verts}, key=lambda p: (p[1], p[0]))

result = {
    "object": obj.name,
    "unit_system": bpy.context.scene.unit_settings.system,
    "unit_scale": bpy.context.scene.unit_settings.scale_length,
    "dimensions": [obj.dimensions.x, obj.dimensions.y, obj.dimensions.z],
    "bbox": {
        "min": [min_x, min_y, min_z],
        "max": [max_x, max_y, max_z],
    },
    "vertex_count": len(obj.data.vertices),
    "polygon_count": len(obj.data.polygons),
    "unique_x_count": len(xs),
    "unique_y_count": len(ys),
    "unique_z_count": len(zs),
    "x_values_sample": xs[:20] + xs[-20:],
    "y_values": ys,
    "z_values_sample": zs[:30] + zs[-30:],
    "end_profiles": end_profiles,
    "yz_pairs": yz_pairs,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("WROTE", OUT)
print("OBJECT", obj.name)
print("DIMS", [round(v, 6) for v in obj.dimensions])
print("BBOX", result["bbox"])
print("END_PROFILE_COUNTS", {k: len(v) for k, v in end_profiles.items()})
