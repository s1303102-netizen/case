"""PNG-only dual-clamp integration study: 60 mm axial spacing and one shared axle.

The original full-model mesh uses numeric centimetres despite meter UI units;
the detailed clamp uses millimetres. All preview geometry is converted to metres.
Neither input .blend is saved or overwritten.
"""
from pathlib import Path
import math,json,hashlib
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path('/Users/alissachang/Desktop/大專')
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'完整模型.blend'
CLAMP=ROOT/'夾傘機構/夾傘旋轉機構_10mm_含雨傘.blend'
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=hashfile(SOURCE)
clamp_hash=hashfile(CLAMP)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original_scene=bpy.context.scene
scene=bpy.data.scenes.new('雙組夾傘機構_前後60mm_共軸_僅PNG模擬')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene.frame_set(1)


def mat(name,rgb,metal=0,rough=.45):
    material=bpy.data.materials.new(name)
    material.use_nodes=True
    material.diffuse_color=(*rgb,1)
    bsdf=material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*rgb,1)
    bsdf.inputs['Metallic'].default_value=metal
    bsdf.inputs['Roughness'].default_value=rough
    return material


white=mat('模擬_不透明白色外殼',(.76,.79,.82),.02,.43)
copies={}
for obj in original_scene.objects:
    if obj.type!='MESH':
        continue
    copy=obj.copy()
    copy.data=obj.data.copy()
    scene.collection.objects.link(copy)
    copy.matrix_world=Matrix.Scale(.01,4)@obj.matrix_world
    if obj.name=='Cube':
        copy.data.materials.clear()
        copy.data.materials.append(white)
        for face in copy.data.polygons:
            face.material_index=0
    copies[obj.name]=copy
shell=copies['Cube']
shell.data.transform(shell.matrix_world)
shell.matrix_world=Matrix.Identity(4)
shell.data.update()

# Measure the actual saved groove, not the illustrative umbrella photograph.
groove=[v.co.copy() for v in shell.data.vertices
        if abs(v.co.x)<.02 and .14<v.co.y<.26 and .68<v.co.z<.701]
assert len(groove)==8,len(groove)
gx=(min(p.x for p in groove)+max(p.x for p in groove))/2
gy=(min(p.y for p in groove)+max(p.y for p in groove))/2
floor_z=min(p.z for p in groove)
top_z=max(p.z for p in groove)
width=max(p.x for p in groove)-min(p.x for p in groove)
assert abs(width-.010)<1e-6
axis=Vector((gx,gy,floor_z+.005))

# Read only the mechanism collection, excluding the umbrella collection entirely.
with bpy.data.libraries.load(str(CLAMP),link=False) as (src,dst):
    assert '夾傘旋轉機構' in src.collections
    dst.collections=['夾傘旋轉機構']
mechanism=dst.collections[0]
mechanism.name='預覽_沿用10mm夾傘機構'
clamp_objects=list(mechanism.all_objects)
assert not any(o.name.startswith('雨傘_') for o in clamp_objects)
drive_mat=mat('模擬_驅動輪深藍灰橡膠',(.030,.065,.105),0,.65)
orange_mat=mat('模擬_橘色尼龍定向輪',(.86,.12,.012),0,.42)
for material in (drive_mat,orange_mat):
    material.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.22
for obj in clamp_objects:
    obj.animation_data_clear()
    if obj.type=='MESH':
        obj.hide_render=False
    if obj.name=='驅動輪軸':
        # Replace both independent shafts with one continuous shared axle.
        obj.hide_render=True
for obj in clamp_objects:
    if obj.name.startswith('驅動輪_基本圓柱'):
        obj.rotation_euler.y=0
        obj.data.materials.clear()
        obj.data.materials.append(drive_mat)
    elif '橘色尼龍輪' in obj.name:
        obj.rotation_euler.y=0
        obj.data.materials.clear()
        obj.data.materials.append(orange_mat)
bpy.context.view_layer.update()
placements=[]
group_axes=[]
for label,offset in [('後組',-.030),('前組',.030)]:
    group_axis=axis+Vector((0,offset,0))
    placement=Matrix.Translation(group_axis)@Matrix.Scale(.001,4)@Matrix.Translation((0,0,-24.5))
    instance=bpy.data.objects.new('預覽_'+label+'_夾傘機構',None)
    scene.collection.objects.link(instance)
    instance.instance_type='COLLECTION'
    instance.instance_collection=mechanism
    instance.matrix_world=placement
    placements.append((label,placement))
    group_axes.append(group_axis)
bpy.context.view_layer.update()
measured_centers={}
drive_centers=[]
for (label,placement),group_axis in zip(placements,group_axes):
    measured_centers[label]={}
    for obj in clamp_objects:
        if obj.name.startswith('驅動輪_基本圓柱') or '橘色尼龍輪' in obj.name:
            center=(placement@obj.matrix_world).translation
            measured_centers[label][obj.name]=list(center)
            expected_radius=.043 if obj.name.startswith('驅動輪_基本圓柱') else .011
            assert abs((center-group_axis).length-expected_radius)<1e-5,(obj.name,list(center),list(group_axis))
            if obj.name.startswith('驅動輪_基本圓柱'):
                drive_centers.append(center)
assert abs((drive_centers[1]-drive_centers[0]).length-.060)<1e-6
assert abs(drive_centers[1].x-drive_centers[0].x)<1e-6
assert abs(drive_centers[1].z-drive_centers[0].z)<1e-6

shaft_start=drive_centers[0].y-.013
shaft_end=drive_centers[1].y+.013
shaft_radius=.004
shaft_material=mat('模擬_共同轉軸_不鏽鋼',(.48,.55,.62),.80,.25)
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=shaft_radius,
    depth=shaft_end-shaft_start,location=(axis.x,(shaft_start+shaft_end)/2,drive_centers[0].z),
    rotation=(math.pi/2,0,0))
shaft=bpy.context.object
shaft.name='預覽_兩大驅動輪共用單一轉軸_直徑8mm'
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
shaft.data.materials.append(shaft_material)
for p in shaft.data.polygons:
    p.use_smooth=len(p.vertices)==4
bevel=shaft.modifiers.new('轉軸端部圓角','BEVEL')
bevel.width=.00015
bevel.segments=3
shaft['diameter_mm']=8.0
shaft['length_mm']=(shaft_end-shaft_start)*1000
shaft['shared_drive_center_spacing_mm']=60.0
assert shaft_start<drive_centers[0].y-.009 and shaft_end>drive_centers[1].y+.009

# Keep the same opening width and height. Extend only its depth to accommodate
# the rear clamp, retaining the last 5 mm of the original support groove.
half=.045
bottom=.6075000458
radius=.004
front_y=max(p.y for p in groove)
back_y=gy-.045
groove_back=min(p.y for p in groove)
groove_half=width/2
bm=bmesh.new()
bm.from_mesh(shell.data)
bm.faces.ensure_lookup_table()
front_faces=[f for f in bm.faces if all(abs(v.co.y-front_y)<1e-6 for v in f.verts)
             and max(v.co.z for v in f.verts)>.69 and min(v.co.z for v in f.verts)<.01]
assert len(front_faces)==1
top_faces=[f for f in bm.faces if len(f.verts)==4
           and all(abs(v.co.z-top_z)<1e-6 for v in f.verts)
           and max(v.co.y for v in f.verts)>.249
           and min(v.co.y for v in f.verts)>.149
           and max(abs(v.co.x) for v in f.verts)>.69
           and min(abs(v.co.x) for v in f.verts)<.006]
assert len(top_faces)==2
groove_faces=[f for f in bm.faces if all(abs(v.co.x)<=.005001 for v in f.verts)
              and all(.149<v.co.y<.251 for v in f.verts)
              and all(floor_z-1e-6<=v.co.z<=top_z+1e-6 for v in f.verts)]
assert len(groove_faces)==3
removed_indices=[f.index for f in [*front_faces,*top_faces,*groove_faces]]
bmesh.ops.delete(bm,geom=[*front_faces,*top_faces,*groove_faces],context='FACES_ONLY')


def face(points,normal=None):
    verts=[bm.verts.new(p) for p in points]
    f=bm.faces.new(verts)
    f.material_index=0
    f.normal_update()
    if normal is not None and f.normal.dot(Vector(normal))<0:
        f.normal_flip()
    return f


contour=[(-half,top_z),(-half,bottom+radius)]
for i in range(1,13):
    a=math.pi+math.pi/2*i/12
    contour.append((-half+radius+radius*math.cos(a),bottom+radius+radius*math.sin(a)))
contour.append((half-radius,bottom))
for i in range(1,13):
    a=3*math.pi/2+math.pi/2*i/12
    contour.append((half-radius+radius*math.cos(a),bottom+radius+radius*math.sin(a)))
contour.append((half,top_z))
outer=[(half,top_z),(.70,top_z),(.70,0),(-.70,0),(-.70,top_z)]+contour[:-1]
face([(x,front_y,z) for x,z in outer],(0,1,0))
for side in (-1,1):
    points=[(side*.70,groove_back,top_z),(side*.70,front_y,top_z),
            (side*half,front_y,top_z),(side*half,back_y,top_z),
            (side*groove_half,back_y,top_z),(side*groove_half,groove_back,top_z)]
    face(points,(0,0,1))
    face([(side*groove_half,groove_back,top_z),(side*groove_half,groove_back,floor_z),
          (side*groove_half,back_y,floor_z),(side*groove_half,back_y,top_z)],(-side,0,0))
face([(-groove_half,groove_back,floor_z),(groove_half,groove_back,floor_z),
      (groove_half,back_y,floor_z),(-groove_half,back_y,floor_z)],(0,0,1))
back_outline=[(-half,top_z),(-groove_half,top_z),(-groove_half,floor_z),
              (groove_half,floor_z),(groove_half,top_z),(half,top_z)]+list(reversed(contour[1:-1]))
face([(x,back_y,z) for x,z in back_outline],(0,1,0))
for (ax,az),(bx,bz) in zip(contour,contour[1:]):
    f=face([(ax,front_y,az),(bx,front_y,bz),(bx,back_y,bz),(ax,back_y,az)])
    toward=Vector((0,(front_y+back_y)/2,(bottom+top_z)/2))-f.calc_center_median()
    if f.normal.dot(toward)<0:
        f.normal_flip()
bm.to_mesh(shell.data)
bm.free()
shell.data.update()

# Confirm a genuinely open viewing path and the retained rear support groove.
shell.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co.copy() for v in shell.data.vertices],
    [tuple(t.vertices) for t in shell.data.loop_triangles],all_triangles=True)
hit=tree.ray_cast(Vector((0,.30,axis.z-.043)),Vector((0,-1,0)),.16)
assert hit[0] is not None and abs(hit[0].y-back_y)<1e-5,('Front cutout obstructed',hit)
assert tree.ray_cast(Vector((.06,.30,.65)),Vector((0,-1,0)),.08)[0] is not None
groove_test=tree.ray_cast(Vector((0,(groove_back+back_y)/2,.75)),Vector((0,0,-1)),.1)
assert groove_test[0] is not None and abs(groove_test[0].z-floor_z)<1e-5
assert shaft_start>back_y+.001 and shaft_end<front_y-.001
assert abs(shaft.dimensions.x-.008)<1e-6 and abs(shaft.dimensions.z-.008)<1e-6

def look(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

world=bpy.data.worlds.new('預覽_柔光環境')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.74,.81,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
scene.world=world
for name,pos,energy,size in [('主光',(1.2,2.2,3.2),700,2.3),
                           ('補光',(-1.7,1.5,1.6),450,1.8),
                           ('輪廓',(.7,-1.9,2.6),520,1.8)]:
    data=bpy.data.lights.new('模擬_'+name,'AREA')
    data.energy=energy
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(obj)
    obj.location=pos
    look(obj,(0,.10,.68))
floor_mesh=bpy.data.meshes.new('模擬地面_mesh')
floor_mesh.from_pydata([(-3,-3,-.004),(3,-3,-.004),(3,3,-.004),(-3,3,-.004)],[],[(0,1,2,3)])
floor=bpy.data.objects.new('模擬地面',floor_mesh)
scene.collection.objects.link(floor)
floor.data.materials.append(mat('模擬地面',(.69,.72,.74),0,.8))
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-.35
scene.render.resolution_percentage=100
cam_data=bpy.data.cameras.new('預覽_鏡頭')
cam=bpy.data.objects.new('預覽_鏡頭',cam_data)
scene.collection.objects.link(cam)
cam_data.type='ORTHO'
cam_data.clip_start=.001
cam_data.clip_end=100
scene.camera=cam
views=[
    ('01_雙組夾傘機構_整體位置.png',(1.70,2.65,1.78),(0,.04,.64),2.20,1600,1400),
    ('02_雙組夾傘機構_前後排列與共軸近照.png',(.025,.43,1.08),(0,.20,.663),.245,1600,1450),
    ('03_雙組夾傘機構_俯視中心距.png',(.005,.22,1.20),(0,.20,.66),.19,1450,1450),
]
for filename,position,target,scale,w,h in views:
    scene.view_settings.exposure=-.55 if filename.startswith('01') else -.95
    cam.location=position
    cam_data.ortho_scale=scale
    look(cam,target)
    scene.render.resolution_x=w
    scene.render.resolution_y=h
    scene.render.filepath=str(HERE/filename)
    print('RENDERING',filename,flush=True)
    bpy.ops.render.render(write_still=True)

assert hashfile(SOURCE)==source_hash,'Original complete model changed during preview.'
assert hashfile(CLAMP)==clamp_hash,'Original mechanism changed during preview.'
report={
    'preview_only':True,'source_blend_modified':False,'umbrella_imported':False,
    'mechanism_count':2,'axial_center_spacing_mm':60.0,
    'placement_convention':'Keep the original midpoint; place groups 30 mm forward and 30 mm backward along the shaft axis.',
    'source_blend':str(SOURCE),'source_sha256':source_hash,
    'clamp_source':str(CLAMP),'clamp_sha256':clamp_hash,
    'original_numeric_length_unit':'cm (model geometry convention)',
    'preview_world_length_unit':'m',
    'shaft_diameter_mm':10,
    'shaft_axis_source_cm':[axis.x*100,axis.y*100,axis.z*100],
    'measured_groove_cm':{'width':width*100,'floor':floor_z*100,'top':top_z*100,
        'y_min':groove_back*100,'y_max':front_y*100},
    'mechanism_source_millimetres_to_preview_metres':.001,
    'upper_center_spacing_mm':17.7482393493,
    'verified_mechanism_centers_preview_metres':measured_centers,
    'shared_drive_axle_mm':{'diameter':8.0,'length':(shaft_end-shaft_start)*1000,
        'center_spacing':(drive_centers[1]-drive_centers[0]).length*1000,
        'y_start_source_cm':shaft_start*100,'y_end_source_cm':shaft_end*100,
        'axis_direction':[0,1,0],'continuous_single_object':True,
        'original_individual_axles_hidden':True},
    'upper_height_above_shaft_mm':6.5,'upper_height_above_drive_axis_mm':49.5,
    'cutout_mm':{'width':half*2000,'visible_front_height':(top_z-bottom)*1000,
        'front_entry_depth':(front_y-back_y)*1000,'bottom_corner_radius':radius*1000,
        'bottom_z_source_cm':bottom*100,'back_y_source_cm':back_y*100},
    'retained_rear_groove_length_mm':(back_y-groove_back)*1000,
    'changed_original_shell_faces_in_preview':removed_indices,
    'front_view_path_open_checked':True,'rear_groove_support_preserved_checked':True,
    'images':[view[0] for view in views],
    'note':'Two floating clamps, single continuous drive axle. Opening width and height unchanged; depth extended for rear group. No umbrella or motor.'}
(HERE/'雙組夾傘機構_模擬檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PNG_ONLY_COMPLETE_SOURCE_UNCHANGED',json.dumps(report,ensure_ascii=False),flush=True)
