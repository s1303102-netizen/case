"""Compact, full-profile air-knife test fixture. No CFD or source edits.

Preserves inlet/flange, 2 mm slot, original arc radius, 90-degree bend and
contraction. Shortens the arc and loft; an interchangeable bypass allows
experimental operating-point adjustment, not a claimed resistance match.
All mesh coordinates and STL coordinates are millimetres.
"""
from pathlib import Path
import bpy,bmesh,math,json,hashlib,struct,ast
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
SPEC=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
ARC=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']
protected=[ROOT/'第一版.blend',HERE.parent/'集風罩_單體.blend']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32
collection=bpy.data.collections.new('240mm弧長_原剖面測試罩');scene.collection.children.link(collection)
alts=bpy.data.collections.new('旁通孔片_替換件_每次只裝一片');scene.collection.children.link(alts)

def mat(name,color,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.33
    return m
bodymat=mat('測試罩_藍灰',(0.055,.25,.34),.1)
platemat=mat('旁通孔片_橙色',(.85,.25,.045),.05)
capmat=mat('測壓口封帽',(.12,.15,.18))
def active(obj):
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
def mesh(name,verts,faces,material=bodymat,target=None):
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);(target or collection).objects.link(obj)
    if material:data.materials.append(material)
    return obj
def boolean(obj,tool,operation='UNION',solver='EXACT'):
    bpy.context.view_layer.update();active(obj)
    m=obj.modifiers.new('實體接合' if operation=='UNION' else operation,'BOOLEAN')
    m.solver=solver;m.operation=operation;m.object=tool
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool,do_unlink=True)
def solid_check(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    if any(not e.is_manifold for e in bm.edges):
        print('BOOLEAN_MICRO_EDGES',[(tuple(e.verts[0].co),tuple(e.verts[1].co),len(e.link_faces)) for e in bm.edges if not e.is_manifold][:8],flush=True)
        # Exact Boolean arithmetic still stores float32 coordinates. Weld only
        # sub-micron duplicates, far below the 2 mm slit and print resolution.
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data)
    bad=sum(not e.is_manifold for e in bm.edges)
    volume=bm.calc_volume(signed=True)
    remaining=set(bm.verts);components=0
    while remaining:
        components+=1;stack=[remaining.pop()]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                other=e.other_vert(v)
                if other in remaining:remaining.remove(other);stack.append(other)
    result={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':bad,
            'signed_material_volume_mm3':volume,'material_components':components}
    bm.free();print('MESH_CHECK',obj.name,json.dumps(result),flush=True)
    assert bad==0 and volume>0 and components==1,(obj.name,result)
    return result
def bounds(obj,transform=None):
    matrix=transform if transform is not None else obj.matrix_world
    pts=[matrix@v.co for v in obj.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    return {'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}
def export_stl(obj,name,transform=None,ground=True):
    matrix=transform if transform is not None else Matrix.Identity(4)
    vertices=[matrix@v.co for v in obj.data.vertices]
    lo=Vector(tuple(min(p[i] for p in vertices) for i in range(3))) if ground else Vector((0,0,0))
    vertices=[v-lo for v in vertices];obj.data.calc_loop_triangles()
    path=HERE/(name+'.stl')
    with path.open('wb') as f:
        f.write(b'Compact hood test fixture; millimetres; geometry checked'.ljust(80,b' '))
        f.write(struct.pack('<I',len(obj.data.loop_triangles)))
        for t in obj.data.loop_triangles:
            a,b,c=[vertices[i] for i in t.vertices];n=(b-a).cross(c-a).normalized()
            f.write(struct.pack('<12fH',*n,*a,*b,*c,0))
    size=[max(v[i] for v in vertices)-min(v[i] for v in vertices) for i in range(3)]
    assert max(size)<290,('Print envelope too large',name,size)
    return {'file':str(path),'size_mm':size,'triangles':len(obj.data.loop_triangles),'grounded':ground}

R=ARC['fitted_arc_radius_mm'];L=240.0;halfangle=L/(2*R)
h=SPEC['pre_nozzle_height_mm'];rb=SPEC['bend']['mean_radius_mm']
Lc=SPEC['nozzle']['converging_length_mm'];Ln=SPEC['nozzle']['total_length_mm']
rv=Ln+rb;neckend=50.;loftend=185.;bendZ=240.;slotZ=bendZ+rb
gap=2.;wall=2.;Nu=121;Nv=4
def S(t):return 10*t**3-15*t**4+6*t**5
def integral(x):
    b=6.
    if x<=0:return 0.
    if x>=Lc:return Lc-b
    if x<b:
        t=x/b;return b*(t**3-.5*t**4)
    if x<=Lc-b:return x-b/2
    t=(x-Lc+b)/b;return Lc-1.5*b+b*(t-t**3+.5*t**4)
def hh(r):return 1. if r<=4 else h/2-math.tan(math.radians(7))*integral(Ln-r)
def arc(u,r):
    a=(2*u-1)*halfangle
    return Vector(((R+r)*math.sin(a),(R+rv)-(R+r)*math.cos(a),0))
def center(u,lam):return Vector(((u-.5)*82,0,0))*(1-lam)+arc(u,rv)*lam
def span(lam):
    pts=[center(i/400,lam) for i in range(401)]
    return sum((b-a).length for a,b in zip(pts,pts[1:]))
toparea=span(1)*h
stations=[('neck',0)]
for part,n in [('neck',6),('loft',54),('straight',12),('bend',40),('nozzle',48),('lip',8)]:
    stations.extend((part,j/n) for j in range(1,n+1))
span_cache={k:span(S(t)) for k,(part,t) in enumerate(stations) if part=='loft'}
def point(u,v,k):
    part,t=stations[k];a=(2*u-1)*halfangle
    if part=='neck':p=center(u,0);out=Vector((0,-1,0));d=88.;z=neckend*t
    elif part=='loft':
        lam=S(t);p=center(u,lam);d=(7216+(toparea-7216)*lam)/span_cache[k]
        dux=(1-lam)*82+lam*(R+rv)*math.cos(a)*2*halfangle
        duy=lam*(R+rv)*math.sin(a)*2*halfangle
        out=Vector((duy,-dux,0)).normalized();z=neckend+(loftend-neckend)*t
    elif part=='straight':
        p=arc(u,rv);out=Vector((math.sin(a),-math.cos(a),0));d=h;z=loftend+55*t
    elif part=='bend':
        alpha=math.pi/2*t;r=Ln+(rb+v*h)*math.cos(alpha)
        p=arc(u,r);p.z=bendZ+(rb+v*h)*math.sin(alpha);return p
    else:
        r=Ln-Lc*t if part=='nozzle' else 4*(1-t)
        p=arc(u,r);p.z=slotZ+v*2*hh(r);return p
    p+=out*(v*d);p.z=z;return p
perimeter=[(i/Nu,-.5) for i in range(Nu)]+[(1,-.5+j/Nv) for j in range(Nv)]
perimeter +=[(1-i/Nu,.5) for i in range(Nu)]+[(0,.5-j/Nv) for j in range(Nv)]
nr=len(perimeter)
verts=[tuple(point(u,v,k)) for k in range(len(stations)) for u,v in perimeter]
faces=[(k*nr+j,k*nr+(j+1)%nr,(k+1)*nr+(j+1)%nr,(k+1)*nr+j)
       for k in range(len(stations)-1) for j in range(nr)]
body=mesh('測試集風罩_240mm弧長_本體',verts,faces)
# The first v=-0.5 wall is on the +Y side of the intake.
if body.data.polygons[0].normal.y<0:
    bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
active(body);m=body.modifiers.new('保持流道尺寸_向外加厚2mm','SOLIDIFY')
m.thickness=2.;m.offset=1;m.use_even_offset=True;m.use_quality_normals=True;m.use_rim=True
bpy.ops.object.modifier_apply(modifier=m.name)
solid_check(body)
def rect(w,h,r,offset=(0,0),steps=10):
    result=[]
    for x,y,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for j in range(steps+1):
            t=math.radians(a+90*j/steps);result.append((offset[0]+x+r*math.cos(t),offset[1]+y+r*math.sin(t)))
    return result
def prism(name,profile,low,high,axis='Z',material=bodymat,target=None):
    def pos(x,y,z):return (x,y,z) if axis=='Z' else ((x,z,y) if axis=='Y' else (z,x,y))
    vs=[pos(x,y,z) for z in (low,high) for x,y in profile];n=len(profile)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,vs,fs,material,target)
def cylinder(name,r,low,high,axis='Z',offset=(0,0),material=bodymat,target=None,n=96):
    prof=[(offset[0]+r*math.cos(math.tau*j/n),offset[1]+r*math.sin(math.tau*j/n)) for j in range(n)]
    return prism(name,prof,low,high,axis,material,target)
def cube(name,lo,hi):
    vs=[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
    return mesh(name,vs,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)])

# Exact original interface: nominal 82x88 opening, 118x120 flange,
# flange centre +2 mm in X, original hole pattern and diameters.
flange=prism('118x120原尺寸接口法蘭',rect(118,120,4,(2,0)),0,3)
boolean(flange,prism('進風淨孔',rect(82,88,3),-3,6),'DIFFERENCE')
holes=[(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
for dy,dz in holes:
    r=3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
    boolean(flange,cylinder('原尺寸法蘭孔',r,-3,6,offset=(2+dz,dy)),'DIFFERENCE')
boolean(body,flange);solid_check(body)
def front_band(name,zlo,zhi):
    vs=[]
    for i in range(Nu+1):
        for r,z in [(0,zlo),(2,zlo),(2,zhi),(0,zhi)]:
            p=arc(i/Nu,r);p.z=slotZ+z;vs.append(tuple(p))
    fs=[]
    for i in range(Nu):
        for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    fs.extend([(3,2,1,0),tuple(4*Nu+j for j in range(4))])
    return mesh(name,vs,fs)
boolean(body,front_band('上刀口面板',1.02,10));boolean(body,front_band('下刀口面板',-10,-1.02))
solid_check(body)
# Rearward bypass keeps its jet away from the measured forward air knife.
boolean(body,cylinder('旁通接管外壁',25,-89.5,-40,'Y',(0,38)))
boolean(body,prism('旁通孔片固定座',rect(64,64,5,(0,38)),-90,-86,'Y'))
boolean(body,cylinder('旁通淨孔44mm',22,-96,-37,'Y',(0,38)),'DIFFERENCE')
for x in [-25,25]:
    for z in [13,63]:boolean(body,cylinder('旁通M3通孔',1.7,-92,-84,'Y',(x,z),n=48),'DIFFERENCE')
solid_check(body)
# External joining lugs allow a split body to be screwed and sealed together.
join_positions=[(51.,20.),(-h/2-7,200.),(h/2+7,230.)]
for y,z in join_positions:
    boolean(body,cube('半片對合外螺絲座',(-8,y-6,z-6),(8,y+6,z+6)))
    boolean(body,cylinder('半片對合M3通孔',1.7,-10,10,'X',(y,z),n=48),'DIFFERENCE')
# Static pressure pickup 25 mm before the bend; capped if not instrumented.
boolean(body,cylinder('測壓口外徑6mm',3,-22,-7,'Y',(0,215),n=64))
boolean(body,cylinder('測壓孔內徑3mm',1.5,-24,-3,'Y',(0,215),n=64),'DIFFERENCE')
# Second pickup on the unchanged intake neck, before the bypass branches off.
# It allows inlet static pressure and pre-bend pressure to be logged separately.
boolean(body,cylinder('入口測壓口外徑6mm',3,45,63,'Y',(25,10),n=64))
boolean(body,cylinder('入口測壓孔內徑3mm',1.5,40,65,'Y',(25,10),n=64),'DIFFERENCE')
body_check=solid_check(body)
# Triangulate Boolean-generated nonplanar n-gons before splitting and STL
# export; the printable representation is checked as triangles as well.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(body.data);bm.free();body_check=solid_check(body)
for p in body.data.polygons:p.use_smooth=True
if hasattr(body.data,'set_sharp_from_angle'):body.data.set_sharp_from_angle(angle=math.radians(32))
body['尺寸單位']='mm';body['出風縫_mm']=2.;body['有效弧長_mm']=240.;body['主壁厚_mm']=2.
body['彎角_deg']=90.;body['彎頭中心半徑_mm']=rb;body['原接口淨口_mm']=[82.,88.]
body['原法蘭外框_mm']=[118.,120.,3.];body['性能狀態']='原剖面測試段；旁通需量測校準，未宣稱等阻力或同風速'

files=[];files.append(export_stl(body,'01_集風罩本體_整件_mm'))
plate_objects=[];plate_checks={}
for d in [0,28,32,36,38,40,44]:
    name='旁通孔片_'+('全封閉' if d==0 else '孔徑'+str(d)+'mm')
    plate=prism(name,rect(64,64,5),0,3,material=platemat,target=alts)
    if d:boolean(plate,cylinder('孔片中心孔',d/2,-2,5),'DIFFERENCE')
    for x in [-25,25]:
        for y in [-25,25]:boolean(plate,cylinder('孔片M3通孔',1.7,-2,5,offset=(x,y),n=48),'DIFFERENCE')
    plate_checks[str(d)]=solid_check(plate)
    files.append(export_stl(plate,'03_旁通孔片_'+('00_封閉' if d==0 else str(d)+'mm')))
    plate['孔徑_mm']=d;plate['用途']='每次只安裝一片；直徑38mm為粗估起點，須實測調整'
    plate.matrix_world=Matrix.Translation((0,-90.3,38))@Matrix.Rotation(math.pi/2,4,'X')
    plate.hide_render=(d!=38);plate.hide_set(d!=38);plate_objects.append(plate)
cap=cylinder('測壓口封帽_內徑6.4mm',5,0,14,material=capmat)
boolean(cap,cylinder('封帽內孔',3.2,-1,12),'DIFFERENCE');solid_check(cap)
files.append(export_stl(cap,'04_測壓口封帽_平底朝下_mm',Matrix.Rotation(math.pi,4,'X')))
cap.matrix_world=Matrix.Translation((0,-11,215))@Matrix.Rotation(math.pi/2,4,'X')
inlet_cap=bpy.data.objects.new('入口測壓口封帽_內徑6.4mm',cap.data)
collection.objects.link(inlet_cap)
inlet_cap.matrix_world=Matrix.Translation((25,52,10))@Matrix.Rotation(-math.pi/2,4,'X')

# A copy for each printable half. Boolean intersection caps the material
# correctly around through-holes; it does not cap the internal air passage.
parts_collection=bpy.data.collections.new('列印左右半片_組裝時改看本體');scene.collection.children.link(parts_collection)
part_checks={}
for isleft in [True,False]:
    label='左半片' if isleft else '右半片'
    obj=bpy.data.objects.new('列印用_'+label,body.data.copy());parts_collection.objects.link(obj)
    lo=(-200,-200,-20) if isleft else (0,-200,-20)
    hi=(0,200,310) if isleft else (200,200,310)
    boolean(obj,cube('分割界限',lo,hi),'INTERSECT',solver='MANIFOLD')
    part_checks[label]=solid_check(obj)
    orientation=Matrix.Rotation(math.pi/2 if isleft else -math.pi/2,4,'Y')
    files.append(export_stl(obj,'02_本體'+label+'_切面朝下_mm',orientation))
    obj['列印姿態']='使用STL已排成中心切面朝下；組合接縫用膠及M3螺絲密封'
    obj.hide_render=True;obj.hide_set(True)

# Slit/inlet/bypass/pressure-tap geometric checks, not a flow simulation.
body.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],
                        [tuple(t.vertices) for t in body.data.loop_triangles],all_triangles=True)
gaps=[]
for i in range(1,40):
    u=i/40;a=(2*u-1)*halfangle;p=arc(u,2);p.z=slotZ
    up=tree.ray_cast(p,Vector((0,0,1)),10);down=tree.ray_cast(p,Vector((0,0,-1)),10)
    assert up[0] is not None and down[0] is not None
    gaps.append(up[3]+down[3]);assert abs(gaps[-1]-2)<.003,gaps[-1]
    assert tree.ray_cast(p,Vector((-math.sin(a),math.cos(a),0)),10)[0] is None
assert tree.ray_cast(Vector((0,0,20)),Vector((0,0,-1)),30)[0] is None
assert tree.ray_cast(Vector((0,-40,38)),Vector((0,-1,0)),60)[0] is None
assert tree.ray_cast(Vector((0,-4,215)),Vector((0,-1,0)),25)[0] is None
assert tree.ray_cast(Vector((25,40,10)),Vector((0,1,0)),28)[0] is None
# Aperture dimensions on the unmodified first 3 mm remain 82x88 centrally.
inlet_width=[]
for origin,direction in [(Vector((0,0,1.5)),Vector((1,0,0))),
                         (Vector((0,0,1.5)),Vector((-1,0,0))),
                         (Vector((0,0,1.5)),Vector((0,1,0))),
                         (Vector((0,0,1.5)),Vector((0,-1,0)))]:
    hit=tree.ray_cast(origin,direction,70);assert hit[0] is not None;inlet_width.append(hit[3])
assert abs(inlet_width[0]+inlet_width[1]-82)<.005
assert abs(inlet_width[2]+inlet_width[3]-88)<.005

bodybounds=bounds(body);assembly_objs=[body,cap,inlet_cap]+[o for o in plate_objects if o['孔徑_mm']==38]
bpy.context.view_layer.update();bb=[bounds(o) for o in assembly_objs]
assembly_size=[max(q['max'][i] for q in bb)-min(q['min'][i] for q in bb) for i in range(3)]
assert max(assembly_size)<290,assembly_size
fraction=L/SPEC['slot_span_mm'];A0=SPEC['slot_span_mm']*2;A1=L*2
q0=A0*25*60/1e6;q1=A1*25*60/1e6
report={'model_type':'compact full-profile test coupon with calibrated bypass',
        'mesh_coordinates_unit':'mm','print_limit_mm':[300,300,300],
        'body_bounds_mm':bodybounds,'assembled_size_mm':assembly_size,
        'full_body_mesh':body_check,'print_half_meshes':part_checks,'bypass_plate_meshes':plate_checks,
        'slit_gap_mm':[min(gaps),max(gaps)],'slit_sample_count':len(gaps),
        'measured_intake_mm':[sum(inlet_width[:2]),sum(inlet_width[2:])],
        'preserved':{'inlet_nominal_mm':[82,88],'flange_mm':[118,120,3],
                     'flange_center_offset_mm':[2,0],'mount_holes':holes,
                     'slot_height_mm':2,'arc_radius_mm':R,'turn_degrees':90,
                     'bend_center_radius_mm':rb,'pre_nozzle_height_mm':h,
                     'contraction_length_mm':Lc,'straight_lip_mm':4,'nozzle_max_wall_angle_deg':7,
                     'bend_approach_straight_mm':55},
        'changed':{'slot_arc_mm':[SPEC['slot_span_mm'],L],
                   'loft_height_mm':[SPEC['loft_stations'][-1]['Z_mm']-SPEC['loft_stations'][0]['Z_mm'],135],
                   'inlet_straight_mm':[50,50],'upstream_arc_mm':span(1),
                   'bypass_bore_mm':44,'bypass_plate_options_mm':[0,28,32,36,38,40,44]},
        'pressure_taps':{'bore_mm':3,'hose_connection_OD_mm':6,
                         'inlet_neck_port_center_mm':[25,44,10],
                         'pre_bend_port_center_mm':[0,-h/2,215],
                         'pre_bend_tap_distance_before_bend_mm':25,
                         'caps_to_print':2,'inlet_tap_before_bypass_split':True,
                         'pickups_flush_to_inner_wall_no_protruding_tubes':True},
        'conditional_sizing_at_25_m_s':{'original_slot_area_mm2':A0,'test_slot_area_mm2':A1,
                                     'span_ratio':fraction,'original_flow_m3_min':q0,
                                     'main_test_flow_m3_min':q1,'missing_flow_for_bypass_m3_min':q0-q1,
                                     'area_ratio_if_bypass_closed':A0/A1,
                                     'ideal_fixed_Q_slot_pressure_ratio_if_bypass_closed':(A0/A1)**2,
                                     'bypass_start_plate_mm':38,'bypass_start_is_unvalidated':True,
                                     'assumed_kinematic_viscosity_m2_s':1.5e-5,
                                     'Re_gap_at_25m_s':25*.002/1.5e-5,
                                     'Re_gap_same_as_original_at_same_velocity':True},
        'claims':{'CFD_executed':False,'resistance_match_verified':False,'velocity_match_verified':False,
                  'full_span_uniformity_represented':False,'inlet_outlet_and_bypass_geometrically_open':True},
        'original_file_hashes':hashes,'files':files}
for p in protected:assert hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p)]
for obj in bpy.context.selected_objects:obj.select_set(False)
body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.region_3d.view_location=(0,5,140)
            space.region_3d.view_distance=510;space.region_3d.view_rotation=Vector((1.3,1.8,.7)).to_track_quat('Z','Y')
            space.shading.type='MATERIAL';space.clip_end=10000
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'30cm測試集風罩_組裝.blend'))
report['blend_file']=str(HERE/'30cm測試集風罩_組裝.blend')
(HERE/'尺寸與幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPACT_HOOD_SAVED',json.dumps({'size':assembly_size,'gap':report['slit_gap_mm'],'files':len(files)}),flush=True)

# Preview uses metre-sized temporary copies; the printable blend stays in mm.
tree_ast=ast.parse((HERE.parent/'blender_build_right_hood.py').read_text())
helpers=ast.Module(body=[n for n in tree_ast.body if isinstance(n,ast.FunctionDef) and n.name in {'look','preview'}],type_ignores=[])
exec(compile(helpers,'preview_helpers','exec'))
original_scene=scene
preview(assembly_objs,.001,(.52,.65,.42),(0,.005,.145),.39,'測試集風罩_正面預覽.png')
preview(assembly_objs,.001,(.48,-.65,.36),(0,-.005,.145),.40,'測試集風罩_旁通側預覽.png')
print('COMPACT_HOOD_COMPLETE',flush=True)
