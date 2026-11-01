"""Build actual single-body print parts in millimetres; source is read only."""
from pathlib import Path
import bpy,bmesh,math,json,hashlib,ast,struct
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
SOURCE=ROOT/'第一版.blend';CACHE=Path('/private/tmp/split_duct_print_parts.blend')
HERE.mkdir(exist_ok=True);(HERE/'STL_毫米').mkdir(exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=digest(SOURCE)
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))
def signature(o):return hashlib.sha256(json.dumps(snapshot(o),sort_keys=True).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
baseline={o.name:signature(o) for o in bpy.data.objects}
source_units=units(bpy.context.scene)
spec=json.loads((ROOT/'集風罩/Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
arcdata=json.loads((ROOT/'集風罩/右半邊集風罩_計算.json').read_text())['measured']
R=arcdata['fitted_arc_radius_mm'];CY=arcdata['fitted_arc_center_Y_mm'];Z=arcdata['opening_center_Z_mm']
t0,t1=map(math.radians,arcdata['arc_theta_degrees']);tf=(t0+t1)/2
Ln=spec['nozzle']['total_length_mm'];Lc=spec['nozzle']['converging_length_mm'];rb=28.;h=spec['pre_nozzle_height_mm']
rv=Ln+rb;upperZ=Z-rb-12;entryZ=upperZ-150;wall=2.4
span=((t1-t0)*R-12)/3;theta_span=span/R;up=Vector((0,0,1))
def arc(side,a,r,z):return Vector((side*(R+r)*math.sin(a),CY-(R+r)*math.cos(a),z))
placements={}
for side,key,name in [(-1,'右側','鼓風機_150FLJ330W_整體網格'),(1,'左側','鼓風機_150FLJ330W_左側_整體網格')]:
    blower=bpy.data.objects[name];port=(blower.matrix_world@Vector((113,-1.5,159)))*10
    X=(blower.matrix_world.to_3x3()@Vector((0,0,1))).normalized();Y=up.cross(X).normalized()
    frame=Matrix(((X.x,Y.x,0,port.x),(X.y,Y.y,0,port.y),(0,0,1,port.z),(0,0,0,1)))
    mids=[t0+theta_span/2+k*(theta_span+6/R) for k in range(3)]
    hood_matrices=[];feeds=[]
    for mid in mids:
        tangent=Vector((side*math.cos(mid),math.sin(mid),0));back=Vector((side*math.sin(mid),-math.cos(mid),0))
        hx=tangent if side==-1 else -tangent;hy=back;p=arc(side,mid,rv,entryZ)
        M=Matrix(((hx.x,hy.x,0,p.x),(hx.y,hy.y,0,p.y),(0,0,1,p.z),(0,0,0,1)))
        assert M.to_3x3().determinant()>.99
        hood_matrices.append([list(row) for row in M]);feeds.append(frame.inverted()@p)
    shift=frame.inverted().to_3x3()@Vector((0,-90 if side==1 else 0,0))
    ends=[Vector(((k-1)*70,0,120))+shift for k in range(3)]
    dirs=[(p-e+up*35).normalized() for p,e in zip(feeds,ends)]
    placements[key]={'blower':name,'frame_mm':[list(row) for row in frame],
        'hood_matrices_mm':hood_matrices,'feed_local_mm':[list(p) for p in feeds],
        'splitter_ends_local_mm':[list(p) for p in ends],'splitter_directions_local':[list(p) for p in dirs]}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
def material(name,color,metal=.05):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal
    return m
bodymat=material('列印件_藍灰',(.06,.24,.32));lipmat=material('刀口面板',(.28,.38,.43),.3)
def active(o):
    for q in bpy.context.selected_objects:q.select_set(False)
    o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,verts,faces,mat=bodymat):
    d=bpy.data.meshes.new(name+'_Mesh');d.from_pydata(verts,[],faces);d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o)
    if mat:d.materials.append(mat)
    return o
def loft(name,rings,mat=bodymat):
    n=len(rings[0]);vv=[p for r in rings for p in r];ff=[]
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;ff.append((a,b,b+n,a+n))
    ff.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
    return mesh(name,vv,ff,mat)
def hollow(name,outer,inner,mat=bodymat):
    n=len(outer[0]);N=len(outer);vv=[];ff=[]
    for ro,ri in zip(outer,inner):vv.extend(ro);vv.extend(ri)
    for j in range(N-1):
        for i in range(n):
            a=j*2*n+i;b=j*2*n+(i+1)%n
            ff.extend([(a,b,b+2*n,a+2*n),(b+n,a+n,a+3*n,b+3*n)])
    for j in [0,N-1]:
        for i in range(n):
            a=j*2*n+i;b=j*2*n+(i+1)%n;ff.append((a,a+n,b+n,b))
    return mesh(name,vv,ff,mat)
def rect(w,d,r=3,N=12):
    out=[]
    for x,y,a in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
        for j in range(N):
            t=math.radians(a+90*j/N);out.append((x+r*math.cos(t),y+r*math.sin(t)))
    return out
def superpts(w,d,n,N=96):
    return [(w/2*math.copysign(abs(math.cos(2*math.pi*j/N))**(2/n),math.cos(2*math.pi*j/N)),
             d/2*math.copysign(abs(math.sin(2*math.pi*j/N))**(2/n),math.sin(2*math.pi*j/N))) for j in range(N)]
def S(t):return 10*t**3-15*t**4+6*t**5
def bez(a,b,c,d,t):return a*(1-t)**3+b*3*(1-t)**2*t+c*3*(1-t)*t*t+d*t**3
def cylinder(name,start,end,r,N=96):
    start=Vector(start);end=Vector(end);axis=(end-start).normalized();q=up.rotation_difference(axis)
    return loft(name,[[p+q@Vector((r*math.cos(2*math.pi*j/N),r*math.sin(2*math.pi*j/N),0)) for j in range(N)] for p in [start,end]])
def boolean(o,cutter,operation='UNION'):
    label=cutter.name
    active(o);m=o.modifiers.new('實體接合' if operation=='UNION' else '真正流道與孔','BOOLEAN');m.operation=operation;m.solver='MANIFOLD' if '左側' in o.name else 'EXACT';m.object=cutter
    bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
    print('BOOLEAN',o.name,label,operation,'bad_edges',bad,flush=True)
def bounds(o,M=None):
    M=M or o.matrix_world;p=[M@v.co for v in o.data.vertices]
    lo=[min(q[i] for q in p) for i in range(3)];hi=[max(q[i] for q in p) for i in range(3)]
    return {'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}
def check(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bad=sum(not e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True)
    todo=set(bm.verts);parts=[];components=[]
    while todo:
        stack=[todo.pop()];num=0;component=[]
        while stack:
            v=stack.pop();num+=1;component.append(v)
            for e in v.link_edges:
                q=e.other_vert(v)
                if q in todo:todo.remove(q);stack.append(q)
        parts.append(num);components.append(component)
    if len(parts)>1:
        print('COMPONENTS',o.name,[(len(c),[min(v.co[i] for v in c) for i in range(3)],[max(v.co[i] for v in c) for i in range(3)]) for c in components],flush=True)
        components.sort(key=len,reverse=True);debris=[]
        for c in components[1:]:
            origin=c[0].co;faces={f for v in c for f in v.link_faces};volume=0
            for face in faces:
                p=[v.co-origin for v in face.verts]
                volume+=sum(p[0].dot(p[i].cross(p[i+1]))/6 for i in range(1,len(p)-1))
            size=[max(v.co[i] for v in c)-min(v.co[i] for v in c) for i in range(3)]
            assert abs(volume)<.25 and min(size)<.05 and max(size)<20,'Unexpected separate structural component'
            debris.extend(c)
        bmesh.ops.delete(bm,geom=debris,context='VERTS')
        print('REMOVED_SUB_RESOLUTION_BOOLEAN_SLIVERS',len(components)-1,flush=True)
        parts=[len(components[0])];bad=sum(not e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True)
    result={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':bad,'connected_components':len(parts),'volume_mm3':vol}
    print('MESH_CHECK',o.name,json.dumps(result),flush=True)
    assert bad==0 and len(parts)==1 and vol>1000,(o.name,result)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    # A few sub-micron Boolean slivers at the knife trim become collinear after
    # float32 STL rotation. Collapse only short edges satisfying the manifold
    # link condition, so both print orientations retain the same solid surface.
    if '小型集風罩' in o.name:
        repaired=0
        for _ in range(100):
            tiny=[f for f in bm.faces if f.calc_area()<1e-7]
            if not tiny:break
            chosen=None
            for f in tiny:
                for e in sorted(f.edges,key=lambda e:e.calc_length()):
                    if e.calc_length()>.002:continue
                    a,b=e.verts
                    na={q.other_vert(a) for q in a.link_edges};nb={q.other_vert(b) for q in b.link_edges}
                    if len(na&nb)==2:chosen=e;break
                if chosen:break
            if chosen is None:
                print('REMAINING_THIN_FACES',[(f.calc_area(),min(e.calc_length() for e in f.edges)) for f in tiny],flush=True)
                break
            bmesh.ops.collapse(bm,edges=[chosen],uvs=False);repaired+=1
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        print('SHORT_EDGE_COLLAPSES',repaired,flush=True)
    post_bad=sum(not e.is_manifold for e in bm.edges)
    print('TRIANGULATED_BAD_EDGES',o.name,post_bad,flush=True)
    assert post_bad==0,'Triangulation introduced a nonmanifold diagonal'
    bm.to_mesh(o.data);bm.free()
    for p in o.data.polygons:p.use_smooth=True
    if hasattr(o.data,'set_sharp_from_angle'):o.data.set_sharp_from_angle(angle=math.radians(35))
    return result
def BVH(o):
    o.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)

parts={}
for key in ['右側','左側']:
    info=placements[key];ends=list(map(Vector,info['splitter_ends_local_mm']));dirs=list(map(Vector,info['splitter_directions_local']))
    neck=loft('分流接頭_'+key+'_一體件',[[Vector((x,y,z)) for x,y in rect(86,92,4)] for z in [0,46]])
    flange=loft('暫用_原法蘭',[[Vector((x+2,y,z)) for x,y in rect(118,120,4)] for z in [0,3]])
    boolean(neck,flange)
    voids=[]
    for k,(E,D) in enumerate(zip(ends,dirs)):
        p0=Vector(((k-1)*28,0,40));p1=p0+up*30;p3=E;p2=E-D*32
        ro=[];ri=[];area0=26*88*math.gamma(1+1/8)**2/math.gamma(1+2/8)
        for j in range(49):
            t=j/48;s=S(t);C=bez(p0,p1,p2,p3,t)
            # Rotate the long rectangular section gradually. Following the
            # rapidly changing centerline normal at the root folds an 88-mm
            # section over itself before it has become circular.
            q=up.rotation_difference(up).slerp(up.rotation_difference(D),s)
            n=8-6*s;ratio=(26/88)**(1-s);A=area0+(math.pi*23.3**2-area0)*s
            coeff=math.gamma(1+1/n)**2/math.gamma(1+2/n);w=math.sqrt(A*ratio/coeff);d=math.sqrt(A/ratio/coeff)
            ro.append([C+q@Vector((x,y,0)) for x,y in superpts(w+4,d+4,n)])
            ri.append([C+q@Vector((x,y,0)) for x,y in superpts(w,d,n)])
        # Straight 25-mm hose slip-over spigot, with a small retention bead.
        q=up.rotation_difference(D)
        for z,r in [(2,25.3),(14,25.3),(16,25.6),(18,25.6),(20,25.3),(24,25.3),(25,25.0)]:
            ro.append([E+D*z+q@Vector((r*math.cos(2*math.pi*j/96),r*math.sin(2*math.pi*j/96),0)) for j in range(96)])
            ri.append([E+D*z+q@Vector((23.3*math.cos(2*math.pi*j/96),23.3*math.sin(2*math.pi*j/96),0)) for j in range(96)])
        # Extend lumen past the closed outer cap.
        ri.append([E+D*28+q@Vector((23.3*math.cos(2*math.pi*j/96),23.3*math.sin(2*math.pi*j/96),0)) for j in range(96)])
        branch=loft('暫用_漸變外殼',ro);boolean(neck,branch)
        voids.append(loft('暫用_漸變內部流道',ri,None))
    common=loft('暫用_矩形進風流道',[[Vector((x,y,z)) for x,y in rect(82,88,3)] for z in [-5,44]],None)
    boolean(neck,common,'DIFFERENCE')
    for v in voids:boolean(neck,v,'DIFFERENCE')
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
        hole=cylinder('暫用_法蘭孔',(2+dz,dy,-2),(2+dz,dy,6),3.2 if abs(dy)==51 and abs(dz)==50 else 2.2,48)
        boolean(neck,hole,'DIFFERENCE')
    # Limit rounding to the divider's inlet edges; a global bevel would attack
    # microscopic Boolean edges around every mounting hole.
    bm=bmesh.new();bm.from_mesh(neck.data)
    nose=[e for e in bm.edges if e.is_manifold and all(abs(v.co.z-44)<.001 for v in e.verts)
          and abs(sum(v.co.x for v in e.verts)/2)<40 and abs(sum(v.co.y for v in e.verts)/2)<43
          and e.calc_face_angle(0)>math.radians(50)]
    print('NOSE_EDGES',key,len(nose),flush=True)
    # Retain the exact connected channel boundary. Small Boolean intersection
    # edges do not support a reliable mesh bevel and must not be rounded blindly.
    bm.to_mesh(neck.data);bm.free()
    result=check(neck);tree=BVH(neck)
    assert tree.ray_cast(Vector((0,0,-1)),up,30)[0] is None
    for E,D in zip(ends,dirs):assert tree.ray_cast(E+D*27,-D,30)[0] is None
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
        assert tree.ray_cast(Vector((2+dz,dy,-1)),up,5)[0] is None
    neck['零件']='一體式三路分流接頭';neck['方向']=key;neck['接口淨尺寸_mm']=[82,88];neck['軟管名義內徑_mm']=51
    neck['套管嘴外徑_mm']=50.6;neck['套管嘴流道內徑_mm']=46.6;neck['套入長度_mm']=25
    neck['公差']='按名義51mm軟管設計；購買實品後應先確認套合。';neck['性能']='未做CFD或實測'
    parts[key]={'object':neck.name,'mesh':result,'bounds':bounds(neck)}

# Universal short hood: one identical part can be rigidly placed at all 6 slots.
def integ(x):
    if x<=0:return 0
    if x>=Lc:return Lc-6
    if x<6:
        u=x/6;return 6*(u**3-.5*u**4)
    if x<=Lc-6:return x-3
    u=(x-Lc+6)/6;return Lc-9+6*(u-u**3+.5*u**4)
def hh(r):return 1 if r<=4 else h/2-math.tan(math.radians(7))*integ(Ln-r)
Nu=96;Nv=8
perim=[(i/Nu,-.5) for i in range(Nu)]+[(1,-.5+j/Nv) for j in range(Nv)]+[(1-i/Nu,.5) for i in range(Nu)]+[(0,.5-j/Nv) for j in range(Nv)]
def pt(u,v,r,z,outer=False):
    a=(u-.5)*theta_span
    if outer:a+=2*wall*(u-.5)/(R+r)
    return Vector(((R+r)*math.sin(a),(R+r)*math.cos(a)-(R+rv),z))
def flat(u,v,z,outer):
    a=(u-.5)*theta_span
    if outer:a+=2*wall*(u-.5)/(R+rv)
    return Vector(((R+rv)*math.sin(a)+math.sin(a)*v*(h+(2*wall if outer else 0)),
        (R+rv)*math.cos(a)-(R+rv)+math.cos(a)*v*(h+(2*wall if outer else 0)),z))
ro=[];ri=[]
for z,r in [(-25,25.0),(-24,25.3),(-20,25.3),(-18,25.6),(-16,25.6),(-14,25.3),(0,25.3)]:
    angles=[math.atan2(2*v,2*u-1) for u,v in perim]
    ro.append([Vector((r*math.cos(a),r*math.sin(a),z)) for a in angles]);ri.append([Vector((23.3*math.cos(a),23.3*math.sin(a),z)) for a in angles])
for j in range(1,73):
    t=j/72;s=S(t);z=150*t
    rin=23.3+(25.5-23.3)*S(min(1,z/18));th=2+(wall-2)*S(min(1,z/18))
    ir=[];orr=[]
    for u,v in perim:
        a=math.atan2(2*v,2*u-1)
        p0=Vector((rin*math.cos(a),rin*math.sin(a),z));p1=flat(u,v,z,False)
        q0=Vector(((rin+th)*math.cos(a),(rin+th)*math.sin(a),z));q1=flat(u,v,z,True)
        ir.append(p0*(1-s)+p1*s);orr.append(q0*(1-s)+q1*s)
    ri.append(ir);ro.append(orr)
for j in range(1,7):
    z=150+12*j/6;ri.append([flat(u,v,z,False) for u,v in perim]);ro.append([flat(u,v,z,True) for u,v in perim])
for j in range(1,49):
    angle=math.pi/2*j/48;pair=[]
    for outer in [False,True]:
        ring=[]
        for u,v in perim:
            rad=rb+v*(h+(2*wall if outer else 0));r=Ln+rad*math.cos(angle)
            ring.append(pt(u,v,r,Z-rb-entryZ+rad*math.sin(angle),outer))
        pair.append(ring)
    ri.append(pair[0]);ro.append(pair[1])
for start,end,N in [(Ln,4,60),(4,0,8)]:
    for j in range(1,N+1):
        r=start+(end-start)*j/N
        ri.append([pt(u,v,r,Z-entryZ+2*v*hh(r),False) for u,v in perim])
        ro.append([pt(u,v,r,Z-entryZ+v*(2*hh(r)+2*wall),True) for u,v in perim])
hood=hollow('小型集風罩_共用款_一體件',ro,ri)
def band(zlo,zhi):
    rings=[]
    for j in range(97):
        u=j/96
        rings.append([pt(u,0,r,Z-entryZ+z,False) for r,z in [(0,zlo),(2,zlo),(2,zhi),(0,zhi)]])
    return loft('暫用_風刀面板',rings,lipmat)
boolean(hood,band(1.02,10));boolean(hood,band(-10,-1.02))
result=check(hood);tree=BVH(hood)
assert tree.ray_cast(Vector((0,0,-28)),up,45)[0] is None
gaps=[]
for j in range(1,40):
    u=j/40;center=pt(u,0,1,Z-entryZ,False)
    a=(u-.5)*theta_span;exitdir=Vector((-math.sin(a),-math.cos(a),0))
    hu=tree.ray_cast(center,up,10);hd=tree.ray_cast(center,-up,10)
    assert hu[0] is not None and hd[0] is not None
    gap=hu[3]+hd[3];gaps.append(gap);assert abs(gap-2)<.005,(u,gap)
    assert tree.ray_cast(center,exitdir,8)[0] is None
hood['零件']='通用小型集風罩；單邊3個、整台6個';hood['出風弧長_mm']=span;hood['出風縫_mm']=2
hood['壁厚說明']='主要外殼約2.4mm；套管嘴壁厚2mm';hood['套管嘴外徑_mm']=50.6;hood['套管嘴內徑_mm']=46.6
hood['彎道中心半徑_mm']=28;hood['收縮段最大壁角_deg']=7;hood['性能']='未做CFD或實測'
parts['集風罩']={'object':hood.name,'mesh':result,'bounds':bounds(hood),'slit_gap_mm':[min(gaps),max(gaps)]}
for p in parts.values():assert max(p['bounds']['size'])<300,p

def export(o,name,rot=None):
    M=rot or Matrix.Identity(4);bb=bounds(o,M);M=Matrix.Translation(Vector((0,0,-bb['min'][2])))@M
    o.data.calc_loop_triangles();path=HERE/'STL_毫米'/name
    with path.open('wb') as f:
        f.write(b'Millimetres - single connected print part'.ljust(80,b' '));f.write(struct.pack('<I',len(o.data.loop_triangles)))
        for tri in o.data.loop_triangles:
            a,b,c=[M@o.data.vertices[i].co for i in tri.vertices];normal=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
    return {'file':str(path),'bounds_mm':bounds(o,M),'triangles':len(o.data.loop_triangles),'sha256':digest(path)}
stls=[]
for key in ['右側','左側']:stls.append(export(bpy.data.objects[parts[key]['object']],f'分流接頭_{key}_列印_mm.stl'))
stls.append(export(hood,'小型集風罩_共用款_直立_mm.stl'))
stls.append(export(hood,'小型集風罩_共用款_斜放45度_mm.stl',Matrix.Rotation(math.radians(-45),4,'X')))
for x in stls:assert max(x['bounds_mm']['size'])<300
manifest={'source':str(SOURCE),'source_sha256':source_hash,'original_object_signatures':baseline,'original_units':source_units,
    'parts':parts,'placements':placements,'STL':stls,'cache':str(CACHE),'hose_ID_mm':51,'hose_OD_assumed_mm':55,
    'spigot_OD_mm':50.6,'spigot_ID_mm':46.6,'hose_overlap_mm':23,'universal_hood_arc_mm':span,
    'CFD_executed':False,'performance_validated':False,'print_envelope_mm':[300,300,300]}
assert digest(SOURCE)==source_hash
(HERE/'模型與列印檢查.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(CACHE))
print('PRINT_PARTS_BUILT',json.dumps(parts,ensure_ascii=False),flush=True)
