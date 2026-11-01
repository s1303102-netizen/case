"""Reposition one blower and reuse the right splitter on both sides; preserve inputs."""
from pathlib import Path
import bpy,bmesh,ast,json,math,hashlib,shutil
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'三路分流_正式模型';ROOT=HERE.parent.parent
old=json.loads((OLD/'模型與列印檢查.json').read_text())
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=[ROOT/'第一版.blend']+sorted(OLD.glob('*.blend'))+sorted((OLD/'STL_毫米').glob('*.stl'))
input_hashes={str(p):digest(p) for p in inputs}
assert digest(ROOT/'第一版.blend')==old['source_sha256'],'Original source changed since earlier delivery.'
tree=ast.parse((OLD/'assemble_four_blends.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {
    'bez','radius_min','hose_path','hose','material','viewport','mm_scene'}],type_ignores=[]),'assembly_helpers','exec'))
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {
    'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))
up=Vector((0,0,1))
def signature(o):return hashlib.sha256(json.dumps(snapshot(o),sort_keys=True).encode()).hexdigest()
def geohash(o):
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],
        'f':[list(p.vertices) for p in o.data.polygons]},separators=(',',':')).encode()).hexdigest()
def geo(o,factor=10):
    o.data.calc_loop_triangles();M=Matrix.Scale(factor,4)@o.matrix_world
    pts=[M@v.co for v in o.data.vertices];tris=[tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(pts,tris,all_triangles=True),pts,tris
def solid(o):
    bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges)
    todo=set(bm.verts);count=0
    while todo:
        count+=1;stack=[todo.pop()]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                q=e.other_vert(v)
                if q in todo:todo.remove(q);stack.append(q)
    vol=bm.calc_volume(signed=True);bm.free()
    assert bad==0 and count==1 and vol>1000,(o.name,bad,count,vol)
    return {'nonmanifold_edges':bad,'connected_components':count,'volume_mm3':vol}
def max_matrix_error(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))

files=[HERE/'01_第一版_共用分流接頭.blend',HERE/'02_單側鼓風機_導管_集風罩.blend',
       HERE/'03_共用分流接頭.blend',HERE/'04_小型集風罩_共用款.blend']
bpy.ops.wm.open_mainfile(filepath=str(OLD/'01_第一版_三路分流集風罩.blend'))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
baseline={o.name:signature(o) for o in bpy.data.objects}
right=bpy.data.objects[old['placements']['右側']['blower']]
left=bpy.data.objects[old['placements']['左側']['blower']]
left_mesh_hash=geohash(left);left_before=left.matrix_world.copy()
port_local=Vector((113,-1.5,159));rp=right.matrix_world@port_local;lp=left.matrix_world@port_local
target=Vector((-rp.x,rp.y,rp.z))
left.matrix_world=Matrix.Translation(target)@Matrix.Rotation(math.pi,4,'Z')@Matrix.Translation(-lp)@left_before
left_after=left.matrix_world.copy()
assert geohash(left)==left_mesh_hash
X=(left.matrix_world.to_3x3()@Vector((0,0,1))).normalized();Y=up.cross(X).normalized()
frame=Matrix(((X.x,Y.x,0,target.x),(X.y,Y.y,0,target.y),(0,0,1,target.z),(0,0,0,1)))
frame_mm=frame.copy();frame_mm.translation=frame.translation*10
collection=bpy.data.objects['三路分流接頭_左側'].users_collection[0]
modified={left.name,'三路分流接頭_左側'}|{f'外購導風管_左側_{i}' for i in range(1,4)}
for name in modified-{left.name}:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
right_split=bpy.data.objects['三路分流接頭_右側']
left_split=right_split.copy();collection.objects.link(left_split)
left_split.name='三路分流接頭_左側';left_split.matrix_world=frame@Matrix.Scale(.1,4)
left_split['安裝側']='左側；與右側共用同一網格，水平旋轉安裝'
hoses=[];paths=[]
colors=[(.03,.33,.62),(.85,.30,.055),(.025,.45,.31)]
for i,(e,d) in enumerate(zip(old['placements']['右側']['splitter_ends_local_mm'],old['placements']['右側']['splitter_directions_local'])):
    hood_index=3-i
    hood=bpy.data.objects[f'小型集風罩_左側_{hood_index}']
    inlet=hood.matrix_world.translation*10
    local_feed=frame_mm.inverted()@inlet
    local,minrad=hose_path(Vector(e),Vector(d),local_feed)
    world=[frame_mm@p for p in local]
    h=hose(f'外購導風管_左側_{i+1}',world,material(f'軟管_左側_修正版_{i+1}',colors[i]))
    collection.objects.link(h);h.matrix_world=Matrix.Scale(.1,4)
    hoses.append(h);paths.append(world)
    hoses[-1]['接至集風罩編號']=hood_index
    print('NEW_HOSE',i+1,'radius',minrad,flush=True)
    assert minrad>40
    if i==0:hose_records=[]
    hose_records.append({'side':'左側','branch':i+1,'hood_index':hood_index,
        'cut_length_mm':sum((b-a).length for a,b in zip(world,world[1:])),
        'minimum_centerline_bend_radius_mm':minrad,'centerline_world_mm':[list(p) for p in world]})
for name,sig in baseline.items():
    if name not in modified:assert signature(bpy.data.objects[name])==sig,name
assert units(s)==old['original_units']
assert geohash(left_split)==geohash(right_split)
shelltree,_,_=geo(bpy.data.objects['Cube'])
cache={o.name:geo(o) for o in bpy.data.objects if o.type=='MESH'}
shell_checks=[]
for o in [left,right,left_split,right_split]+[o for o in bpy.data.objects if o.name.startswith('外購導風管')]:
    hits=cache[o.name][0].overlap(shelltree)
    shell_checks.append({'object':o.name,'shell_surface_intersections':len(hits)})
    assert not hits,(o.name,'crosses shell')
left_hoods=[bpy.data.objects[f'小型集風罩_左側_{i}'] for i in range(1,4)]
right_objects=[o for o in bpy.data.objects if '右側' in o.name and o.type=='MESH']+[right]
pair_checks=[]
for i,h in enumerate(hoses):
    # Its own hood and splitter overlap deliberately over the hose slip-on length.
    unrelated=[left,right]+hoses[i+1:]+[q for q in left_hoods if q.name!=f'小型集風罩_左側_{3-i}']+right_objects
    for other in unrelated:
        hits=cache[h.name][0].overlap(cache[other.name][0])
        pair_checks.append({'a':h.name,'b':other.name,'triangle_contacts':len(hits)})
        assert not hits,(h.name,other.name,'unintended contact')
for a in [left,left_split]+left_hoods:
    for b in right_objects:
        hits=cache[a.name][0].overlap(cache[b.name][0])
        assert not hits,(a.name,b.name,'opposite side contact')
for o in bpy.context.selected_objects:o.select_set(False)
for o in [left,left_split]+hoses:o.select_set(True)
bpy.context.view_layer.objects.active=left
viewport((0,-4,43),175,(1.1,-1.8,.8))
bpy.ops.wm.save_as_mainfile(filepath=str(files[0]))

# Single-side view remains the original right-side complete assembly.
shutil.copy2(OLD/'02_單側鼓風機_導管_集風罩.blend',files[1])
shutil.copy2(OLD/'04_小型集風罩_共用款.blend',files[3])
s=mm_scene()
with bpy.data.libraries.load(str(OLD/'03_分流接頭_左右款.blend'),link=False) as (available,loaded):
    loaded.objects=[old['parts']['右側']['object']]
common=loaded.objects[0]
s.collection.objects.link(common)
common.name='分流接頭_左右共用_一體件';common.matrix_world=Matrix.Identity(4)
common['方向']='左右共用';common['全機列印數量']=2
common['安裝方式']='左右同件；各隨鼓風機法蘭方向旋轉，非鏡像零件'
common.select_set(True);bpy.context.view_layer.objects.active=common
viewport((0,0,75),360,(1.2,-1.8,.8))
part_checks={'分流接頭':solid(common)};commonhash=geohash(common)
bpy.ops.wm.save_as_mainfile(filepath=str(files[2]))

copy_stls={
    '分流接頭_右側_列印_mm.stl':'分流接頭_左右共用_mm.stl',
    '小型集風罩_共用款_直立_mm.stl':'小型集風罩_共用款_直立_mm.stl',
    '小型集風罩_共用款_斜放45度_mm.stl':'小型集風罩_共用款_斜放45度_mm.stl'}
for src,dst in copy_stls.items():shutil.copy2(OLD/'STL_毫米'/src,HERE/'STL_毫米'/dst)

# Reopen all four saved files and check the actual saved coordinates/geometry.
bpy.ops.wm.open_mainfile(filepath=str(files[0]))
for name,sig in baseline.items():
    if name not in modified:assert signature(bpy.data.objects[name])==sig,name
left=bpy.data.objects[old['placements']['左側']['blower']]
assert geohash(left)==left_mesh_hash
assert max_matrix_error(left.matrix_world,left_after)<1e-5
actual=left.matrix_world@port_local
assert (actual-target).length<1e-4
assert abs((left.matrix_world.to_3x3()@Vector((1,0,0))).normalized().dot(up)-1)<1e-6
for side in ['右側','左側']:assert geohash(bpy.data.objects[f'三路分流接頭_{side}'])==commonhash
common_hood_hash=geohash(bpy.data.objects['小型集風罩_右側_1'])
for side in ['右側','左側']:
    for j in range(1,4):assert geohash(bpy.data.objects[f'小型集風罩_{side}_{j}'])==common_hood_hash
for i,rec in enumerate(hose_records):
    o=bpy.data.objects[f'外購導風管_左側_{i+1}']
    assert o['接至集風罩編號']==rec['hood_index']
    assert max_matrix_error(o.matrix_world,Matrix.Scale(.1,4))<1e-6
bpy.ops.wm.open_mainfile(filepath=str(files[1]));assert len(bpy.data.objects)==8
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
assert geohash(bpy.data.objects['三路分流接頭_右側'])==commonhash
bpy.ops.wm.open_mainfile(filepath=str(files[2]));assert len(bpy.data.objects)==1
assert geohash(next(iter(bpy.data.objects)))==commonhash
bpy.ops.wm.open_mainfile(filepath=str(files[3]));assert len(bpy.data.objects)==1
hood=next(iter(bpy.data.objects));assert geohash(hood)==common_hood_hash
part_checks['小型集風罩']=solid(hood)
for p,h in input_hashes.items():assert digest(p)==h,p
report={'revision':'左右共用分流接頭；另一側鼓風機轉180度並將出口後移80mm',
    'date':'2026-10-29','input_sha256_preserved':input_hashes,
    'original_blend_untouched':True,'previous_delivery_untouched':True,
    'full_scene_units':old['original_units'],'standalone_units':'mm',
    'right_port_mm':list(rp*10),'old_left_port_mm':list(lp*10),'new_left_port_mm':list(target*10),
    'left_blower_before_cm':[list(row) for row in left_before],
    'left_blower_after_cm':[list(row) for row in left_after],
    'left_splitter_frame_mm':[list(row) for row in frame_mm],
    'left_blower_mesh_unchanged':True,'two_splitters_same_geometry':True,
    'all_other_previous_objects_unchanged':True,'all_six_hoods_same_geometry':True,
    'hose_records':[{**q,'hood_index':i+1} for i,q in enumerate(old['hose_cut_lengths'][:3])]+hose_records,
    'shell_checks':shell_checks,'hose_pair_checks':pair_checks,
    'saved_files_reopened_and_verified':True,'part_checks':part_checks,
    'blend_files':[str(p) for p in files],'blend_sha256':{p.name:digest(p) for p in files},
    'STL_same_geometry_as_previous_right_and_common_hood':True,'STL_copy_mapping':copy_stls,
    'previous_full_path_and_slot_checks':old['saved_file_checks'],
    'CFD_executed':False,'performance_validated':False,'physical_print_tested':False}
(HERE/'修改與幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('SHARED_REVISION_SAVED_AND_REOPENED',json.dumps({'files':[str(p) for p in files],
    'ports_mm':[list(rp*10),list(target*10)],'left_hose_lengths_mm':[q['cut_length_mm'] for q in hose_records]},ensure_ascii=False),flush=True)
