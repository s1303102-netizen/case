"""Build a verified staging .blend. Publishing to the original file is separate.

Existing geometry is in numeric centimetres; retain those coordinates and set
scene scale_length=.01 so the Blender ruler reports actual millimetres.
"""
from pathlib import Path
from array import array
from collections import Counter
import ast,json,math,hashlib,shutil
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path('/Users/alissachang/Desktop/大專')
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'完整模型.blend'
CLAMP_SOURCE=ROOT/'夾傘機構/夾傘旋轉機構_10mm_含雨傘.blend'
STAGED=HERE/'完整模型_雙組夾傘_前方中空9mm.blend'
BACKUP=HERE/'完整模型_加入夾傘與中空前備份.blend'
MANIFEST=HERE/'正式實作_核對紀錄.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(SOURCE)
if BACKUP.exists():
    assert sha(BACKUP)==before,'Existing backup differs; do not overwrite. Use a fresh staging folder.'
else:
    shutil.copy2(SOURCE,BACKUP)
assert sha(BACKUP)==before
clamp_before=sha(CLAMP_SOURCE)

# Reuse the project's byte-level object audit, without running its old edits.
helper=ast.parse((ROOT/'外殼觀察面調整/change_observation_side.py').read_text())
exec(compile(ast.Module(body=[n for n in helper.body if isinstance(n,ast.FunctionDef)
    and n.name=='fingerprint'],type_ignores=[]),'existing_project_fingerprint','exec'))

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
assert not bpy.data.collections.get('夾傘機構_雙組共軸_正式整合'),'This model is already integrated; edit the existing assembly instead of importing again.'
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
original_frame=scene.frame_current
original_units=[scene.unit_settings.system,scene.unit_settings.scale_length,scene.unit_settings.length_unit]
shell=bpy.data.objects['Cube']
M=shell.matrix_world.copy()
inv=M.inverted()
original_names={o.name for o in bpy.data.objects}
other_fingerprints={o.name:fingerprint(o) for o in bpy.data.objects if o!=shell}
coords_before=[list(v.co) for v in shell.data.vertices]
facekey=lambda f:(tuple(f.vertices),f.material_index,f.use_smooth)
original_faces=Counter(facekey(f) for f in shell.data.polygons)
world=[M@v.co for v in shell.data.vertices]
groove=[p for p in world if abs(p.x)<2 and 14<p.y<26 and 68<p.z<70.1]
assert len(groove)==8,len(groove)
x0=(min(p.x for p in groove)+max(p.x for p in groove))/2
y0=(min(p.y for p in groove)+max(p.y for p in groove))/2
zfloor=min(p.z for p in groove)
ztop=max(p.z for p in groove)
youter0,youter1=min(p.y for p in groove),max(p.y for p in groove)
assert abs(max(p.x for p in groove)-min(p.x for p in groove)-1)<.0001
axis=Vector((x0,y0,zfloor+.5))
t=.9
xi=70-t
yi0,yi1=youter0+t,youter1-t
zbottom=t
zroof=ztop-t
opening_half=4.5

bm=bmesh.new()
bm.from_mesh(shell.data)
bm.faces.ensure_lookup_table()
wp=lambda v:M@v.co
top_faces=[f for f in bm.faces if len(f.verts)==4
    and all(abs(wp(v).z-ztop)<.0001 for v in f.verts)
    and min(wp(v).y for v in f.verts)>14.9
    and max(wp(v).y for v in f.verts)>24.9
    and max(abs(wp(v).x) for v in f.verts)>69.9
    and min(abs(wp(v).x) for v in f.verts)<.6]
groove_faces=[f for f in bm.faces if all(abs(wp(v).x)<=.50001 for v in f.verts)
    and all(youter0-.0001<=wp(v).y<=youter1+.0001 for v in f.verts)
    and all(zfloor-.0001<=wp(v).z<=ztop+.0001 for v in f.verts)]
assert len(top_faces)==2 and len(groove_faces)==3,(len(top_faces),len(groove_faces))
removed_indices=[f.index for f in [*top_faces,*groove_faces]]
removed_keys=[facekey(shell.data.polygons[i]) for i in removed_indices]
bmesh.ops.delete(bm,geom=[*top_faces,*groove_faces],context='FACES_ONLY')
cached=[(M@v.co,v) for v in bm.verts]
newface_roles=[]

def vert(point):
    point=Vector(point)
    for co,v in cached:
        if (co-point).length_squared<1e-10:
            return v
    v=bm.verts.new(inv@point)
    cached.append((point.copy(),v))
    return v

def face(points,normal,role):
    f=bm.faces.new([vert(p) for p in points])
    f.material_index=0
    f.smooth=False
    f.normal_update()
    wn=M.to_3x3().inverted().transposed()@f.normal
    if wn.dot(Vector(normal))<0:
        f.normal_flip()
    newface_roles.append((f,role))
    return f

# Restore the full top surface except the already-approved 90 x 82 mm opening.
for side in (-1,1):
    face([(side*70,youter0,ztop),(side*70,youter1,ztop),
          (side*.5,youter1,ztop),(side*.5,yi1,ztop),
          (side*opening_half,yi1,ztop),(side*opening_half,yi0,ztop),
          (side*.5,yi0,ztop),(side*.5,youter0,ztop)],(0,0,1),'roof_exterior')
    for ya,yb in ((youter0,yi0),(yi1,youter1)):
        face([(side*.5,ya,ztop),(side*.5,ya,zfloor),
              (side*.5,yb,zfloor),(side*.5,yb,ztop)],(-side,0,0),'groove_side')
for ya,yb in ((youter0,yi0),(yi1,youter1)):
    face([(-.5,ya,zfloor),(.5,ya,zfloor),(.5,yb,zfloor),(-.5,yb,zfloor)],
         (0,0,1),'groove_floor')

# Entire lower-front rectangular body's inner surfaces, not a local pocket.
end_profile=[(-xi,zbottom),(xi,zbottom),(xi,zroof),
    (opening_half,zroof),(opening_half,ztop),(.5,ztop),(.5,zfloor),
    (-.5,zfloor),(-.5,ztop),(-opening_half,ztop),(-opening_half,zroof),(-xi,zroof)]
face([(x,yi0,z) for x,z in end_profile],(0,1,0),'rear_inner')
face([(x,yi1,z) for x,z in end_profile],(0,-1,0),'front_inner')
for side in (-1,1):
    face([(side*xi,yi0,zbottom),(side*xi,yi1,zbottom),
          (side*xi,yi1,zroof),(side*xi,yi0,zroof)],(-side,0,0),'side_inner')
    xa,xb=sorted((side*xi,side*opening_half))
    face([(xa,yi0,zroof),(xb,yi0,zroof),(xb,yi1,zroof),(xa,yi1,zroof)],
         (0,0,-1),'roof_inner')
    face([(side*opening_half,yi0,zroof),(side*opening_half,yi1,zroof),
          (side*opening_half,yi1,ztop),(side*opening_half,yi0,ztop)],
         (-side,0,0),'observation_rim')
face([(-xi,yi0,zbottom),(xi,yi0,zbottom),(xi,yi1,zbottom),(-xi,yi1,zbottom)],
     (0,0,1),'bottom_inner')
bm.to_mesh(shell.data)
bm.free()
shell.data.update()
assert [list(v.co) for v in shell.data.vertices[:len(coords_before)]]==coords_before
remaining=original_faces.copy()
remaining.subtract(removed_keys)
assert +remaining<=Counter(facekey(f) for f in shell.data.polygons)
shell['front_body_wall_thickness_mm']=9.0
shell['front_body_hollow_inner_size_mm']=[2*xi*10,(yi1-yi0)*10,(zroof-zbottom)*10]
shell['front_body_observation_opening_mm']=[90,82]
shell['front_body_note']='Entire front rectangular body hollow; top, bottom and all four sides nominal 9 mm. Local top observation opening retained.'

# Append source parts as real editable meshes, not collection instances.
before_collections=set(bpy.data.collections)
with bpy.data.libraries.load(str(CLAMP_SOURCE),link=False) as (src,dst):
    dst.collections=['夾傘旋轉機構']
source_collection=dst.collections[0]
scene.collection.children.link(source_collection)
source_objects=list(source_collection.all_objects)
assert not any(o.name.startswith('雨傘_') for o in source_objects)
for obj in source_objects:
    obj.animation_data_clear()
    if obj.type=='MESH' and ('橘色尼龍輪' in obj.name or obj.name.startswith('驅動輪_基本圓柱')):
        obj.rotation_euler.y=0
bpy.context.view_layer.update()
source_matrices={obj:obj.matrix_world.copy() for obj in source_objects}
assembly_col=bpy.data.collections.new('夾傘機構_雙組共軸_正式整合')
scene.collection.children.link(assembly_col)
assembly=bpy.data.objects.new('夾傘機構_總成_中心距60mm',None)
assembly_col.objects.link(assembly)
assembly.location=axis
assembly.empty_display_type='ARROWS'
assembly.empty_display_size=1.5
assembly['center_spacing_mm']=60.0
assembly['shaft_diameter_mm']=10.0
assembly['umbrella_included']=False
assembly['numeric_geometry_unit']='cm; scene scale_length=.01 metres per Blender unit'
bpy.context.view_layer.update()
drives=[]
rollers=[]
new_mesh_names=[]
group_centers=[]

def parent_keep_world(obj,parent):
    bpy.context.view_layer.update()
    world_matrix=obj.matrix_world.copy()
    obj.parent=parent
    obj.matrix_parent_inverse=parent.matrix_world.inverted()
    obj.matrix_world=world_matrix
    bpy.context.view_layer.update()

def part_label(name):
    if name.startswith('驅動輪_基本圓柱'):return '大驅動輪_76x18mm'
    if name.startswith('驅動輪輪毂'):return '大輪輪轂_'+name.rsplit('_',1)[-1]
    side='左' if name.startswith('左') else '右'
    if '橘色尼龍輪' in name:return side+'_定向輪_12x9mm'
    if '固定片' in name:return side+'_固定片_27x11.4mm'
    if '沖壓輪架' in name:return side+'_輪架_'+name.rsplit('_',1)[-1]
    if '鉚釘' in name:return side+'_鉚釘_'+('負Y' if name.endswith('-1') else '正Y')
    if '輪軸' in name:return side+'_定向輪軸'
    return name

for label,offset in (('後組',-3),('前組',3)):
    center=axis+Vector((0,offset,0))
    group_centers.append(center.copy())
    group=bpy.data.objects.new('夾傘_'+label+'_總成',None)
    assembly_col.objects.link(group)
    group.location=center
    group.empty_display_type='PLAIN_AXES'
    group.empty_display_size=1
    bpy.context.view_layer.update()
    parent_keep_world(group,assembly)
    transform=Matrix.Translation(center)@Matrix.Scale(.1,4)@Matrix.Translation((0,0,-24.5))
    for src in source_objects:
        if src.type!='MESH' or src.name=='驅動輪軸':
            continue
        obj=src.copy()
        obj.data=src.data.copy()
        obj.animation_data_clear()
        obj.name='夾傘_'+label+'_'+part_label(src.name)
        obj.parent=None
        obj.matrix_parent_inverse=Matrix.Identity(4)
        assembly_col.objects.link(obj)
        obj.matrix_world=transform@source_matrices[src]
        bpy.context.view_layer.update()
        parent_keep_world(obj,group)
        obj.hide_render=False
        obj.hide_viewport=False
        obj['source_part']=src.name
        obj['clamp_group']=label
        new_mesh_names.append(obj.name)
        if '橘色尼龍輪' in src.name:
            obj['component_role']='passive_roller'
            rollers.append(obj)
        elif src.name.startswith('驅動輪_基本圓柱'):
            obj['component_role']='drive_wheel'
            drives.append(obj)
    group['shaft_center_source_cm']=list(center)
assert len(drives)==2 and len(rollers)==4

# Drop only the appended library's unlinked originals; copies remain independent.
for obj in source_objects:
    bpy.data.objects.remove(obj,do_unlink=True)
for col in list(set(bpy.data.collections)-before_collections):
    if col!=assembly_col:
        bpy.data.collections.remove(col)

shaft0,shaft1=yi0+.02,yi1-.02
steel=bpy.data.materials.new('共軸_不鏽鋼')
steel.diffuse_color=(.48,.55,.62,1)
steel.use_nodes=True
bsdf=steel.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(.48,.55,.62,1)
bsdf.inputs['Metallic'].default_value=.8
bsdf.inputs['Roughness'].default_value=.25
drive_z=axis.z-4.3
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.4,depth=shaft1-shaft0,
    location=(axis.x,(shaft0+shaft1)/2,drive_z),rotation=(math.pi/2,0,0))
shaft=bpy.context.object
shaft.name='夾傘_共用轉軸_直徑8mm'
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
for col in list(shaft.users_collection):col.objects.unlink(shaft)
assembly_col.objects.link(shaft)
shaft.data.materials.append(steel)
for poly in shaft.data.polygons:poly.use_smooth=len(poly.vertices)==4
bevel=shaft.modifiers.new('端部圓角','BEVEL')
bevel.width=.015
bevel.segments=3
bpy.context.view_layer.update()
parent_keep_world(shaft,assembly)
shaft['component_role']='shared_drive_shaft'
shaft['diameter_mm']=8.0
shaft['length_mm']=(shaft1-shaft0)*10
new_mesh_names.append(shaft.name)

# Radius-linked kinematic preview: one shaft controls both big wheels and four
# passive rollers. No force/friction simulation or umbrella geometry is added.
shaft.rotation_mode='XYZ'
shaft.rotation_euler.y=0
driver=shaft.driver_add('rotation_euler',1).driver
driver.expression='6.283185307179586*(frame-1)/119'
for obj,ratio in [*((o,1) for o in drives),*((o,38/6) for o in rollers)]:
    obj.rotation_mode='XYZ'
    obj.rotation_euler.y=0
    driver=obj.driver_add('rotation_euler',1).driver
    var=driver.variables.new()
    var.name='shaft_angle'
    var.type='SINGLE_PROP'
    var.targets[0].id=shaft
    var.targets[0].data_path='rotation_euler[1]'
    driver.expression=f'shaft_angle*{ratio:.16g}'
scene.frame_start=1
scene.frame_end=120
scene.frame_set(1)
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.01
scene.unit_settings.length_unit='MILLIMETERS'
scene['geometry_unit_note']='Coordinates retained in centimetres; .01 metre/unit makes ruler measurements physical.'
scene['dual_clamp_integration']='Two groups at Y17/Y23 cm, 60 mm axial centers, no umbrella.'

def shell_tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True)

def validate():
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    shell=bpy.data.objects['Cube']
    tree=shell_tree(shell)
    measured=[]
    def ray(origin,direction,length=300):
        hit=tree.ray_cast(Vector(origin),Vector(direction),length)
        assert hit[0] is not None,(origin,direction)
        return hit[0]
    for x in (-60,0,60):
        for z in (10,35,65):
            fouter=ray((x,30,z),(0,-1,0))
            finner=ray((x,20,z),(0,1,0))
            router=ray((x,10,z),(0,1,0))
            rinner=ray((x,20,z),(0,-1,0))
            for val in ((fouter.y-finner.y)*10,(rinner.y-router.y)*10):
                assert abs(val-9)<.002,val
                measured.append(val)
    for z in (10,35,65):
        for side in (-1,1):
            outer=ray((side*80,20,z),(-side,0,0))
            inner=ray((0,20,z),(side,0,0))
            assert abs(abs(outer.x-inner.x)*10-9)<.002
    for x in (-60,-30,0,30,60):
        inner=ray((x,20,35),(0,0,-1))
        outer=ray((x,20,-1),(0,0,1))
        assert abs((inner.z-outer.z)*10-9)<.002
    for x in (-60,-30,-5,5,30,60):
        inner=ray((x,20,35),(0,0,1))
        outer=ray((x,20,75),(0,0,-1))
        assert abs((outer.z-inner.z)*10-9)<.002,(x,list(inner),list(outer))
    assert tree.ray_cast(Vector((0,20,50)),Vector((0,0,1)),20.01)[0] is None
    for ya,yb in ((youter0,yi0),(yi1,youter1)):
        hit=ray((0,(ya+yb)/2,75),(0,0,-1),10)
        assert abs(hit.z-zfloor)<.0002
    for name,signature in other_fingerprints.items():
        assert fingerprint(bpy.data.objects[name])==signature,('Unrelated object changed',name)
    assert [list(v.co) for v in shell.data.vertices[:len(coords_before)]]==coords_before
    assert +remaining<=Counter(facekey(f) for f in shell.data.polygons)
    dc=[o.matrix_world.translation.copy() for o in drives]
    assert abs((dc[1]-dc[0]).length*10-60)<.001
    assert abs(dc[0].x-dc[1].x)<.0001 and abs(dc[0].z-dc[1].z)<.0001
    for center in dc:
        assert abs(center.z-drive_z)<.0001,([list(c) for c in dc],drive_z)
    for roller in rollers:
        c=roller.matrix_world.translation
        g=group_centers[0] if roller['clamp_group']=='後組' else group_centers[1]
        assert abs((c-g).length*10-11)<.001
        assert abs((c.z-g.z)*10-6.5)<.001
    assert abs(shaft.dimensions.x*10-8)<.001
    assert shaft0>yi0 and shaft1<yi1
    assert abs(scene.unit_settings.scale_length-.01)<1e-8
    assert not any(o.name.startswith('雨傘_') for o in scene.objects)
    motion=[]
    for frame in (1,31,61,120):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        angle=shaft.rotation_euler.y
        assert all(abs(o.rotation_euler.y-angle)<.0001 for o in drives)
        assert all(abs(o.rotation_euler.y-angle*38/6)<.0001 for o in rollers)
        motion.append({'frame':frame,'shaft_radians':angle})
    scene.frame_set(1)
    return {'front_rear_thickness_sample_range_mm':[min(measured),max(measured)],
        'side_wall_9mm_ray_checks':6,'bottom_9mm_ray_checks':5,'roof_9mm_ray_checks':6,
        'front_rear_wall_9mm_ray_checks':18,'full_width_cavity_checks_passed':True,
        'top_observation_opening_verified':True,'groove_ends_preserved':True,
        'other_objects_byte_fingerprint_verified':list(other_fingerprints),
        'unchanged_original_shell_vertices':len(coords_before),
        'original_shell_faces_preserved_except':removed_indices,
        'drive_centers_source_cm':[list(c) for c in dc],'motion_samples':motion}

verification=validate()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.clip_end=1000
            space.region_3d.view_location=Vector((0,10,65))
            space.region_3d.view_distance=185
            space.region_3d.view_rotation=Vector((1.4,2.4,1.2)).to_track_quat('Z','Y')
            space.shading.type='SOLID'
            space.shading.color_type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT')
assembly.select_set(True)
bpy.context.view_layer.objects.active=assembly
assert sha(SOURCE)==before,'User saved source while staging; original not replaced.'
bpy.ops.wm.save_as_mainfile(filepath=str(STAGED),compress=True)

# Reopen the exact bytes that will be published, then repeat geometry checks.
drive_names=[o.name for o in drives]
roller_names=[o.name for o in rollers]
shaft_name=shaft.name
bpy.ops.wm.open_mainfile(filepath=str(STAGED))
scene=bpy.context.scene
drives=[bpy.data.objects[name] for name in drive_names]
rollers=[bpy.data.objects[name] for name in roller_names]
shaft=bpy.data.objects[shaft_name]
verification=validate()
assert sha(SOURCE)==before and sha(BACKUP)==before and sha(CLAMP_SOURCE)==clamp_before
report={'source':str(SOURCE),'source_sha256_before':before,'staged_file':str(STAGED),
    'staged_sha256':sha(STAGED),'backup_file':str(BACKUP),'backup_sha256':sha(BACKUP),
    'clamp_source_sha256':clamp_before,'shell_thickness_mm':9,
    'hollow_scope':'entire lower-front rectangular body, not a local pocket',
    'outer_front_body_mm':[1400,(youter1-youter0)*10,ztop*10],
    'inner_cavity_mm':[2*xi*10,(yi1-yi0)*10,(zroof-zbottom)*10],
    'local_top_opening_mm':[90,(yi1-yi0)*10],
    'shaft_diameter_mm':10,'clamp_count':2,'clamp_center_distance_mm':60,
    'drive_wheel_diameter_mm':76,'drive_wheel_width_mm':18,
    'common_drive_shaft_diameter_mm':8,'common_drive_shaft_length_mm':(shaft1-shaft0)*10,
    'drive_bottom_to_bottom_inner_clearance_mm':(drive_z-3.8-zbottom)*10,
    'original_scene_units':original_units,
    'new_scene_units':[scene.unit_settings.system,scene.unit_settings.scale_length,scene.unit_settings.length_unit],
    'original_object_world_matrices_and_other_meshes_unchanged':True,
    'umbrella_added':False,'staged_reopened_and_verified':True,'new_mesh_names':new_mesh_names,
    'verification':verification,'original_file_not_yet_overwritten':True}
MANIFEST.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('STAGED_VERIFIED',json.dumps(report,ensure_ascii=False),flush=True)
