import bpy
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path('/Users/alissachang/Desktop/大專')
WORK = Path('/private/tmp/clamp-hide-axes.UN0OSA')
SOURCE = ROOT / '完整模型.blend'
OUTPUT = WORK / '完整模型_隱藏總成輔助軸.blend'
BACKUP = WORK / '完整模型_隱藏輔助軸前備份.blend'
NAMES = ['夾傘機構_總成_中心距60mm', '夾傘_後組_總成', '夾傘_前組_總成']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def mesh_state():
    state = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        payload = {
            'vertices': [tuple(v.co) for v in mesh.vertices],
            'edges': [tuple(e.vertices) for e in mesh.edges],
            'faces': [(tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons],
            'materials': [m.name if m else None for m in mesh.materials],
            'parent': obj.parent.name if obj.parent else None,
            'matrix': [list(row) for row in obj.matrix_world],
            'visible': {layer.name: obj.visible_get(view_layer=layer) for layer in bpy.context.scene.view_layers},
        }
        state[obj.name] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return state

source_sha = sha(SOURCE)
shutil.copy2(SOURCE, BACKUP)
assert sha(BACKUP) == source_sha
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
frame = bpy.context.scene.frame_current
bpy.context.view_layer.update()
before = mesh_state()
for name in NAMES:
    obj = bpy.data.objects[name]
    assert obj.type == 'EMPTY'
    for layer in bpy.context.scene.view_layers:
        obj.hide_set(True, view_layer=layer)
for layer in bpy.context.scene.view_layers:
    for obj in layer.objects:
        obj.select_set(False, view_layer=layer)
    layer.objects.active = None
bpy.context.view_layer.update()
assert mesh_state() == before, 'Hiding controls changed mesh geometry, pose, parenting, or visibility'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
bpy.context.view_layer.update()
assert bpy.context.scene.frame_current == frame
assert mesh_state() == before, 'Saved file mesh state changed'
for name in NAMES:
    assert all(bpy.data.objects[name].hide_get(view_layer=layer) for layer in bpy.context.scene.view_layers)
assert all(layer.objects.active is None for layer in bpy.context.scene.view_layers)
report = {
    'source': str(SOURCE), 'source_sha256': source_sha,
    'output': str(OUTPUT), 'output_sha256': sha(OUTPUT),
    'backup': str(BACKUP), 'hidden_empty_controls': NAMES,
    'verified_mesh_objects_unchanged': len(before),
    'verified': ['mesh geometry', 'mesh world transforms', 'mesh visibility', 'parent relationships', 'saved hidden state', 'selection cleared'],
    'note': 'Only the viewport display of three Empty assembly controls was hidden. Physical parts and rotation drivers were not edited.'
}
(WORK / '核對紀錄.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
