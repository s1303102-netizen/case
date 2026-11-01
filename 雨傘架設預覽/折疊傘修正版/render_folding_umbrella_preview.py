"""PNG-only placement study. Never save or modify the source .blend file."""
from pathlib import Path
import bpy,bmesh,json,math,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent.parent/'第一版.blend'
HERE.mkdir(exist_ok=True)
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_scene=bpy.context.scene
scene=bpy.data.scenes.new('僅PNG_折疊傘修正版')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def mat(name,color,metal=0,rough=.45):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    return m
shellmat=mat('預覽_白色機殼',(.75,.78,.80),.02,.43)
fabric1=mat('預覽_藏藍傘布',(.018,.12,.21),0,.65)
fabric2=mat('預覽_藏藍傘布_鄰片',(.019,.127,.22),0,.65)
for m in [fabric1,fabric2]:
    nodes=m.node_tree.nodes;links=m.node_tree.links
    bsdf=nodes.get('Principled BSDF');bsdf.inputs['Sheen Weight'].default_value=.22
    tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=7500
    tex.inputs['Detail'].default_value=2
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.00006
    links.new(tex.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
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
def rib_profile(t,height):
    q=1-t
    # An elastic-rib silhouette: nearly flat at the crown, steeper toward tip.
    return (3*q*q*t*.30*canopy_radius+3*q*t*t*.82*canopy_radius+t**3*canopy_radius,
            3*q*q*t*.01*height+3*q*t*t*.38*height+t**3*height)
def meridian_length(height):
    pts=[Vector(rib_profile(j/1000,height)) for j in range(1001)]
    return sum((b-a).length for a,b in zip(pts,pts[1:]))
lo,hi=.1,.4
for _ in range(48):
    dome_depth=(lo+hi)/2
    if meridian_length(dome_depth)<rib_length:lo=dome_depth
    else:hi=dome_depth
dome_depth=(lo+hi)/2
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
    # Eight fabric gores span neighboring ribs. Interpolation uses their chord,
    # rather than projecting fabric back onto a circular surface of revolution.
    sector=(phi%(2*math.pi))/(math.pi/4)
    k=int(math.floor(sector));u=sector-k
    a=k*math.pi/4;b=a+math.pi/4
    r,depth=rib_profile(t,dome_depth)
    x=r*((1-u)*math.cos(a)+u*math.cos(b))
    z=r*((1-u)*math.sin(a)+u*math.sin(b))
    panel_mid=math.sin(math.pi*u)**2
    inward=.008*t**6*panel_mid
    radial=Vector((x,z))
    if radial.length>1e-9:
        radial*=max(0,radial.length-inward)/radial.length
        x,z=radial
    belly=.006*math.sin(math.pi*t)*panel_mid
    # Subtle folds in the tensioned cloth; vanish at crown, hem, and seams.
    crease=.0007*math.sin(3*math.pi*t)**2*math.sin(2*math.pi*u)*math.sin(math.pi*t)
    return (x,tip_y+depth+belly+crease,axis_z+z)
for j in range(1,nr+1):
    for k in range(nphi):verts.append(canopy_point(j/nr,2*math.pi*k/nphi))
faces=[]
for k in range(nphi):faces.append((0,1+k,1+(k+1)%nphi))
for j in range(nr-1):
    for k in range(nphi):
        a=1+j*nphi+k;b=1+j*nphi+(k+1)%nphi
        faces.append((a,b,b+nphi,a+nphi))
fabric=mesh('預覽_23吋折疊傘_八片張力布面',verts,faces,fabric1)
fabric.data.materials.append(fabric2)
for p in fabric.data.polygons:p.material_index=((p.index%nphi)//(nphi//8))%2
bm=bmesh.new();bm.from_mesh(fabric.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(fabric.data);bm.free()
solid=fabric.modifiers.new('薄傘布_0.3mm','SOLIDIFY');solid.thickness=.0003
for k in range(8):
    phi=k*math.pi/4
    for seg,(start,end) in enumerate([(0,.42),(.42,.75),(.75,1)]):
        pts=[]
        for j in range(33):
            p=Vector(canopy_point(start+(end-start)*j/32,phi));p.y+=.0023;pts.append(p)
        tube('預覽_折疊骨_%02d_第%d節'%(k+1,seg+1),pts,[.0016,.0014,.0011][seg],ribmat)
    for hinge,t in enumerate([.42,.75]):
        p=Vector(canopy_point(t,phi));p.y+=.003
        tangent=Vector((-math.sin(phi),0,math.cos(phi)))
        tube('預覽_骨節鉚釘_%02d_%d'%(k+1,hinge),[p-tangent*.003,p+tangent*.003],.0015,metal)
        q=Vector(canopy_point(t-.014,phi));q.y+=.003
        s=Vector(canopy_point(t+.014,phi));s.y+=.003
        tube('預覽_骨節套_%02d_%d'%(k+1,hinge),[q,s],.0025,black)
    p=Vector(canopy_point(.42,phi));p.y+=.005
    tube('預覽_內支骨_%02d'%(k+1),[(0,.046,axis_z),p],.00135,ribmat)
    q=Vector(canopy_point(.70,phi));q.y+=.004
    link_start=p.lerp(Vector((0,.046,axis_z)),.32)
    tube('預覽_折疊拉桿_%02d'%(k+1),[link_start,q],.0008,metal)
    seam=[Vector(canopy_point(j/64,phi))+Vector((0,.0006,0)) for j in range(65)]
    tube('預覽_布片車縫_%02d'%(k+1),seam,.00045,ribmat)
    end=Vector(canopy_point(1,phi));pre=Vector(canopy_point(.984,phi))
    tube('預覽_傘珠_%02d'%(k+1),[pre,end+(end-pre).normalized()*.003],.0022,black)
tube('預覽_傘面滾邊',[canopy_point(1,2*math.pi*k/nphi) for k in range(nphi+1)],.00105,ribmat)
# Telescope changes are outside the support groove. Its full contact length
# retains the user-specified 10-mm diameter.
tube('預覽_伸縮中棒_上節8mm',[(0,tip_y,axis_z),(0,.072,axis_z)],.004,metal)
shaft=tube('預覽_伸縮中棒_支承段10mm',[(0,.070,axis_z),(0,.302,axis_z)],.005,metal)
tube('預覽_伸縮中棒_下節12mm',[(0,.300,axis_z),(0,.475,axis_z)],.006,metal)
for y,r in [(.070,.0057),(.300,.0067)]:
    tube('預覽_伸縮套環_'+str(y),[(0,y-.002,axis_z),(0,y+.003,axis_z)],r,ribmat)
tube('預覽_開傘滑套',[(0,.029,axis_z),(0,.064,axis_z)],.0085,black)
tube('預覽_折傘短傘頂',[(0,-.124,axis_z),(0,-.108,axis_z)],.0065,black)
# Short folding-umbrella grip: 60 mm long, about 32 mm wide, total length 650 mm.
grip_start=.466;grip_end=.526
grip_verts=[];rings=[(grip_start,.0115),(grip_start+.003,.0145),
    (grip_start+.010,.016),(grip_end-.009,.016),(grip_end-.002,.0145),(grip_end,.0115)]
ng=64
for y,r in rings:
    for i in range(ng):
        a=2*math.pi*i/ng;grip_verts.append((r*math.cos(a),y,axis_z+r*.90*math.sin(a)))
grip_faces=[tuple(reversed(range(ng)))]
for j in range(len(rings)-1):
    for i in range(ng):
        a=j*ng+i;b=j*ng+(i+1)%ng;grip_faces.append((a,b,b+ng,a+ng))
grip_faces.append(tuple((len(rings)-1)*ng+i for i in range(ng)))
mesh('預覽_折疊傘_6cm短直握把',grip_verts,grip_faces,black)
tube('預覽_握把頂圈',[(0,grip_start+.002,axis_z),(0,grip_start+.005,axis_z)],.0148,orange)
# Raised oval button and a small wrist loop.
button_y=grip_start+.020
tube('預覽_自動開收按鈕',[(0,button_y-.007,axis_z+.0146),(0,button_y+.007,axis_z+.0146)],.004,ribmat)
tube('預覽_按鈕白標',[(0,button_y-.002,axis_z+.0188),(0,button_y+.002,axis_z+.0188)],.0005,metal)
loop=[]
for i in range(65):
    a=2*math.pi*i/64
    loop.append((.013*math.sin(a),grip_end-.003+.012*math.sin(a),axis_z-.014-.026*(1-math.cos(a))))
tube('預覽_握把腕繩',loop,.0011,black)

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
        'open_tip_to_tip_cm':canopy_radius*200,'rib_curve_depth_cm':dome_depth*100,
        'handle_length_cm':6,'handle_max_width_cm':3.2,'open_total_length_cm':65,
        'handle_dimensions_status':'Illustrative assumption, not measured from user umbrella.',
        'outline':'8 rib-tip corners; chord-spanning fabric gores with inward-bowed hems; not a surface of revolution.',
        'shaft_diameter_cm':1,'shaft_axis_z_cm':axis_z*100,'canopy_tip_y_cm':tip_y*100,
        'shape_note':'Open three-fold 8-rib illustrative umbrella; telescopic shaft, articulated ribs, short straight grip. No individual umbrella measurements supplied.',
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
views=[('23吋折疊傘_立體架設模擬.png',(2.1,2.85,1.90),(0,.06,.63),2.40),
       ('23吋折疊傘_側面間隙模擬.png',(-3,.15,.72),(0,.15,.72),1.64),
       ('23吋折疊傘_短握把與凹槽.png',(.45,1.0,1.02),(0,.30,axis_z),.80),
       ('23吋折疊傘_八片傘面輪廓.png',(0,2.4,axis_z),(0,0,axis_z),1.23)]
report['views']={}
for filename,position,target,scale in views:
    if '八片傘面輪廓' in filename:
        for obj in copies.values():obj.hide_render=True
        floor.hide_render=True
        scene.render.film_transparent=True
    cam.location=position;d.ortho_scale=scale;look(cam,target)
    bpy.context.view_layer.update()
    scene.render.filepath=str(HERE/filename);bpy.ops.render.render(write_still=True)
    markers={}
    for key,point in {'support':support,'canopy_tip':(0,tip_y,axis_z),
        'canopy_rim':(canopy_radius,tip_y+dome_depth,axis_z),
        'gap_canopy':verts[minimum_index],'gap_shell':nearest_tip}.items():
        q=world_to_camera_view(scene,cam,Vector(point));markers[key]=[q.x*1500,(1-q.y)*1450]
    report['views'][filename]={'markers_px':markers,'camera_m':position,'target_m':target}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash,'Source file changed externally while preview rendered.'
report['source_sha256_after']=source_hash
(HERE/'23吋折疊傘_預覽定位與假設.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PNG_PREVIEWS_COMPLETE_SOURCE_UNCHANGED',flush=True)
