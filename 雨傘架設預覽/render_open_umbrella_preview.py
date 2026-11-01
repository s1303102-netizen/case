"""PNG-only placement study. Never save or modify the source .blend file."""
from pathlib import Path
import bpy,bmesh,json,math,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'第一版.blend'
HERE.mkdir(exist_ok=True)
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_scene=bpy.context.scene
scene=bpy.data.scenes.new('僅PNG_開傘架設預覽')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def mat(name,color,metal=0,rough=.45):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    return m
shellmat=mat('預覽_白色機殼',(.75,.78,.80),.02,.43)
fabric1=mat('預覽_藍色傘布',(.025,.22,.35),.03,.55)
fabric2=mat('預覽_深藍傘布',(.018,.13,.23),.03,.56)
metal=mat('預覽_不鏽鋼中棒',(.50,.57,.63),.82,.24)
black=mat('預覽_防滑握把',(.025,.031,.040),0,.60)
ribmat=mat('預覽_傘骨與縫線',(.048,.070,.085),.38,.32)
orange=mat('預覽_中心套環',(.82,.28,.055),.08,.40)
copies={}
for obj in source_scene.objects:
    if obj.type!='MESH':continue
    copy=obj.copy();copy.data=obj.data.copy();scene.collection.objects.link(copy)
    copy.matrix_world=Matrix.Scale(.01,4)@obj.matrix_world
    if obj.name=='Cube':
        copy.data.materials.clear();copy.data.materials.append(shellmat)
        for p in copy.data.polygons:p.material_index=0
    copies[obj.name]=copy

def mesh(name,verts,faces,material):
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    for p in data.polygons:p.use_smooth=True
    return obj
def tube(name,points,radius,material):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=2
    c.bevel_depth=radius;c.bevel_resolution=4;c.use_fill_caps=True
    spl=c.splines.new('POLY');spl.points.add(len(points)-1)
    for p,co in zip(spl.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,c);scene.collection.objects.link(o);c.materials.append(material)
    return o

# Size is a documented illustrative assumption, not a measured individual umbrella.
rib_length=.5842;canopy_radius=.515
lo,hi=.01,1.5
for _ in range(70):
    beta=(lo+hi)/2
    if math.sin(beta)/beta>canopy_radius/rib_length:lo=beta
    else:hi=beta
beta=(lo+hi)/2;dome_radius=rib_length/beta
support_vertices=[copies['Cube'].matrix_world@v.co for v in copies['Cube'].data.vertices]
groove_vertices=[p for p in support_vertices if abs(p.x)<.02 and .14<p.y<.26 and .68<p.z<.701]
assert len(groove_vertices)>=8,'Save the groove version before rendering.'
groove_bottom=min(p.z for p in groove_vertices)
groove_top=max(p.z for p in groove_vertices)
groove_width=max(p.x for p in groove_vertices)-min(p.x for p in groove_vertices)
assert abs(groove_width-.01)<1e-5
axis_z=groove_bottom+.005;tip_y=-.110
nphi=256;nr=64
verts=[(0,tip_y,axis_z)]
def canopy_point(t,phi):
    scallop=.012*(1-math.cos(8*phi))/2*t**8
    a=beta*t*(1-scallop)
    r=dome_radius*math.sin(a)
    y=tip_y+dome_radius*(1-math.cos(a))
    return (r*math.cos(phi),y,axis_z+r*math.sin(phi))
for j in range(1,nr+1):
    for k in range(nphi):verts.append(canopy_point(j/nr,2*math.pi*k/nphi))
faces=[]
for k in range(nphi):faces.append((0,1+k,1+(k+1)%nphi))
for j in range(nr-1):
    for k in range(nphi):
        a=1+j*nphi+k;b=1+j*nphi+(k+1)%nphi
        faces.append((a,b,b+nphi,a+nphi))
fabric=mesh('預覽_23吋開傘_八片傘布',verts,faces,fabric1)
fabric.data.materials.append(fabric2)
for p in fabric.data.polygons:p.material_index=((p.index%nphi)//(nphi//8))%2
bm=bmesh.new();bm.from_mesh(fabric.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(fabric.data);bm.free()
solid=fabric.modifiers.new('薄傘布_0.3mm','SOLIDIFY');solid.thickness=.0003
for k in range(8):
    phi=k*math.pi/4
    pts=[]
    for j in range(81):
        p=Vector(canopy_point(j/80,phi));p.y+=.0016;pts.append(p)
    tube('預覽_傘骨_%02d'%(k+1),pts,.00115,ribmat)
    p=Vector(canopy_point(.48,phi));p.y+=.003
    tube('預覽_支骨_%02d'%(k+1),[(0,.045,axis_z),p],.00105,metal)
tube('預覽_傘面滾邊',[canopy_point(1,2*math.pi*k/nphi) for k in range(nphi+1)],.00105,ribmat)
shaft=tube('預覽_直徑1cm中棒',[(0,tip_y,axis_z),(0,.630,axis_z)],.005,metal)
tube('預覽_開傘滑套',[(0,.029,axis_z),(0,.064,axis_z)],.0085,black)
tube('預覽_傘頂套',[(0,-.126,axis_z),(0,-.108,axis_z)],.006,black)
tube('預覽_傘頂短尖',[(0,-.137,axis_z),(0,-.125,axis_z)],.0035,metal)
grippts=[(0,.585,axis_z),(0,.72,axis_z)]
for k in range(65):
    a=math.pi*k/64
    grippts.append((0,.72+.032*math.sin(a),axis_z-.032+.032*math.cos(a)))
grippts.append((0,.67,axis_z-.064))
tube('預覽_J形握把',grippts,.009,black)
tube('預覽_握把裝飾環',[(0,.583,axis_z),(0,.592,axis_z)],.0093,orange)

bpy.context.view_layer.update()
shell=copies['Cube'];shell.data.calc_loop_triangles();fabric.data.calc_loop_triangles()
sp=[shell.matrix_world@v.co for v in shell.data.vertices]
st=[tuple(t.vertices) for t in shell.data.loop_triangles]
shelltree=BVHTree.FromPolygons(sp,st,all_triangles=True)
canopytree=BVHTree.FromPolygons([Vector(v) for v in verts],
    [tuple(t.vertices) for t in fabric.data.loop_triangles],all_triangles=True)
contacts=canopytree.overlap(shelltree)
assert not contacts,'Illustrative umbrella fabric crosses the current shell.'
nearest=[shelltree.find_nearest(Vector(v))[3] for v in verts]
minimum_index=min(range(len(nearest)),key=lambda i:nearest[i])
nearest_tip=shelltree.find_nearest(Vector(verts[minimum_index]))[0]
support=(0,.20,axis_z)
report={'source_blend':str(SOURCE),'source_sha256_before':source_hash,
    'source_blend_saved_or_modified':False,'output':'PNG preview only',
    'umbrella_assumptions':{'nominal_size_inch':23,'rib_meridian_cm':rib_length*100,
        'open_diameter_cm':canopy_radius*200,'spherical_dome_depth_cm':dome_radius*(1-math.cos(beta))*100,
        'shaft_diameter_cm':1,'shaft_axis_z_cm':axis_z*100,'canopy_tip_y_cm':tip_y*100,
        'shape_note':'8-rib illustrative umbrella; no individual umbrella measurements supplied.',
        'diameter_reference':'https://www.kinyo.tw/products/ku-9765'},
    'support_measured':{'shaft_center_cm':[0,20,axis_z*100],'low_plane_z_cm':groove_top*100,
        'groove_width_cm':groove_width*100,'groove_depth_cm':(groove_top-groove_bottom)*100,
        'groove_bottom_z_cm':groove_bottom*100,'groove_y_range_cm':[min(p.y for p in groove_vertices)*100,max(p.y for p in groove_vertices)*100],
        'small_groove_detected_in_saved_file':True,
        'note':'D10 shaft rests on the saved groove bottom; existing groove is unchanged. Nominal width equals shaft diameter.'},
    'fabric_shell_surface_intersections':len(contacts),
    'sampled_fabric_shell_clearance_cm':min(nearest)*100,
    'clearance_sample_count':len(nearest),
    'sample_clearance_points_m':[verts[minimum_index],list(nearest_tip)],
    'clearance_note':'Vertex-to-triangle sample for assumed rigid fabric; excludes shaft support contact and fabric deflection.',
    'CFD_executed':False}
print('UMBRELLA_PREVIEW_GEOMETRY',json.dumps(report,ensure_ascii=False),flush=True)

floor=mesh('預覽_地面',[(-3,-3,-.004),(3,-3,-.004),(3,3,-.004),(-3,3,-.004)],[(0,1,2,3)],
    mat('預覽_淺灰地面',(.69,.72,.74),0,.8))
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('預覽_柔光環境');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.74,.81,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;scene.world=world
for name,pos,energy,size in [('主光',(1.1,2.3,3.1),650,2.4),('補光',(-2.0,.9,1.9),430,2.0),('背光',(.6,-1.8,2.5),520,1.6)]:
    d=bpy.data.lights.new('預覽_'+name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);o.location=pos;look(o,(0,0,.65))
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48
scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.45;scene.render.resolution_percentage=100
scene.render.resolution_x=1500;scene.render.resolution_y=1450
d=bpy.data.cameras.new('預覽鏡頭');cam=bpy.data.objects.new('預覽鏡頭',d);scene.collection.objects.link(cam)
d.type='ORTHO';d.lens=50;d.clip_start=.01;d.clip_end=100;scene.camera=cam
views=[('23吋開傘_立體架設模擬.png',(2.1,2.85,1.90),(0,.11,.63),2.45),
       ('23吋開傘_側面間隙模擬.png',(-3,.22,.72),(0,.22,.72),1.72),
       ('23吋開傘_傘柄支承近照.png',(.18,.43,.88),(0,.20,axis_z),.25)]
report['views']={}
for filename,position,target,scale in views:
    cam.location=position;d.ortho_scale=scale;look(cam,target)
    bpy.context.view_layer.update()
    scene.render.filepath=str(HERE/filename);bpy.ops.render.render(write_still=True)
    markers={}
    for key,point in {'support':support,'canopy_tip':(0,tip_y,axis_z),
        'canopy_rim':(canopy_radius,tip_y+dome_radius*(1-math.cos(beta)),axis_z),
        'gap_canopy':verts[minimum_index],'gap_shell':nearest_tip}.items():
        q=world_to_camera_view(scene,cam,Vector(point));markers[key]=[q.x*1500,(1-q.y)*1450]
    report['views'][filename]={'markers_px':markers,'camera_m':position,'target_m':target}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash,'Source file changed externally while preview rendered.'
report['source_sha256_after']=source_hash
(HERE/'23吋開傘_預覽定位與假設.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PNG_PREVIEWS_COMPLETE_SOURCE_UNCHANGED',flush=True)
