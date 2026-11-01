"""Bake and join only the blower; keep its appearance and existing objects."""
from pathlib import Path
from collections import Counter
import ast
import bpy
import hashlib
import json
import os
import shutil
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '第一版.blend'
STAGED = HERE / '第一版_鼓風機Join待驗證.blend'
BACKUP = HERE / '第一版_鼓風機Join前備份.blend'
REPORT = HERE / '鼓風機_Join檢查.json'
COLLECTION = '鼓風機_150FLJ330W'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Reuse the full original-data snapshot functions without executing installation.
module = ast.parse((HERE / 'blender_verify_and_install_blower.py').read_text())
helpers = ast.Module(body=[node for node in module.body
                          if isinstance(node, ast.FunctionDef)
                          and node.name in {'attribute_values', 'snapshot', 'units'}],
                     type_ignores=[])
exec(compile(helpers, str(HERE / 'blender_verify_and_install_blower.py'), 'exec'))


def surface(objects):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    verts = []
    material_faces = Counter()
    faces = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        verts.extend(tuple(evaluated.matrix_world @ vertex.co) for vertex in data.vertices)
        for poly in data.polygons:
            index = poly.material_index
            mat = data.materials[index] if index < len(data.materials) else None
            material_faces[mat.name if mat else '<none>'] += 1
        faces += len(data.polygons)
        evaluated.to_mesh_clear()
    verts.sort()
    low = [min(p[i] for p in verts) for i in range(3)]
    high = [max(p[i] for p in verts) for i in range(3)]
    return {'vertices': verts, 'face_count': faces,
            'material_faces': dict(material_faces), 'min': low, 'max': high}


initial_hash = digest(SOURCE)
collection = bpy.data.collections[COLLECTION]
root = bpy.data.objects['鼓風機_總成_公分場景比例']
parts = [obj for obj in collection.objects if obj.type in {'MESH', 'CURVE', 'FONT'}]
assert len(parts) == 178, 'Unexpected blower parts; inspect before joining.'
originals = {obj.name: snapshot(obj) for obj in bpy.data.objects if obj not in collection.objects[:]}
original_units = units(bpy.context.scene)
old_scene = bpy.context.scene.name
root_properties = {key: root[key] for key in root.keys()}
before = surface(parts)
if BACKUP.exists():
    assert digest(BACKUP) == initial_hash, 'Existing join backup differs; refusing to overwrite it.'
else:
    shutil.copy2(SOURCE, BACKUP)

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.scene.objects:
    obj.select_set(False)
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects['鼓風機_蝸殼_進風側板']
assert bpy.ops.object.convert.poll(), 'Cannot convert blower parts to mesh.'
bpy.ops.object.convert(target='MESH')
converted = list(bpy.context.selected_objects)
assert len(converted) == len(parts) and all(obj.type == 'MESH' for obj in converted)
assert bpy.ops.object.join.poll(), 'Cannot join converted meshes.'
bpy.ops.object.join()
joined = bpy.context.view_layer.objects.active
assert joined.type == 'MESH'
world = joined.matrix_world.copy()
joined.parent = None
joined.matrix_world = world
joined.name = '鼓風機_150FLJ330W_整體網格'
joined.data.name = '鼓風機_150FLJ330W_整體網格_Mesh'
for key, value in root_properties.items():
    joined[key] = value
joined['合併方式'] = '所有修改器、曲線與文字已轉為網格，再以 Join 合併。'
joined['原零件數'] = len(parts)
joined['合併前備份'] = str(BACKUP)
bpy.data.objects.remove(root, do_unlink=True)
bpy.context.view_layer.update()
assert len(collection.objects) == 1
assert all(snapshot(bpy.data.objects[name]) == data for name, data in originals.items())
assert units(bpy.context.scene) == original_units
after = surface([joined])
assert len(before['vertices']) == len(after['vertices']), 'Vertex count changed.'
assert before['face_count'] == after['face_count'], 'Face count changed.'
assert before['material_faces'] == after['material_faces'], 'Material assignments changed.'

# Compare both directions with a geometric tolerance, avoiding decimal-bin
# boundaries that can misclassify harmless floating-point transform rounding.
def max_surface_distance(left, right):
    tree = KDTree(len(right))
    for index, point in enumerate(right):
        tree.insert(point, index)
    tree.balance()
    return max(tree.find(point)[2] for point in left)

surface_error = max(max_surface_distance(before['vertices'], after['vertices']),
                    max_surface_distance(after['vertices'], before['vertices']))
assert surface_error < 0.0001, f'World-space surface changed: {surface_error}'
assert max(abs(before[key][i] - after[key][i]) for key in ('min', 'max') for i in range(3)) < 0.0001
joined.select_set(True)
bpy.context.view_layer.objects.active = joined
bpy.ops.wm.save_as_mainfile(filepath=str(STAGED))
bpy.ops.wm.open_mainfile(filepath=str(STAGED))
joined = bpy.data.objects['鼓風機_150FLJ330W_整體網格']
assert all(snapshot(bpy.data.objects[name]) == data for name, data in originals.items())
assert units(bpy.context.scene) == original_units
assert bpy.context.scene.name == old_scene
assert len(bpy.data.collections[COLLECTION].objects) == 1
assert joined.parent is None and len(joined.modifiers) == 0
assert bpy.context.view_layer.objects.active == joined and joined.select_get()
reopened = surface([joined])
assert reopened['vertices'] == after['vertices']
assert reopened['material_faces'] == after['material_faces']
assert digest(SOURCE) == initial_hash, 'Source file changed during join; refusing to overwrite.'
staged_hash = digest(STAGED)
os.replace(STAGED, SOURCE)
assert digest(SOURCE) == staged_hash
report = {'檔案': str(SOURCE), '備份': str(BACKUP),
          '合併前類型': {'MESH':153, 'CURVE':22, 'FONT':3, 'EMPTY':1},
          '合併後': {'物件': joined.name, '類型':joined.type,
                    '頂點數':len(joined.data.vertices), '面數':len(joined.data.polygons),
                    '材質數':len(joined.data.materials),
                    '位置':list(joined.location), '縮放':list(joined.scale)},
          '檢查': {'原物件與場景單位保持原樣':True, '表面頂點位置保持原樣':True,
                   '面數與材質分配保持原樣':True, '儲存重新開啟驗證':True},
          '合併表面浮點誤差_mm':surface_error*10,
          '表面包絡場景座標': {'min':reopened['min'], 'max':reopened['max']},
          '檔案_sha256':staged_hash}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLOWER_JOIN_COMPLETE',json.dumps(report,ensure_ascii=False))
