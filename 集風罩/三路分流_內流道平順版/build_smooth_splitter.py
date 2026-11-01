"""Build a continuous rectangular-root splitter and analytically rounded thin noses."""
from pathlib import Path
import bpy,bmesh,math,json,hashlib,ast,struct
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
OLD=HERE.parent/'三路分流_共用接頭修正版'
spec=json.loads((HERE.parent/'三路分流_正式模型/模型與列印檢查.json').read_text())
tree=ast.parse((HERE.parent/'三路分流_正式模型/build_print_parts.py').read_text())
names={'material','active','mesh','loft','rect','S','bez','cylinder','boolean','bounds','check','BVH','export'}
bodymat=None
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'geometry_helpers','exec'))
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs={str(p):digest(p) for p in [ROOT/'第一版.blend']+sorted(OLD.glob('*.blend'))}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
scene.unit_settings.length_unit='MILLIMETERS';up=Vector((0,0,1))
bodymat=material('平順接頭_藍灰',(.06,.24,.32))

def rect(w,d,r=3,N=12):
    # Include BOTH arc endpoints, so every adjoining straight wall is exactly
    # planar; omitting an endpoint makes the long side subtly slant inward.
    out=[]
    for x,y,a in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
        for j in range(N+1):
            t=math.radians(a+90*j/N);out.append((x+r*math.cos(t),y+r*math.sin(t)))
    return out

def root_loop(xmin,xmax,ymin,ymax,radii,N=256):
    """Ray intersections with a rectangle with independently rounded corners.
    Corner radii order: top-right, top-left, bottom-left, bottom-right.
    Internal divider corners are exactly square, outside corners match the R3 inlet.
    """
    a=(xmax-xmin)/2;b=(ymax-ymin)/2;cx=(xmin+xmax)/2;cy=(ymin+ymax)/2
    out=[]
    for j in range(N):
        angle=2*math.pi*j/N;c=math.cos(angle);s=math.sin(angle);m=max(abs(c),abs(s))
        x=a*c/m;y=b*s/m;idx=0 if x>=0 and y>=0 else 1 if x<0<=y else 2 if x<0 and y<0 else 3
        r=radii[idx]
        if r and abs(x)>a-r and abs(y)>b-r:
            aa=x*x+y*y;bb=-2*(abs(x)*(a-r)+abs(y)*(b-r))
            cc=(a-r)**2+(b-r)**2-r*r
            factor=(-bb+math.sqrt(max(0,bb*bb-4*aa*cc)))/(2*aa)
            x*=factor;y*=factor
        out.append(Vector((cx+x,cy+y,0)))
    return out
def poly_area(p):return abs(sum(a.x*b.y-b.x*a.y for a,b in zip(p,p[1:]+p[:1])))/2
def extrude_xz(name,outline,y0=-45,y1=45):
    n=len(outline);verts=[(x,y,z) for y in [y0,y1] for x,z in outline]
    faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,verts,faces)

# Preserve the blower flange, rectangular throat, and all three hose interfaces.
o=loft('分流接頭_左右共用_內流道平順版',[[Vector((x,y,z)) for x,y in rect(86,92,4)] for z in [0,46]])
flange=loft('暫用_原規格法蘭',[[Vector((x+2,y,z)) for x,y in rect(118,120,4)] for z in [0,3]])
boolean(o,flange)
info=spec['placements']['右側'];ends=list(map(Vector,info['splitter_ends_local_mm']));dirs=list(map(Vector,info['splitter_directions_local']))
voids=[];path_records=[]
for k,(E,D) in enumerate(zip(ends,dirs)):
    xmin,xmax=[(-41,-15),(-13,13),(15,41)][k]
    radii=[(0,3,3,0),(0,0,0,0),(3,0,0,3)][k]
    base=root_loop(xmin,xmax,-44,44,radii)
    center=Vector(((xmin+xmax)/2,0,0));local=[p-center for p in base]
    outerbase=root_loop(xmin-2,xmax+2,-46,46,[r+2 for r in radii])
    outerlocal=[p-center for p in outerbase]
    area0=poly_area(local)
    p0=Vector(((k-1)*28,0,40));p1=p0+up*30;p2=E-D*32
    ro=[[Vector((p.x,p.y,38)) for p in outerbase]]
    ri=[[Vector((p.x,p.y,38)) for p in base]]
    for j in range(81):
        t=j/80;s=S(t);C=bez(p0,p1,p2,E,t)
        q=up.rotation_difference(up).slerp(up.rotation_difference(D),s)
        pi=[];po=[]
        for i in range(len(local)):
            a=2*math.pi*i/len(local);circle=Vector((math.cos(a),math.sin(a),0))
            pi.append(local[i]*(1-s)+circle*23.3*s)
            po.append(outerlocal[i]*(1-s)+circle*25.3*s)
        circle_area=len(local)*23.3**2*math.sin(2*math.pi/len(local))/2
        target_area=area0+(circle_area-area0)*s
        factor=math.sqrt(target_area/poly_area(pi))
        # Apply identical scale to both loops to retain the same smoothly changing wall.
        ro.append([C+q@(p*factor) for p in po]);ri.append([C+q@(p*factor) for p in pi])
    q=up.rotation_difference(D);N=len(local)
    for z,r in [(2,25.3),(14,25.3),(16,25.6),(18,25.6),(20,25.3),(24,25.3),(25,25.0)]:
        ro.append([E+D*z+q@Vector((r*math.cos(2*math.pi*j/N),r*math.sin(2*math.pi*j/N),0)) for j in range(N)])
        ri.append([E+D*z+q@Vector((23.3*math.cos(2*math.pi*j/N),23.3*math.sin(2*math.pi*j/N),0)) for j in range(N)])
    ri.append([E+D*28+q@Vector((23.3*math.cos(2*math.pi*j/N),23.3*math.sin(2*math.pi*j/N),0)) for j in range(N)])
    boolean(o,loft('暫用_連續漸變外殼',ro))
    voids.append(loft('暫用_精確矩形根部流道',ri,None))
    path_records.append({'p0':list(p0),'p1':list(p1),'p2':list(p2),'end':list(E),'direction':list(D),'root_area_mm2':area0})
common=loft('暫用_與鼓風機吻合的R3矩形流道',[[Vector((x,y,z)) for x,y in rect(82,88,3)] for z in [-5,40]])
boolean(o,common,'DIFFERENCE')
for c in voids:boolean(o,c,'DIFFERENCE')

# Two continuous plates: a true R0.4 semicircular leading nose, followed by
# a 19.6-mm quintic taper from 0.8 to 2.0 mm. No Boolean bevel or corner pads.
for xcenter in [-14,14]:
    right=[]
    for j in range(17):
        a=-math.pi/2+math.pi/2*j/16
        right.append((xcenter+.4*math.cos(a),20.4+.4*math.sin(a)))
    for j in range(1,81):
        t=j/80;z=20.4+19.6*t;half=.4+.6*S(t)
        right.append((xcenter+half,z))
    left=[(2*xcenter-x,z) for x,z in right[-1:0:-1]]
    boolean(o,extrude_xz('暫用_薄鼻端漸厚分隔板',right+left))
for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
    boolean(o,cylinder('暫用_原法蘭安裝孔',(2+dz,dy,-2),(2+dz,dy,6),3.2 if abs(dy)==51 and abs(dz)==50 else 2.2,48),'DIFFERENCE')
checks=check(o);o.data.materials.clear();o.data.materials.append(bodymat)
bb=bounds(o);assert max(bb['size'])<300
tree=BVH(o)
def clear(a,b,label):
    d=b-a;hit=tree.ray_cast(a,d.normalized(),d.length)
    assert hit[0] is None,(label,list(a),list(b),list(hit[0]) if hit[0] else None)
for k,rec in enumerate(path_records):
    p0,p1,p2,E,D=[Vector(rec[a]) for a in ['p0','p1','p2','end','direction']]
    pp=[Vector((p0.x,0,-1)),p0]+[bez(p0,p1,p2,E,j/200) for j in range(1,201)]+[E+D*27]
    for a,b in zip(pp,pp[1:]):clear(a,b,'branch center '+str(k))
corner_paths=[]
for x in [-40,-15.4,-12.6,12.6,15.4,40]:
    ys=[-43,43] if abs(x)==40 else [-43.8,43.8]
    for y in ys:
        clear(Vector((x,y,39.5)),Vector((x,y,40.5)),'rectangular root corner')
        corner_paths.append([x,y])
thickness=[]
for z in [20.4,21,25,30,35,39.9]:
    for xc in [-14,14]:
        l=tree.ray_cast(Vector((xc-3,0,z)),Vector((1,0,0)),6)
        r=tree.ray_cast(Vector((xc+3,0,z)),Vector((-1,0,0)),6)
        assert l[0] is not None and r[0] is not None
        measured=r[0].x-l[0].x
        expected=.8+1.2*S(max(0,min(1,(z-20.4)/19.6)))
        assert abs(measured-expected)<.004,(z,measured,expected)
        thickness.append({'plate_center_x_mm':xc,'z_mm':z,'thickness_mm':measured})
for z in [1,10,19]:
    for origin,direction,target in [(Vector((0,0,z)),Vector((1,0,0)),41),(Vector((0,0,z)),Vector((-1,0,0)),41),
        (Vector((0,0,z)),Vector((0,1,0)),44),(Vector((0,0,z)),Vector((0,-1,0)),44)]:
        hit=tree.ray_cast(origin,direction,60)
        print('INLET_RAY',list(origin),list(direction),hit[3],flush=True)
        assert hit[0] is not None and abs(hit[3]-target)<.005,(list(origin),list(direction),hit[3],target)
for E,D in zip(ends,dirs):clear(E+D*27,E+D*1,'hose opening')
o['零件']='左右共用三路分流接頭；內流道平順版'
o['進風口_mm']=[82,88];o['入口圓角_mm']=3;o['前緣圓弧半徑_mm']=.4
o['前端基準厚度_mm']=.8;o['分隔板厚度_mm']=2;o['分隔板起始高度_mm']=20
o['管嘴主外徑_mm']=50.6;o['管嘴內徑_mm']=46.6;o['管嘴套接長_mm']=25
o['性能']='僅幾何改善；無CFD或壓損實測'
scene.collection['版本']='內流道平順版'
for q in bpy.context.selected_objects:q.select_set(False)
o.select_set(True);bpy.context.view_layer.objects.active=o
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_location=(0,0,75);a.spaces.active.region_3d.view_distance=340
            a.spaces.active.region_3d.view_rotation=Vector((1.2,-1.8,.8)).to_track_quat('Z','Y')
            a.spaces.active.shading.type='MATERIAL'
partfile=HERE/'03_共用分流接頭_內流道平順版.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(partfile))
stl=export(o,'分流接頭_左右共用_內流道平順_mm.stl')
# Keep actual triangles for independently plotted section comparisons.
o.data.calc_loop_triangles()
triangles=[[list(o.data.vertices[i].co) for i in t.vertices] for t in o.data.loop_triangles]
(HERE/'新接頭三角面.json').write_text(json.dumps(triangles,separators=(',',':')))
bpy.ops.wm.open_mainfile(filepath=str(OLD/'03_共用分流接頭.blend'))
oldpart=next(o for o in bpy.data.objects if o.type=='MESH');oldpart.data.calc_loop_triangles()
triangles=[[list(oldpart.data.vertices[i].co) for i in t.vertices] for t in oldpart.data.loop_triangles]
(HERE/'舊接頭三角面.json').write_text(json.dumps(triangles,separators=(',',':')))
for p,h in inputs.items():assert digest(p)==h
report={'input_hashes':inputs,'part_file':str(partfile),'STL':stl,'bounds_mm':bb,'mesh_check':checks,
    'branch_paths':path_records,'all_three_full_center_paths_clear':True,
    'root_corner_test_locations_mm':corner_paths,'root_corners_no_ledge_in_1mm_transition':True,
    'divider_thickness_samples':thickness,'nose_radius_mm':.4,'nose_base_thickness_mm':.8,
    'divider_full_thickness_mm':2,'common_inlet_mm':[82,88],'inlet_corner_radius_mm':3,
    'CFD_executed':False,'performance_validated':False,'physical_print_tested':False}
(HERE/'流道幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('NEW_SMOOTH_SPLITTER_COMPLETE',json.dumps({'bounds_mm':bb,'mesh':checks,'thickness_samples':thickness},ensure_ascii=False),flush=True)
