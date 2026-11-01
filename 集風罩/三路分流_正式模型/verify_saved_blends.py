from pathlib import Path
import bpy,bmesh,ast,json,math,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
REPORT=HERE/'模型與列印檢查.json';r=json.loads(REPORT.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=Path(r['source']);assert digest(source)==r['source_sha256']
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))
def signature(o):return hashlib.sha256(json.dumps(snapshot(o),sort_keys=True).encode()).hexdigest()
def geohash(o):
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],
        'f':[list(p.vertices) for p in o.data.polygons]},separators=(',',':')).encode()).hexdigest()
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
    return {'nonmanifold_edges':bad,'connected_material_components':count,'signed_material_volume_mm3':vol}
def bvh(o):
    o.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def clear_path(tree,path,label):
    for a,b in zip(path,path[1:]):
        d=b-a
        if d.length>.0001:
            hit=tree.ray_cast(a,d.normalized(),d.length)
            assert hit[0] is None,(label,list(a),list(b),list(hit[0]))
def bez(a,b,c,d,t):return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
checks={};expected_geo={}

bpy.ops.wm.open_mainfile(filepath=r['blend_files'][2])
assert len(bpy.data.objects)==2
for side in ['右側','左側']:
    o=next(o for o in bpy.data.objects if o.get('方向')==side)
    checks[side]=solid(o);expected_geo[side]=geohash(o);tree=bvh(o)
    info=r['placements'][side]
    for k,(e,d) in enumerate(zip(info['splitter_ends_local_mm'],info['splitter_directions_local'])):
        E=Vector(e);D=Vector(d);p0=Vector(((k-1)*28,0,40));p1=p0+Vector((0,0,30));p2=E-D*32
        pts=[Vector((0,0,-1)),Vector((0,0,25)),p0]
        pts.extend(bez(p0,p1,p2,E,j/150) for j in range(1,151))
        pts.extend(E+D*j for j in range(1,28));clear_path(tree,pts,side+str(k))
    checks[side]['three_full_center_paths_clear']=True

bpy.ops.wm.open_mainfile(filepath=r['blend_files'][3])
assert len(bpy.data.objects)==1;o=next(iter(bpy.data.objects));checks['集風罩']=solid(o);expected_geo['集風罩']=geohash(o)
tree=bvh(o);Z=699.8660278320312;rb=28;Ln=51.42645372522041;rv=Ln+rb;entryZ=509.8660278320312
pts=[Vector((0,0,z)) for z in range(-28,163)]
for j in range(1,101):
    a=math.pi/2*j/100;r0=Ln+rb*math.cos(a);pts.append(Vector((0,r0-rv,Z-rb-entryZ+rb*math.sin(a))))
pts.extend(Vector((0,r0-rv,Z-entryZ)) for r0 in [Ln*(1-j/200) for j in range(1,201)])
pts.append(Vector((0,-rv-3,Z-entryZ)));clear_path(tree,pts,'Hood')
checks['集風罩']['full_center_path_clear']=True
R=749.6789214766717;theta_span=r['universal_hood_arc_mm']/R;gaps=[]
for j in range(1,60):
    a=(j/60-.5)*theta_span;center=Vector(((R+1)*math.sin(a),(R+1)*math.cos(a)-(R+rv),Z-entryZ))
    upper=tree.ray_cast(center,Vector((0,0,1)),10);lower=tree.ray_cast(center,Vector((0,0,-1)),10)
    assert upper[0] is not None and lower[0] is not None
    gap=upper[3]+lower[3];gaps.append(gap);assert abs(gap-2)<.005
checks['集風罩']['saved_measured_slot_mm']=[min(gaps),max(gaps)]

bpy.ops.wm.open_mainfile(filepath=r['blend_files'][0])
for name,sig in r['original_object_signatures'].items():
    if name not in r['replaced_old_hood_objects']:assert signature(bpy.data.objects[name])==sig,name
assert units(bpy.context.scene)==r['original_units']
for side in ['右側','左側']:
    assert geohash(bpy.data.objects['三路分流接頭_'+side])==expected_geo[side]
    for j in range(1,4):assert geohash(bpy.data.objects[f'小型集風罩_{side}_{j}'])==expected_geo['集風罩']
assert all(name not in bpy.data.objects for name in r['replaced_old_hood_objects'])
checks['完整場景']={'all_other_source_objects_preserved':True,'old_hoods_replaced':True,'six_hood_meshes_match_one_common_STL':True}

bpy.ops.wm.open_mainfile(filepath=r['blend_files'][1])
assert len(bpy.data.objects)==8,len(bpy.data.objects)
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
blower=bpy.data.objects[r['placements']['右側']['blower']]
expected_matrix=Matrix.Scale(10,4)@Matrix(r['original_blower_matrices_cm']['右側'])
assert max(abs(blower.matrix_world[i][j]-expected_matrix[i][j]) for i in range(4) for j in range(4))<.0001
assert geohash(bpy.data.objects['三路分流接頭_右側'])==expected_geo['右側']
for j in range(1,4):assert geohash(bpy.data.objects[f'小型集風罩_右側_{j}'])==expected_geo['集風罩']
checks['單側組裝']={'objects':8,'unit':'millimetres','single_side_complete':True,'blower_scale_and_position_verified':True}
assert digest(source)==r['source_sha256']
r['saved_files_reopened_and_verified']=True;r['saved_file_checks']=checks
r['blend_sha256']={Path(p).name:digest(Path(p)) for p in r['blend_files']}
r['stage']='complete; source preserved; four saved files reopened; STL checks in separate report'
REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2))
print('FOUR_SAVED_BLEND_FILES_VERIFIED',json.dumps(checks,ensure_ascii=False),flush=True)
