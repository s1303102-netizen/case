"""Reopen the actual deliverable; check print parts and original preservation."""
from pathlib import Path
import bpy,bmesh,json,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
report_path=HERE/'尺寸與幾何檢查.json'
r=json.loads(report_path.read_text())
bpy.ops.wm.open_mainfile(filepath=r['blend_file'])
scene=bpy.context.scene
assert scene.unit_settings.system=='METRIC' and abs(scene.unit_settings.scale_length-.001)<1e-9
assert scene.unit_settings.length_unit=='MILLIMETERS'
assert len(bpy.data.objects)==12
body=bpy.data.objects['測試集風罩_240mm弧長_本體']
assert not body.hide_get() and not body.modifiers
volumes={}
for obj in bpy.data.objects:
    assert obj.type=='MESH' and not obj.modifiers
    bm=bmesh.new();bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges),obj.name
    volumes[obj.name]=bm.calc_volume(signed=True);assert volumes[obj.name]>0
    bm.free()
    if obj.name.startswith('列印用_'):assert obj.hide_get() and obj.hide_render
    if obj.name.startswith('旁通孔片_'):assert obj.hide_get()==(obj['孔徑_mm']!=38)
assert abs(volumes['列印用_左半片']+volumes['列印用_右半片']-volumes[body.name])<.01
body.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],
    [tuple(t.vertices) for t in body.data.loop_triangles],all_triangles=True)
for dy,dz in r['preserved']['mount_holes']:
    center=Vector((2+dz,dy,-1))
    assert tree.ray_cast(center,Vector((0,0,1)),5)[0] is None,('Original flange hole blocked',dy,dz)
# Pickups end flush with the channel, with no annular tube lip in the air.
hit=tree.ray_cast(Vector((27.25,43,10)),Vector((0,1,0)),5)
assert hit[0] is not None and abs(hit[0].y-44)<.01
spec=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
arc=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']
radius=arc['fitted_arc_radius_mm']+spec['bend']['vertical_center_r_mm']
expected_y=radius-math.sqrt((radius+spec['pre_nozzle_height_mm']/2)**2-2.25**2)
hit=tree.ray_cast(Vector((2.25,-5,215)),Vector((0,-1,0)),5)
assert hit[0] is not None and abs(hit[0].y-expected_y)<.02
assert r['pressure_taps']['inlet_neck_port_center_mm']==[25,44,10]
for path,expected in r['original_file_hashes'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected
stl_checks=json.loads((HERE/'STL檔案重讀檢查.json').read_text())
assert len(stl_checks)==11 and all(q['nonmanifold_coordinate_edges']==0 and q['collapsed_triangles']==0 for q in stl_checks)
r['saved_blend_reopened_and_checked']=True
r['original_models_unchanged']=True
r['original_12_flange_holes_clear']=True
r['split_halves_volume_sum_error_mm3']=abs(volumes['列印用_左半片']+volumes['列印用_右半片']-volumes[body.name])
r['binary_stl_files_reopened_and_checked']=True
r['static_pickups_flush_geometry_checked']=True
r['blend_sha256']=hashlib.sha256(Path(r['blend_file']).read_bytes()).hexdigest()
report_path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAVED_MODEL_CHECKS_PASS',json.dumps({'parts':len(bpy.data.objects),'size_mm':r['assembled_size_mm'],'original_models_unchanged':True}),flush=True)
