"""Build the solid right-hand Airblade-referenced hood and two Blender files.

No CFD is run. Source surface is built explicitly; this is a 2-mm solid housing,
not the closed fluid-volume STL made during the cancelled CFD preparation.
"""
from pathlib import Path
import ast
import bpy
import bmesh
import math
import json
import hashlib
import shutil
from mathutils import Vector, Matrix

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE_FILE=ROOT/'第一版.blend'
STAGED=HERE/'第一版_集風罩待檢查.blend'
BACKUP=HERE/'第一版_加入集風罩前備份.blend'
STANDALONE=HERE/'集風罩_單體.blend'
STL_FILE=HERE/'集風罩_單體_mm.stl'
REPORT=HERE/'集風罩_建模與定位檢查.json'
HOOD_NAME='集風罩_右半邊_第二版_實體'
SPEC=json.loads((HERE/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
ARC=json.loads((HERE/'右半邊集風罩_計算.json').read_text())
file_hash=hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()

# Full snapshots of existing mesh attributes, UVs and object settings.
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
helpers=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef)
                        and node.name in {'attribute_values','snapshot','units'}],type_ignores=[])
exec(compile(helpers,'original_snapshot_helpers','exec'))
original_scene=bpy.context.scene
originals={obj.name:snapshot(obj) for obj in bpy.data.objects}
original_units=units(original_scene)
assert bpy.data.objects.get(HOOD_NAME) is None,'Hood already exists; refusing to duplicate it.'
if not BACKUP.exists():shutil.copy2(SOURCE_FILE,BACKUP)
else:assert hashlib.sha256(BACKUP.read_bytes()).hexdigest()==file_hash,'Backup name already contains another version.'
blower=bpy.data.objects['鼓風機_150FLJ330W_整體網格']
port_local=Vector((113,-1.5,159))
old_port=blower.matrix_world@port_local
new_port=Vector(SPEC['blower']['proposed_port_center_cm'])
angle=math.radians(SPEC['blower']['Z_rotation_about_port_degrees'])
blower.matrix_world=(Matrix.Translation(new_port)@Matrix.Rotation(angle,4,'Z')@
                    Matrix.Translation(-old_port)@blower.matrix_world)
bpy.context.view_layer.update()
assert (blower.matrix_world@port_local-new_port).length<1e-4

collection=bpy.data.collections.new('集風罩_右半邊_第二版')
original_scene.collection.children.link(collection)


def material(name,color,metal=0,rough=.35):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metal
    bsdf.inputs['Roughness'].default_value=rough
    return m


bodymat=material('集風罩_藍灰外殼',(0.043,0.21,0.285),.15,.32)
flangemat=material('集風罩_接口法蘭',(0.10,0.16,0.20),.45,.29)
lipmat=material('集風罩_弧形刀口面板',(0.24,0.32,0.36),.70,.24)


def new_mesh(name,verts,faces,mat=bodymat):
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    if mat:obj.data.materials.append(mat)
    obj.location=new_port;obj.scale=(.1,.1,.1)
    return obj


def active(obj):
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj


def boolean(obj,cutter,operation='UNION'):
    label=cutter.name
    m=obj.modifiers.new('實體接合' if operation=='UNION' else '接口開孔','BOOLEAN')
    m.operation=operation;m.solver='EXACT';m.object=cutter
    active(obj);bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    if obj.name==HOOD_NAME:diagnose(obj,label)


def diagnose(obj,label):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bad=[e for e in bm.edges if not e.is_manifold]
    print('TOPOLOGY',label,len(bm.verts),len(bm.faces),len(bad),flush=True)
    print('LOCAL_BOUNDS',label,[(min(v.co[i] for v in bm.verts),max(v.co[i] for v in bm.verts)) for i in range(3)],flush=True)
    if bad:
        print('BAD_EDGE_SAMPLES',[(tuple(e.verts[0].co),len(e.link_faces)) for e in bad[:6]],flush=True)
    bm.free()


R=ARC['measured']['fitted_arc_radius_mm'];CY=ARC['measured']['fitted_arc_center_Y_mm']
t0,t1=[math.radians(t) for t in ARC['measured']['arc_theta_degrees']]
tf=(t0+t1)/2
port=Vector(tuple(v*10 for v in new_port))
h=SPEC['pre_nozzle_height_mm'];rv=SPEC['bend']['vertical_center_r_mm'];rb=SPEC['bend']['mean_radius_mm']
Z=ARC['measured']['opening_center_Z_mm'];bendZ=Z-rb
neckend=port.z+50;upperstart=bendZ-55
Lc=SPEC['nozzle']['converging_length_mm'];Ln=SPEC['nozzle']['total_length_mm'];lip=4;blend=6
def S(t):return 10*t**3-15*t**4+6*t**5
def integral(x):
    if x<=0:return 0
    if x>=Lc:return Lc-blend
    if x<blend:
        t=x/blend;return blend*(t**3-.5*t**4)
    if x<=Lc-blend:return x-blend/2
    t=(x-Lc+blend)/blend;return Lc-1.5*blend+blend*(t-t**3+.5*t**4)
def hh(r):return 1 if r<=lip else h/2-math.tan(math.radians(7))*integral(Ln-r)
def arc(u,r):
    a=t0+(t1-t0)*u
    return Vector((-(R+r)*math.sin(a),CY-(R+r)*math.cos(a),0))
def loft_center(u,lam):
    base=port+Vector((-82*(u-.5)*math.cos(tf),82*(u-.5)*math.sin(tf),0))
    top=arc(u,rv)
    return base*(1-lam)+top*lam
def span(lam):
    pts=[loft_center(i/400,lam) for i in range(401)]
    return sum((a-b).length for a,b in zip(pts,pts[1:]))
toparea=span(1)*h
stations=[('neck',0)]
for part,count in [('neck',6),('loft',72),('straight',10),('bend',32),('nozzle',40),('lip',4)]:
    stations.extend((part,j/count) for j in range(1,count+1))
span_cache={k:span(S(t)) for k,(part,t) in enumerate(stations) if part=='loft'}


def surface_point(u,v,k):
    part,t=stations[k]
    if part=='neck':
        p=loft_center(u,0);d=88;out=Vector((-math.sin(tf),-math.cos(tf),0));z=port.z+50*t
    elif part=='loft':
        lam=S(t);p=loft_center(u,lam);d=(7216+(toparea-7216)*lam)/span_cache[k]
        # Analytic tangent avoids float32 cancellation in finite differences,
        # which otherwise produces microscopic creases and miter spikes.
        a=t0+(t1-t0)*u
        delta=Vector((-(1-lam)*82*math.cos(tf)-lam*(R+rv)*math.cos(a)*(t1-t0),
                       (1-lam)*82*math.sin(tf)+lam*(R+rv)*math.sin(a)*(t1-t0),0))
        out=Vector((-delta.y,delta.x,0)).normalized();z=neckend+(upperstart-neckend)*t
    elif part=='straight':
        p=arc(u,rv);d=h;a=t0+(t1-t0)*u;out=Vector((-math.sin(a),-math.cos(a),0));z=upperstart+55*t
    elif part=='bend':
        a=math.pi/2*t;r=Ln+(rb+v*h)*math.cos(a);z=bendZ+(rb+v*h)*math.sin(a)
        p=arc(u,r);p.z=z;return p-port
    else:
        r=Ln-Lc*t if part=='nozzle' else lip*(1-t)
        p=arc(u,r);p.z=Z+v*2*hh(r);return p-port
    p+=out*(v*d);p.z=z
    return p-port


# Inner wall, with genuinely open intake/outlet. Solidify adds material outward.
Nu=144;Nv=4
perimeter=[]
perimeter.extend((i/Nu,-.5) for i in range(Nu))
perimeter.extend((1,-.5+j/Nv) for j in range(Nv))
perimeter.extend((1-i/Nu,.5) for i in range(Nu))
perimeter.extend((0,.5-j/Nv) for j in range(Nv))
nr=len(perimeter)
verts=[tuple(surface_point(u,v,k)) for k in range(len(stations)) for u,v in perimeter]
faces=[(k*nr+j,k*nr+(j+1)%nr,(k+1)*nr+(j+1)%nr,(k+1)*nr+j)
       for k in range(len(stations)-1) for j in range(nr)]
hood=new_mesh(HOOD_NAME,verts,faces)
diagnose(hood,'inner surface')
# Recalculation can globally flip an open surface. Verify the initial front wall
# points out of the fluid before committing to an outward material offset.
p=hood.data.polygons[0]
desired=Vector((math.sin(tf),math.cos(tf),0))
if p.normal.dot(desired)<0:
    bm=bmesh.new();bm.from_mesh(hood.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(hood.data);bm.free()
solid=hood.modifiers.new('2mm實體壁厚','SOLIDIFY')
solid.thickness=2;solid.offset=1;solid.use_even_offset=True;solid.use_quality_normals=True;solid.use_rim=True
active(hood);bpy.ops.object.modifier_apply(modifier=solid.name)
diagnose(hood,'solidify')


def rounded_rect(width,height,r,center=(0,0),steps=12):
    result=[]
    for x,y,a in [(width/2-r,height/2-r,0),(-width/2+r,height/2-r,90),
                  (-width/2+r,-height/2+r,180),(width/2-r,-height/2+r,270)]:
        for i in range(steps+1):
            t=math.radians(a+90*i/steps)
            result.append((center[0]+x+r*math.cos(t),center[1]+y+r*math.sin(t)))
    return result


tangent=Vector((-math.cos(tf),math.sin(tf),0));out=Vector((-math.sin(tf),-math.cos(tf),0))
def uvw(u,v,w):return tangent*u+out*v+Vector((0,0,w))
def prism(name,profile,low,high,mat=flangemat):
    vertices=[tuple(uvw(u,v,z)) for z in (low,high) for u,v in profile];n=len(profile)
    polys=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    polys.extend((j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n))
    return new_mesh(name,vertices,polys,mat)


# Actual blower flange is centered 2 mm off the nominal aperture center.
flange=prism('集風罩_118x120進風法蘭',rounded_rect(118,120,4,(2,0)),0,3)
opening=prism('暫用_82x88圓角進風孔',rounded_rect(82,88,3),-3,6,None)
boolean(flange,opening,'DIFFERENCE')
hole_positions=[(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),
                (-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
for i,(dy,dz) in enumerate(hole_positions):
    r=3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
    prof=[(2+dz+r*math.cos(math.tau*j/48),-dy+r*math.sin(math.tau*j/48)) for j in range(48)]
    cutter=prism('暫用_法蘭孔'+str(i),prof,-3,6,None)
    boolean(flange,cutter,'DIFFERENCE')
boolean(hood,flange)


# Curved front trim fills the original 20-mm aperture, retaining the 2-mm jet.
# Two bands fuse to the solid shell: this is a sealed material housing.
def front_band(name,zlow,zhigh):
    vertices=[]
    for i in range(Nu+1):
        u=i/Nu
        for r,z in [(0,zlow),(2,zlow),(2,zhigh),(0,zhigh)]:
            p=arc(u,r);p.z=Z+z;vertices.append(tuple(p-port))
    polys=[]
    for i in range(Nu):
        a=i*4;b=(i+1)*4
        for j in range(4):polys.append((a+j,a+(j+1)%4,b+(j+1)%4,b+j))
    polys.extend([(3,2,1,0),tuple(Nu*4+j for j in range(4))])
    return new_mesh(name,vertices,polys,lipmat)
# Leave the exact slit walls to the continuous tube. The trim overlaps those
# walls while starting 0.02 mm beyond the inner faces, avoiding coincident
# Boolean faces and leaving the clear 2 mm aperture entirely unchanged.
boolean(hood,front_band('集風罩_上刀口面板',1.02,10))
boolean(hood,front_band('集風罩_下刀口面板',-10,-1.02))


# Clean Boolean artifacts conservatively; preserve the 2-mm aperture and edges.
bm=bmesh.new();bm.from_mesh(hood.data)
diagnose(hood,'before cleanup')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
nonmanifold=[e for e in bm.edges if not e.is_manifold]
volume=bm.calc_volume(signed=False)
counts={'vertices':len(bm.verts),'edges':len(bm.edges),'faces':len(bm.faces),
        'nonmanifold_edges':len(nonmanifold),'solid_material_volume_mm3':volume}
bm.to_mesh(hood.data);bm.free()
assert counts['nonmanifold_edges']==0, f'Hood solid is not closed: {counts}'
assert volume>10000, f'Hood material volume invalid: {volume}'
for p in hood.data.polygons:p.use_smooth=True
if hasattr(hood.data,'set_sharp_from_angle'):hood.data.set_sharp_from_angle(angle=math.radians(32))
hood['造型']='第二版：連續扇形展寬／薄截面90°轉彎／緩收窄縫'
hood['範圍']='右半邊（X負側）；左右中央保留50mm不出風'
hood['壁厚_mm']=2.0;hood['出風縫_mm']=2.0
hood['有效出風弧長_mm']=SPEC['slot_span_mm'];hood['進風淨口_mm']=[82.0,88.0]
hood['進風法蘭_mm']=[118.0,120.0,3.0]
hood['出口面板高度_mm']=20.0;hood['末端最大收縮半角_deg']=7.0
hood['轉彎中心半徑_mm']=28.0
hood['網格座標單位']='mm；整合場景以0.1比例對應原公分座標'
hood['性能狀態']='候選幾何；未完成CFD，未將風速或均勻度作為已驗證數值'

def mesh_bounds(obj):
    bpy.context.view_layer.update()
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    return {'min':lo,'max':hi,'size':[hi[i]-lo[i] for i in range(3)]}
hoodbounds=mesh_bounds(hood);blowerbounds=mesh_bounds(blower)
print('BOUNDS',json.dumps({'hood':hoodbounds,'blower':blowerbounds}),flush=True)
for bounds in [hoodbounds,blowerbounds]:
    assert bounds['min'][0]>-70 and bounds['max'][0]<70
    assert bounds['min'][1]>-25 and bounds['max'][1]<25
    assert bounds['min'][2]>=0 and bounds['max'][2]<125
for name,before in originals.items():
    after=snapshot(bpy.data.objects[name])
    if name==blower.name:
        for key in ['matrix','location','rotation']:before={k:v for k,v in before.items() if k!=key};after={k:v for k,v in after.items() if k!=key}
    assert before==after,'Existing object changed unexpectedly: '+name
assert units(original_scene)==original_units
active(hood)


def viewport(target,distance,direction):
    rotation=Vector(direction).to_track_quat('Z','Y')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_location=target
                space.region_3d.view_distance=distance;space.region_3d.view_rotation=rotation
                space.region_3d.view_perspective='PERSP';space.clip_end=10000
                space.shading.type='MATERIAL'
viewport((-28,-5,47),138,(-1.5,-.38,.40))
bpy.ops.wm.save_as_mainfile(filepath=str(STAGED))
report={'original_source_sha256':file_hash,'backup':str(BACKUP),
        'original_preserved':[name for name in originals if name!=blower.name],
        'blower_mesh_preserved':True,'blower_old_port_cm':list(old_port),
        'blower_new_port_cm':list(blower.matrix_world@port_local),
        'blower_origin_cm':list(blower.location),'blower_rotation_deg':[math.degrees(a) for a in blower.rotation_euler],
        'blower_bounds_cm':blowerbounds,'hood_bounds_cm':hoodbounds,'hood_solid':counts,
        'wall_thickness_mm':2,'outlet_gap_mm':2,'outlet_trim_height_mm':20,'right_half_only':True,
        'scene_original_unit_settings':original_units,'interface_aligned':True,'CFD_executed':False,
        'saved_files_reopened_and_checked':False,'staged_integrated_file':str(STAGED)}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('INTEGRATED_HOOD_STAGED',json.dumps(report,ensure_ascii=False))


def look(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def preview(objects,matrix_scale,camera_pos,target,ortho,filename):
    scene=bpy.data.scenes.new('集風罩_臨時預覽')
    copies=[]
    for obj in objects:
        copy=obj.copy();scene.collection.objects.link(copy)
        copy.matrix_world=Matrix.Scale(matrix_scale,4)@obj.matrix_world
        copies.append(copy)
    bpy.context.window.scene=scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40;scene.cycles.use_denoising=True
    scene.render.resolution_x=1500;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('集風罩_預覽世界');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.40,.46,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4;scene.world=world
    camdata=bpy.data.cameras.new('集風罩_預覽鏡頭');cam=bpy.data.objects.new('集風罩_預覽鏡頭',camdata);scene.collection.objects.link(cam)
    cam.location=camera_pos;camdata.type='ORTHO';camdata.ortho_scale=ortho;camdata.clip_end=100
    look(cam,target);scene.camera=cam
    for name,position,power,size in [('主光',(-1.2,-1.8,2.6),650,1.6),('柔光',(1.7,-.4,1.5),430,1.4),('輪廓光',(-.2,1.8,2.2),550,1.3)]:
        light=bpy.data.lights.new('集風罩_預覽'+name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=position;look(obj,target)
    scene.render.filepath=str(HERE/filename);bpy.ops.render.render(write_still=True)
    bpy.context.window.scene=original_scene if original_scene.name in bpy.data.scenes else next(s for s in bpy.data.scenes if s!=scene)
    for obj in list(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(scene)

preview([bpy.data.objects['Cube'],blower,hood],.01,(-1.75,-.40,.95),(-.20,-.04,.55),1.6,'集風罩_外殼內配置預覽.png')

# Standalone file contains one solid hood mesh, using actual mm scene units.
bpy.ops.wm.read_factory_settings(use_empty=True)
original_scene=bpy.context.scene
with bpy.data.libraries.load(str(STAGED),link=False) as (available,loaded):loaded.objects=[HOOD_NAME]
single=loaded.objects[0];original_scene.collection.objects.link(single)
single.matrix_world=Matrix.Identity(4)
original_scene.unit_settings.system='METRIC';original_scene.unit_settings.scale_length=.001
original_scene.unit_settings.length_unit='MILLIMETERS'
single['網格座標單位']='1 Blender單位 = 1 mm；STL以毫米輸出'
active(single);viewport((0,0,240),870,(1.1,-1.9,.7))
bpy.ops.wm.save_as_mainfile(filepath=str(STANDALONE))
# Exact mesh triangle coordinates in mm, avoiding exporter-dependent unit defaults.
single.data.calc_loop_triangles()
import struct
with STL_FILE.open('wb') as out:
    out.write(b'Right hood solid, millimetres, 2mm wall, 2mm jet slot'.ljust(80,b' '))
    out.write(struct.pack('<I',len(single.data.loop_triangles)))
    for tri in single.data.loop_triangles:
        a,b,c=[single.data.vertices[i].co for i in tri.vertices];normal=(b-a).cross(c-a).normalized()
        out.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
report['standalone_file']=str(STANDALONE);report['standalone_stl_mm']=str(STL_FILE)
report['standalone_bounds_mm']=mesh_bounds(single)
report['standalone_stl_triangles']=len(single.data.loop_triangles)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
preview([single],.001,(-.95,-1.25,.80),(0,0,.25),.76,'集風罩_單體預覽.png')
print('TWO_HOOD_MODELS_BUILT')
