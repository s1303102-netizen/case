"""Single-piece straight rectangular-to-long-slot diagnostic nozzles, millimetres."""
from pathlib import Path
from array import array
import bpy,bmesh,math,json,hashlib,struct,ast
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
W=216.;H=240.;NECK=12.;TRANSITION=216.;LIP=12.;WALL=2.;N=256
assert NECK+TRANSITION+LIP==H
protected=[p for p in [ROOT/'第一版.blend',ROOT/'完整模型.blend'] if p.exists()]
hashfile=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
hashes={str(p):hashfile(p) for p in protected}
def ease(t):
    b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def rect(w,d,r=3,cx=0,cy=0,n=N):
    pts=[];a=w/2;b=d/2
    for i in range(n):
        angle=2*math.pi*i/n;c=math.cos(angle);s=math.sin(angle);m=max(abs(c),abs(s))
        x=a*c/m;y=b*s/m
        if r>1e-8 and abs(x)>a-r and abs(y)>b-r:
            A=x*x+y*y;B=-2*(abs(x)*(a-r)+abs(y)*(b-r));C=(a-r)**2+(b-r)**2-r*r
            t=(-B+math.sqrt(max(0,B*B-4*A*C)))/(2*A);x*=t;y*=t
        pts.append(Vector((cx+x,cy+y,0)))
    return pts
def mesh(name,v,f,mat=None):
    d=bpy.data.meshes.new(name+'_Mesh');d.from_pydata(v,[],f);d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o)
    if mat:d.materials.append(mat)
    return o
def loft(name,rings,mat=None):
    n=len(rings[0]);verts=[p for ring in rings for p in ring];faces=[]
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
    return mesh(name,verts,faces,mat)
def solid_surface(outer,inner,mat):
    n=len(outer[0]);verts=[];faces=[]
    for ro,ri in zip(outer,inner):verts.extend(ro);verts.extend(ri)
    for j in range(len(outer)-1):
        for i in range(n):
            a=j*n*2+i;b=j*n*2+(i+1)%n
            faces.extend([(a,b,b+n*2,a+n*2),(b+n,a+n,a+n*3,b+n*3)])
    for j in [0,len(outer)-1]:
        for i in range(n):
            a=j*n*2+i;b=j*n*2+(i+1)%n;faces.append((a,a+n,b+n,b))
    return mesh('直通長型風刀_完整件',verts,faces,mat)
def boolean(o,cutter,operation):
    for q in bpy.context.selected_objects:q.select_set(False)
    o.select_set(True);bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('接口實體與孔','BOOLEAN');m.operation=operation;m.solver='EXACT';m.object=cutter
    bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)
def material():
    m=bpy.data.materials.new('風刀_藍灰');m.diffuse_color=(.06,.24,.32,1);m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.06,.24,.32,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.38
    return m
def dims(o):
    p=[v.co for v in o.data.vertices];lo=[min(v[i] for v in p) for i in range(3)];hi=[max(v[i] for v in p) for i in range(3)]
    return {'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}
def polygon_area(p):return abs(sum(a.x*b.y-a.y*b.x for a,b in zip(p,p[1:]+p[:1])))/2
def geohash(o):
    h=hashlib.sha256();a=array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    a=array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',a);h.update(a.tobytes());return h.hexdigest()
def verify_mesh(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bad=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True)
    todo=set(bm.verts);count=0
    while todo:
        count+=1;stack=[todo.pop()]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                u=e.other_vert(v)
                if u in todo:todo.remove(u);stack.append(u)
    assert bad==0 and count==1 and volume>1000,(bad,count,volume)
    bm.to_mesh(o.data);bm.free()
    for p in o.data.polygons:p.use_smooth=True
    if hasattr(o.data,'set_sharp_from_angle'):o.data.set_sharp_from_angle(angle=math.radians(32))
    return {'nonmanifold_edges':bad,'material_components':count,'volume_mm3':volume,
        'vertices':len(o.data.vertices),'triangles':len(o.data.polygons)}
def bvh(o):
    o.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def export_stl(o,path):
    o.data.calc_loop_triangles()
    with path.open('wb') as f:
        f.write(b'Straight slot test nozzle, millimetres, one piece'.ljust(80,b' '));f.write(struct.pack('<I',len(o.data.loop_triangles)))
        for t in o.data.loop_triangles:
            a,b,c=[o.data.vertices[i].co for i in t.vertices];n=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*n,*a,*b,*c,0))
report={'date':'2026-11-01','net_slot_length_mm':W,'total_height_mm':H,'neck_mm':NECK,
    'transition_mm':TRANSITION,'terminal_straight_mm':LIP,'nominal_cross_section_wall_mm':WALL,
    'input_file_hashes':hashes,'variants':[],'flow_direction':'+Z, straight through',
    'CFD_executed':False,'pressure_flow_or_print_validated':False}
for gap in [2,4,6]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=.001;s.unit_settings.length_unit='MILLIMETERS'
    mat=material();B=max((W-82)*88/82+2,1.5*(88-gap));C=B-88+gap
    outer=[];inner=[];stations=[]
    for z in [0,3,NECK]:stations.append((z,0))
    stations.extend((NECK+TRANSITION*j/120,ease(j/120)) for j in range(1,121))
    stations.append((H,1))
    sections=[]
    for z,t in stations:
        w=82+(W-82)*t;d=88-B*t+C*t*t;r0=3*(1-t)
        ri=[p+Vector((0,0,z)) for p in rect(w,d,r0)]
        ro=[p+Vector((0,0,z)) for p in rect(w+2*WALL,d+2*WALL,r0+WALL)]
        inner.append(ri);outer.append(ro);sections.append({'z_mm':z,'lambda':t,'inner_width_mm':w,'inner_depth_mm':d,'area_mm2':polygon_area(ri)})
    changes=[b['area_mm2']-a['area_mm2'] for a,b in zip(sections,sections[1:])]
    assert max(changes)<.002,'Cross-section area expands unexpectedly'
    maxangle=0
    for ra,rb in zip(inner,inner[1:]):
        for a,b in zip(ra,rb):
            dz=b.z-a.z
            if dz>1e-6:maxangle=max(maxangle,math.degrees(math.atan(math.hypot(b.x-a.x,b.y-a.y)/dz)))
    assert maxangle<35
    o=solid_surface(outer,inner,mat)
    fl=loft('暫用_原法蘭',[[p+Vector((0,0,z)) for p in rect(118,120,4,cx=2)] for z in [0,3]],mat)
    boolean(o,fl,'UNION')
    cut=loft('暫用_原進風淨口',[[p+Vector((0,0,z)) for p in rect(82,88,3)] for z in [-2,4]])
    boolean(o,cut,'DIFFERENCE')
    holes=[(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
    for dy,dz in holes:
        rr=3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
        circles=[[Vector((2+dz+rr*math.cos(2*math.pi*j/64),dy+rr*math.sin(2*math.pi*j/64),z)) for j in range(64)] for z in [-1,5]]
        boolean(o,loft('暫用_原安裝孔',circles),'DIFFERENCE')
    o.name=f'直通長型風刀_216x{gap}mm_單件'
    check=verify_mesh(o);bounds=dims(o)
    assert bounds['size'][0]<=220.0001 and bounds['size'][2]<=250 and abs(bounds['min'][2])<1e-4
    assert abs(bounds['size'][0]-220)<.0001 and abs(bounds['max'][2]-H)<.0001
    o['淨出風長_mm']=W;o['出風縫_mm']=gap;o['最大外寬_mm']=220;o['高度_mm']=H
    o['進風淨口_mm']=[82,88];o['法蘭_mm']=[118,120,3];o['主壁厚_mm']=WALL
    o['風向']='向上直通 +Z；不含90度彎道';o['出口']='直線狹縫在最高處、最寬處，無額外內縮'
    o['列印']='單件中空，毫米100%；無測壓孔、旁通或內部分隔板'
    o['性能']='測試候選件；未做CFD或實際壓損及風速量測'
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_location=(0,0,H/2);a.spaces.active.region_3d.view_distance=480
                a.spaces.active.region_3d.view_rotation=Vector((1.3,-1.8,.9)).to_track_quat('Z','Y')
                a.spaces.active.shading.type='MATERIAL';a.spaces.active.clip_end=10000
    for obj in bpy.context.selected_objects:obj.select_set(False)
    o.select_set(True);bpy.context.view_layer.objects.active=o
    blend=HERE/f'直通風刀_216x{gap}mm.blend';stl=HERE/'STL_毫米'/f'直通風刀_216x{gap}mm_單件_mm.stl'
    expected=geohash(o);bpy.ops.wm.save_as_mainfile(filepath=str(blend));export_stl(o,stl)
    bpy.ops.wm.open_mainfile(filepath=str(blend));assert len(bpy.data.objects)==1
    o=next(iter(bpy.data.objects));assert geohash(o)==expected;tree=bvh(o)
    assert tree.ray_cast(Vector((0,0,-1)),Vector((0,0,1)),H+2)[0] is None
    slit=[]
    for x in [-W/2+.5]+[-W/2+W*j/40 for j in range(1,40)]+[W/2-.5]:
        p=Vector((x,0,H-.5));a=tree.ray_cast(p,Vector((0,1,0)),10);b=tree.ray_cast(p,Vector((0,-1,0)),10)
        assert a[0] is not None and b[0] is not None
        slit.append(a[3]+b[3]);assert abs(slit[-1]-gap)<.005
        assert tree.ray_cast(p,Vector((0,0,1)),2)[0] is None
    # No inset: full-length opening exists at maximum Z and at the final maximum width.
    for dy,dz in holes:assert tree.ray_cast(Vector((2+dz,dy,-1)),Vector((0,0,1)),5)[0] is None
    record={'gap_mm':gap,'net_slot_length_mm':W,'outlet_area_mm2':W*gap,'bounds_mm':bounds,
        'blend':str(blend),'STL':str(stl),'blend_sha256':hashfile(blend),'STL_sha256':hashfile(stl),
        'mesh':check,'saved_blend_reopened':True,'slot_gap_sample_range_mm':[min(slit),max(slit)],
        'slot_sampling_count':len(slit),'all_slot_paths_clear':True,'full_straight_center_path_clear':True,
        'all_12_mount_holes_clear':True,'outlet_at_top_and_maximum_width':True,
        'maximum_sampled_wall_path_angle_from_vertical_deg':maxangle,'area_monotonically_nonincreasing':True,
        'depth_polynomial_coefficients':[88,-B,C],'sections':sections}
    report['variants'].append(record)
    print('STRAIGHT_NOZZLE_COMPLETE',json.dumps({k:record[k] for k in ['gap_mm','bounds_mm','mesh','maximum_sampled_wall_path_angle_from_vertical_deg']},ensure_ascii=False),flush=True)
for p,h in hashes.items():assert hashfile(p)==h
report['original_models_unchanged']=True
(HERE/'尺寸與流道檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('ALL_STRAIGHT_NOZZLES_SAVED_AND_VERIFIED',flush=True)
