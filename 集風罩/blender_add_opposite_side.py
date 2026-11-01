"""Add the opposite full-size hood and an identical, rigidly rotated blower.

Stage and reopen before installing. Preserve every existing object and unit.
This performs geometry checks only; no fluid simulation.
"""
from pathlib import Path
import bpy,bmesh,ast,json,hashlib,shutil,os,math
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'第一版.blend'
BACKUP=HERE/'第一版_新增另一側鼓風機與集風罩前備份.blend'
STAGED=HERE/'第一版_雙側待檢查.blend'
REPORT=HERE/'雙側鼓風機與集風罩_位置與原物件檢查.json'
OLD_HOOD='集風罩_右半邊_第二版_實體'
OLD_BLOWER='鼓風機_150FLJ330W_整體網格'
NEW_HOOD='集風罩_左半邊_第二版_實體'
NEW_BLOWER='鼓風機_150FLJ330W_左側_整體網格'

tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
    and n.name in {'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signature(obj):
    return hashlib.sha256(json.dumps(snapshot(obj),sort_keys=True).encode()).hexdigest()
def bounds(obj):
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    low=[min(p[a] for p in points) for a in range(3)]
    high=[max(p[a] for p in points) for a in range(3)]
    return {'min':low,'max':high,'size':[b-a for a,b in zip(low,high)]}
def bvh(obj):
    obj.data.calc_loop_triangles()
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    tris=[tuple(t.vertices) for t in obj.data.loop_triangles]
    return BVHTree.FromPolygons(pts,tris,all_triangles=True),pts,tris

source_hash=digest(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
assert NEW_HOOD not in bpy.data.objects and NEW_BLOWER not in bpy.data.objects,'Opposite side already exists.'
assert OLD_HOOD in bpy.data.objects and OLD_BLOWER in bpy.data.objects
before={o.name:signature(o) for o in bpy.data.objects}
old_units=units(bpy.context.scene)
old_scenes=sorted(s.name for s in bpy.data.scenes)
if BACKUP.exists():assert digest(BACKUP)==source_hash,'Existing backup belongs to another source version.'
else:shutil.copy2(SOURCE,BACKUP)

collection=bpy.data.collections.new('左側鼓風機與集風罩')
bpy.context.scene.collection.children.link(collection)
reflect=Matrix.Diagonal((-1.0,1.0,1.0,1.0))
source_hood=bpy.data.objects[OLD_HOOD]
hood=source_hood.copy();hood.data=source_hood.data.copy();hood.name=NEW_HOOD
hood.data.name='集風罩_左半邊_第二版_網格'
collection.objects.link(hood)
# Bake the reflection into the new mesh, reverse winding, and keep positive scale.
hood.data.transform(reflect)
bm=bmesh.new();bm.from_mesh(hood.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(hood.data);bm.free();hood.data.update()
hood.matrix_world=reflect@source_hood.matrix_world@reflect
hood['範圍']='左半邊（X正側）；以X=0對稱原右側，沿用原中央50mm不出風範圍'
hood['建立方式']='以目前第一版.blend內的原尺寸右側集風罩對稱建立'
spec=json.loads((HERE/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
inlet_shift_cm=8.0
loft_start=50.0
loft_end=spec['bend']['start_Z_mm']-55.0-source_hood.location.z*10
# Translate each horizontal section without changing its span or area. A
# quintic taper leaves the complete inlet neck and upper turn tangent intact.
for vertex in hood.data.vertices:
    t=max(0.0,min(1.0,(vertex.co.z-loft_start)/(loft_end-loft_start)))
    taper=10*t**3-15*t**4+6*t**5
    vertex.co.y-=inlet_shift_cm*10*taper
hood.location.y+=inlet_shift_cm
hood.data.update()
hood['進風端向Y正方向位移_cm']=inlet_shift_cm
hood['下段修正']='入口及法蘭內移8cm；展寬段以五次曲線漸變銜接，原90度彎道與出風口位置保留'

source_blower=bpy.data.objects[OLD_BLOWER]
blower=source_blower.copy();blower.data=source_blower.data.copy();blower.name=NEW_BLOWER
blower.data.name='鼓風機_150FLJ330W_左側_網格'
collection.objects.link(blower)
port_local=Vector((113,-1.5,159))
# The blower is the same manufactured part, not reflected geometry. Rotation
# reverses its local flange Y direction; that flange/bolt pattern is symmetric.
local_y_flip=Matrix.Translation(port_local)@Matrix.Diagonal((1.0,-1.0,1.0,1.0))@Matrix.Translation(-port_local)
shift=Matrix.Translation((0,inlet_shift_cm,0))
blower.matrix_world=shift@reflect@source_blower.matrix_world@local_y_flip
blower['定位方式']='原鼓風機網格複製並剛體旋轉；保持相同葉輪與蝸殼手性，出風朝上'
bpy.context.view_layer.update()
assert blower.matrix_world.to_3x3().determinant()>0
assert hood.matrix_world.to_3x3().determinant()>0
assert [list(v.co) for v in blower.data.vertices]==[list(v.co) for v in source_blower.data.vertices]
assert [list(p.vertices) for p in blower.data.polygons]==[list(p.vertices) for p in source_blower.data.polygons]
assert (blower.matrix_world@port_local-hood.location).length<1e-4
normal=(blower.matrix_world.to_3x3()@Vector((1,0,0))).normalized()
assert (normal-Vector((0,0,1))).length<1e-5
# Confirm the asymmetric 2-mm flange offset and the symmetric bolt locations
# coincide with the reflected original interface.
flange_points=[Vector((113,-1.5,161))]
for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
    flange_points.append(Vector((113,-1.5+dy,161+dz)))
actual=[blower.matrix_world@p for p in flange_points]
expected=[shift@reflect@source_blower.matrix_world@p for p in flange_points]
flange_error=max(min((a-e).length for e in expected) for a in actual)*10
assert flange_error<.001

report={'source_sha256':source_hash,'backup':str(BACKUP),'added_objects':[NEW_BLOWER,NEW_HOOD],
        'original_objects_preserved':list(before),'mirror_plane':'X=0 cm','scene_units_preserved':old_units,
        'blower_is_identical_mesh_rigidly_rotated':True,'blower_mesh_reflected':False,
        'new_port_center_cm':list(blower.matrix_world@port_local),
        'inlet_shift_from_exact_mirror_cm':[0,inlet_shift_cm,0],
        'hood_transition_adjustment':'Horizontal sections shift with quintic taper between original neck and upper straight; outlet and bend unchanged.',
        'flange_and_bolt_alignment_max_error_mm':flange_error,'CFD_executed':False}
for obj in [hood,blower]:
    bb=bounds(obj);report[obj.name]={'bounds_cm':bb,'matrix':[list(r) for r in obj.matrix_world]}
    print('NEW_BOUNDS',obj.name,json.dumps(bb),flush=True)
    assert 0<bb['min'][0]<bb['max'][0]<70
    assert -25<bb['min'][1]<bb['max'][1]<25
    assert -.0001<bb['min'][2]<bb['max'][2]<125
shelltree,shellpoints,shelltris=bvh(bpy.data.objects['Cube'])
ht,hp,htri=bvh(hood);bt,bp,btri=bvh(blower)
assert not bt.overlap(shelltree),'New blower intersects shell.'
contacts=ht.overlap(shelltree)
report['new_blower_shell_surface_intersections']=0
report['new_hood_shell_surface_contacts']=len(contacts)
for hi,si in contacts:
    assert all(abs(hp[v].z-70.9866)<.001 for v in htri[hi]),'Hood intersects shell away from original upper opening trim.'
assert not ht.overlap(bvh(source_hood)[0]),'Left and right hoods overlap.'
assert not bt.overlap(bvh(source_blower)[0]),'Left and right blowers overlap.'
assert not ht.overlap(bvh(source_blower)[0])
assert not bt.overlap(bvh(source_hood)[0])
report['opposite_side_pair_surface_intersections']=0
bm=bmesh.new();bm.from_mesh(hood.data)
assert all(e.is_manifold for e in bm.edges)
assert bm.calc_volume(signed=True)>0
report['new_hood_nonmanifold_edges']=0
bm.free()
# Match original slit path, with reflection of both point and exit direction.
arc=json.loads((HERE/'右半邊集風罩_計算.json').read_text())['measured']
R=arc['fitted_arc_radius_mm'];CY=arc['fitted_arc_center_Y_mm'];Z=arc['opening_center_Z_mm']
t0,t1=map(math.radians,arc['arc_theta_degrees'])
gaps=[]
for i in range(1,40):
    a=t0+(t1-t0)*i/40
    p=Vector(((R+2)*math.sin(a)/10,(CY-(R+2)*math.cos(a))/10,Z/10))
    up=ht.ray_cast(p,Vector((0,0,1)),.3)
    down=ht.ray_cast(p,Vector((0,0,-1)),.3)
    assert up[0] is not None and down[0] is not None
    gap=(up[3]+down[3])*10;gaps.append(gap)
    assert abs(gap-2)<.002
    exit_direction=Vector((-math.sin(a),math.cos(a),0))
    assert ht.ray_cast(p,exit_direction,.8)[0] is None
    assert shelltree.ray_cast(p,exit_direction,2)[0] is None,'Shell blocks new outlet.'
report['slit_gap_mm']=[min(gaps),max(gaps)]
report['outlet_clear_samples']=len(gaps)
for name,expected_sig in before.items():assert signature(bpy.data.objects[name])==expected_sig,name
assert units(bpy.context.scene)==old_units
for o in bpy.context.selected_objects:o.select_set(False)
hood.select_set(True);blower.select_set(True);bpy.context.view_layer.objects.active=hood
bpy.ops.wm.save_as_mainfile(filepath=str(STAGED))

# Reopen the actual saved file, then install only after preservation checks.
bpy.ops.wm.open_mainfile(filepath=str(STAGED))
assert set(bpy.data.objects.keys())==set(before)|{NEW_HOOD,NEW_BLOWER}
for name,expected_sig in before.items():assert signature(bpy.data.objects[name])==expected_sig,name
assert units(bpy.context.scene)==old_units
assert sorted(s.name for s in bpy.data.scenes)==old_scenes
report['saved_file_reopened_and_original_objects_verified']=True
assert digest(SOURCE)==source_hash,'Source changed while working; refusing installation.'
final_hash=digest(STAGED)
os.replace(STAGED,SOURCE)
assert digest(SOURCE)==final_hash
report['result_file']=str(SOURCE);report['result_sha256']=final_hash
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('OPPOSITE_SIDE_INSTALLED',json.dumps(report,ensure_ascii=False),flush=True)

# Render both installed assemblies without the enclosure hiding the far side.
original_scene=bpy.context.scene
tree=ast.parse((HERE/'blender_build_right_hood.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
    and n.name in {'look','preview'}],type_ignores=[]),'preview_helpers','exec'))
preview([bpy.data.objects[n] for n in [OLD_HOOD,OLD_BLOWER,NEW_HOOD,NEW_BLOWER]],
        .01,(1.35,-2.10,1.35),(0,-.05,.40),1.62,'雙側鼓風機與集風罩_配置預覽.png')
print('OPPOSITE_SIDE_COMPLETE',flush=True)
