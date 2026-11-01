"""Create four requested .blend files from checked print-part meshes."""
from pathlib import Path
import bpy,bmesh,ast,math,json,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
REPORT=HERE/'模型與列印檢查.json';r=json.loads(REPORT.read_text())
SOURCE=Path(r['source']);CACHE=Path(r['cache']);up=Vector((0,0,1))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(SOURCE)==r['source_sha256']
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))
def signature(o):return hashlib.sha256(json.dumps(snapshot(o),sort_keys=True).encode()).hexdigest()
def loadpart(key):
    name=r['parts'][key]['object']
    with bpy.data.libraries.load(str(CACHE),link=False) as (available,loaded):loaded.objects=[name]
    return loaded.objects[0]
def mm_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
    bpy.context.preferences.filepaths.save_version=0
    s.unit_settings.system='METRIC';s.unit_settings.scale_length=.001;s.unit_settings.length_unit='MILLIMETERS'
    return s
def viewport(target,distance,direction):
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                s=a.spaces.active;s.region_3d.view_location=target;s.region_3d.view_distance=distance
                s.region_3d.view_rotation=Vector(direction).to_track_quat('Z','Y');s.region_3d.view_perspective='PERSP'
                s.shading.type='MATERIAL';s.clip_end=100000
def material(name,c):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*c,1)
    return m
def bez(a,b,c,d,t):return a*(1-t)**3+b*3*(1-t)**2*t+c*3*(1-t)*t*t+d*t**3
def radius_min(a,b,c,d):
    out=[]
    for j in range(121):
        t=j/120;v=3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)
        w=6*(1-t)*(c-2*b+a)+6*t*(d-2*c+b);cross=v.cross(w).length
        if cross>1e-8:out.append(v.length**3/cross)
    return min(out) if out else 1e9
def hose_path(E,D,I):
    A=E+D*35;B=I-up*35;best=(-1,None)
    for l1 in range(20,101,10):
        for l2 in range(20,101,10):
            p1=A+D*l1;p2=B-up*l2
            # No backward progress in height inside the curved section.
            if p1.z>p2.z+5:continue
            value=radius_min(A,p1,p2,B)
            if value>best[0]:best=(value,(p1,p2))
    assert best[1] is not None
    p1,p2=best[1]
    points=[E+D*(2+33*j/10) for j in range(11)]
    points.extend(bez(A,p1,p2,B,j/100) for j in range(1,101))
    points.extend(I-up*(35-33*j/10) for j in range(1,11))
    return points,best[0]
def hose(name,points,mat):
    outer=[];inner=[];N=64
    for j,p in enumerate(points):
        direction=points[min(j+1,len(points)-1)]-points[max(j-1,0)]
        q=up.rotation_difference(direction.normalized())
        outer.append([p+q@Vector((27.5*math.cos(2*math.pi*i/N),27.5*math.sin(2*math.pi*i/N),0)) for i in range(N)])
        inner.append([p+q@Vector((25.5*math.cos(2*math.pi*i/N),25.5*math.sin(2*math.pi*i/N),0)) for i in range(N)])
    vv=[];ff=[]
    for ro,ri in zip(outer,inner):vv.extend(ro);vv.extend(ri)
    for j in range(len(points)-1):
        for i in range(N):
            a=j*2*N+i;b=j*2*N+(i+1)%N
            ff.extend([(a,b,b+2*N,a+2*N),(b+N,a+N,a+3*N,b+3*N)])
    for j in [0,len(points)-1]:
        for i in range(N):
            a=j*2*N+i;b=j*2*N+(i+1)%N;ff.append((a,a+N,b+N,b))
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(vv,[],ff);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    o=bpy.data.objects.new(name,data);data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    o['零件類型']='外購軟管示意；不需列印';o['名義內徑_mm']=51;o['示意外徑_mm']=55
    return o
def add_assembly(side,s,scale=1):
    info=r['placements'][side];frame=Matrix(info['frame_mm']);collection=bpy.data.collections.new('三路分流_'+side)
    s.collection.children.link(collection);made=[];pipes=[];records=[]
    split=loadpart(side);split.name='三路分流接頭_'+side
    collection.objects.link(split);split.matrix_world=Matrix.Scale(scale,4)@frame;made.append(split)
    hoodproto=loadpart('集風罩')
    for i,M in enumerate(info['hood_matrices_mm']):
        h=hoodproto if i==0 else hoodproto.copy()
        if i>0:h.data=hoodproto.data
        collection.objects.link(h);h.name=f'小型集風罩_{side}_{i+1}'
        h.matrix_world=Matrix.Scale(scale,4)@Matrix(M);made.append(h)
    mats=[material('軟管_'+side+str(i),c) for i,c in enumerate([(.03,.33,.62),(.85,.30,.055),(.025,.45,.31)])]
    for i,(el,dl,il) in enumerate(zip(info['splitter_ends_local_mm'],info['splitter_directions_local'],info['feed_local_mm'])):
        local,minrad=hose_path(Vector(el),Vector(dl),Vector(il));world=[frame@p for p in local]
        pipe=hose(f'外購導風管_{side}_{i+1}',world,mats[i]);collection.objects.link(pipe)
        pipe.matrix_world=Matrix.Scale(scale,4);made.append(pipe);pipes.append(pipe)
        records.append({'side':side,'branch':i+1,'cut_length_mm':sum((b-a).length for a,b in zip(world,world[1:])),
                        'minimum_centerline_bend_radius_mm':minrad,'centerline_world_mm':[list(p) for p in world]})
    return made,pipes,records
def bvh(o,factor=1):
    o.data.calc_loop_triangles();M=Matrix.Scale(factor,4)@o.matrix_world
    points=[M@v.co for v in o.data.vertices];tris=[tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(points,tris,all_triangles=True),points,tris

# 01: copy current complete scene; remove only the two old full-width hoods.
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));s=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
original_blower_matrices={side:[list(row) for row in bpy.data.objects[info['blower']].matrix_world]
    for side,info in r['placements'].items()}
removed=[]
for name in ['集風罩_右半邊_第二版_實體','集風罩_左半邊_第二版_實體']:
    assert name in bpy.data.objects,name
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True);removed.append(name)
allnew=[];pipeobjs=[];hoses=[]
for side in ['右側','左側']:
    made,pipes,records=add_assembly(side,s,.1);allnew+=made;pipeobjs+=pipes;hoses+=records
assert units(s)==r['original_units']
for name,sig in r['original_object_signatures'].items():
    if name not in removed:assert signature(bpy.data.objects[name])==sig,name
shelltree,sp,st=bvh(bpy.data.objects['Cube'],10)
intersections=[]
for o in allnew:
    tree,points,tris=bvh(o,10);hits=tree.overlap(shelltree)
    z=[points[v].z for hi,si in hits for v in tris[hi]]
    rec={'object':o.name,'triangle_contacts':len(hits),'contact_z_mm':[min(z),max(z)] if z else None}
    intersections.append(rec)
    print('SHELL_CHECK',json.dumps(rec,ensure_ascii=False),flush=True)
    if '外購導風管' in o.name or '三路分流接頭' in o.name:assert not hits,'New component crosses shell: '+o.name
    elif hits:
        assert all(abs(points[v].z-709.8660278)<.05 for hi,si in hits for v in tris[hi]),'Hood crosses shell away from upper trim: '+o.name
for o in bpy.context.selected_objects:o.select_set(False)
for o in allnew:o.select_set(True)
bpy.context.view_layer.objects.active=allnew[0]
viewport((0,-4,48),180,(-1.1,1.8,.8))
files=[HERE/'01_第一版_三路分流集風罩.blend',HERE/'02_單側鼓風機_導管_集風罩.blend',HERE/'03_分流接頭_左右款.blend',HERE/'04_小型集風罩_共用款.blend']
bpy.ops.wm.save_as_mainfile(filepath=str(files[0]))

# 02: one side including the unchanged blower; actual millimetre units.
s=mm_scene()
blowername=r['placements']['右側']['blower']
with bpy.data.libraries.load(str(SOURCE),link=False) as (available,loaded):loaded.objects=[blowername]
blower=loaded.objects[0];s.collection.objects.link(blower)
bpy.context.view_layer.update()
blower.matrix_world=Matrix.Scale(10,4)@Matrix(original_blower_matrices['右側'])
made,pipes,records=add_assembly('右側',s,1)
viewport((-330,-60,370),1000,(-1.1,1.8,.8))
bpy.ops.wm.save_as_mainfile(filepath=str(files[1]))

# 03: two variants, both genuine one-piece printable meshes.
s=mm_scene()
for key,x in [('右側',-160),('左側',160)]:
    o=loadpart(key);s.collection.objects.link(o);o.matrix_world=Matrix.Translation((x,0,0))
viewport((0,-25,80),760,(1.3,-1.8,.8))
bpy.ops.wm.save_as_mainfile(filepath=str(files[2]))

# 04: one reusable small hood.
s=mm_scene();o=loadpart('集風罩');s.collection.objects.link(o);o.matrix_world=Matrix.Translation((0,0,25))
viewport((0,-20,120),430,(1.1,-1.8,.8))
bpy.ops.wm.save_as_mainfile(filepath=str(files[3]))

r.update({'blend_files':[str(p) for p in files],'replaced_old_hood_objects':removed,
    'original_blower_matrices_cm':original_blower_matrices,
    'original_other_objects_preserved':True,'hose_cut_lengths':hoses,'shell_checks':intersections,
    'source_sha256_after':digest(SOURCE),'stage':'four files saved; reopen verification pending'})
assert r['source_sha256_after']==r['source_sha256']
REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2))
print('FOUR_BLEND_FILES_SAVED',flush=True)
