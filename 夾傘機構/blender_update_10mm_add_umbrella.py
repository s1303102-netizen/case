"""Update existing detailed caster geometry and add a closed umbrella.

Blender units are millimetres. X is horizontal; Y is the umbrella/roller axis;
Z is up. Generated umbrella dimensions other than the D10 shaft are illustrative.
Run Blender --background --python this_file.py.
"""
import math
import json
from pathlib import Path
import bpy
from mathutils import Vector

SOURCE = Path('/Users/alissachang/Desktop/大專/夾傘機構/夾傘旋轉機構_3D.blend')
OUT = Path(__file__).resolve().parent
BLEND = OUT / '夾傘旋轉機構_10mm_含雨傘.blend'
HEIGHT = 6.5
HALF_SPACING = math.sqrt(11.0**2 - HEIGHT**2)


def material(name, color, metallic=0, roughness=.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color,1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    return mat


def attach(obj, collection, parent):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def cylinder(name, y0, y1, radius, mat, collection, root, shaft_z, bevel=0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=radius, depth=y1-y0,
        location=(0,(y0+y1)/2,shaft_z), rotation=(math.pi/2,0,0))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices)==4
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('圓角','BEVEL')
        modifier.width = bevel
        modifier.segments = 3
    bpy.context.view_layer.update()
    return attach(obj,collection,root)


def tube(name, points, radius, mat, collection, root):
    curve = bpy.data.curves.new(name+'_curve','CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 16
    curve.bevel_depth = radius
    curve.bevel_resolution = 5
    curve.use_fill_caps = True
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point,coord in zip(spline.points,points):
        point.co = (*coord,1)
    obj = bpy.data.objects.new(name,curve)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()
    return obj


def configure_motion(drive, rollers, root):
    # All contact motion derives from the driving wheel, giving linear angular
    # speeds and the radius ratio for nominal rolling without slip.
    for obj in [drive,*rollers,root]:
        obj.animation_data_clear()
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler[1] = 0
    driver = drive.driver_add('rotation_euler',1).driver
    driver.expression = '6.283185307179586*(frame-1)/119'
    for obj, ratio in [*((obj,38/6) for obj in rollers),(root,-38/5)]:
        driver = obj.driver_add('rotation_euler',1).driver
        var = driver.variables.new()
        var.name = 'drive_angle'
        var.type = 'SINGLE_PROP'
        var.targets[0].id = drive
        var.targets[0].data_path = 'rotation_euler[1]'
        driver.expression = f'drive_angle*{ratio:.16g}'


def add_umbrella(center):
    col = bpy.data.collections.new('雨傘_收合概念款_10mm傘柄')
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new('雨傘_沿傘柄軸旋轉總成',None)
    col.objects.link(root)
    root.location = center
    root.empty_display_type = 'ARROWS'
    root.empty_display_size = 15
    root['shaft_diameter_mm'] = 10.0
    root['note'] = 'Closed illustrative umbrella; only the 10 mm shaft diameter is specified.'
    bpy.context.view_layer.update()
    metal = material('雨傘_拉絲金屬傘柄',(.48,.55,.61),.72,.27)
    grip = material('雨傘_防滑握把',(.025,.036,.047),.03,.65)
    dark = material('雨傘_縫線與束帶',(.022,.06,.075),0,.7)
    navy = material('雨傘_深藍傘布',(.018,.075,.13),0,.62)
    blue = material('雨傘_藍綠傘布',(.022,.18,.23),0,.60)
    accent = material('雨傘_束帶扣',(.15,.33,.35),.1,.35)
    shaft = cylinder('雨傘_實體傘柄_直徑10mm',-150,425,5,metal,col,root,center.z)
    shaft['diameter_mm'] = 10.0
    shaft['clamping_section_y_mm'] = 0.0
    cylinder('雨傘_握把金屬接圈',-150,-140,6.3,metal,col,root,center.z,.4)
    # J handle outside the contact region, made as an editable native curve.
    points = [(0,-145,center.z),(0,-195,center.z)]
    for step in range(65):
        angle = math.pi + math.pi*step/64
        points.append((27+27*math.cos(angle),-195+27*math.sin(angle),center.z))
    points.append((54,-175,center.z))
    tube('雨傘_J形防滑握把',points,10.5,grip,col,root)

    rings = [(60,7),(66,11),(85,18),(120,23),(180,25),
             (260,22),(330,17),(380,11),(408,7),(427,5.5)]
    segments = 160
    verts = []
    for y,radius in rings:
        for i in range(segments):
            angle = 2*math.pi*i/segments
            rr = radius + .9*math.cos(8*angle)
            verts.append((rr*math.cos(angle),y,center.z+rr*math.sin(angle)))
    faces = []
    for j in range(len(rings)-1):
        for i in range(segments):
            faces.append((j*segments+i,j*segments+(i+1)%segments,
                          (j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    mesh = bpy.data.meshes.new('雨傘_八摺收合傘布_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    fabric = bpy.data.objects.new('雨傘_八摺收合傘布',mesh)
    col.objects.link(fabric)
    for mat in (navy,blue):
        mesh.materials.append(mat)
    for idx,face in enumerate(mesh.polygons):
        face.material_index = ((idx%segments)//20)%2
        face.use_smooth = True
    fabric.parent = root
    fabric.matrix_parent_inverse = root.matrix_world.inverted()
    solid = fabric.modifiers.new('傘布厚度','SOLIDIFY')
    solid.thickness = .4
    solid.offset = -1
    for rib in range(8):
        angle = (rib+.5)*math.pi/4
        points = [((rad-.6)*math.cos(angle),y,center.z+(rad-.6)*math.sin(angle))
                  for y,rad in rings]
        tube(f'雨傘_折線_{rib+1}',points,.24,dark,col,root)
    cylinder('雨傘_束帶',181,196,26.2,dark,col,root,center.z,.8)
    bpy.ops.mesh.primitive_cube_add(location=(0,188.5,center.z+26.5))
    buckle = bpy.context.object
    buckle.name = '雨傘_束帶扣'
    buckle.dimensions = (9,10,1.5)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    buckle.data.materials.append(accent)
    bevel = buckle.modifiers.new('扣角圓角','BEVEL')
    bevel.width = .6
    bevel.segments = 3
    bpy.context.view_layer.update()
    attach(buckle,col,root)
    cylinder('雨傘_傘尖金屬套',427,445,4.8,metal,col,root,center.z,.3)
    cylinder('雨傘_傘尖',445,462,3.0,grip,col,root,center.z,.6)
    return col,root,shaft


def look_at(camera,target):
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()


def bounds(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    return [obj.evaluated_get(deps).matrix_world @ Vector(p)
            for obj in objects for p in obj.evaluated_get(deps).bound_box]


def new_camera(name,location,target,ortho):
    data = bpy.data.cameras.new(name+'_data')
    data.type = 'ORTHO'
    data.ortho_scale = ortho
    data.clip_start = .1
    data.clip_end = 4000
    obj = bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj,target)
    return obj


def fit_camera(camera,objects,target,aspect):
    bpy.context.view_layer.update()
    right = camera.rotation_euler.to_quaternion() @ Vector((1,0,0))
    up = camera.rotation_euler.to_quaternion() @ Vector((0,1,0))
    points = bounds(objects)
    horizontal = [(p-Vector(target)).dot(right) for p in points]
    vertical = [(p-Vector(target)).dot(up) for p in points]
    width,height = max(horizontal)-min(horizontal),max(vertical)-min(vertical)
    camera.location += right*((max(horizontal)+min(horizontal))/2)
    camera.location += up*((max(vertical)+min(vertical))/2)
    camera.data.ortho_scale = max(width,height*aspect)*1.13


def validate(drive,rollers,center,col,root,shaft):
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    centers = [obj.matrix_world.translation.copy() for obj in rollers]
    origin = drive.matrix_world.translation.copy()
    assert abs((centers[1]-centers[0]).x-2*HALF_SPACING) < .001
    for c in centers:
        assert abs((c-center).length-11) < .001
        assert abs(c.z-origin.z-49.5) < .001
    assert abs((center-origin).length-43) < .001
    assert abs(shaft.dimensions.x-10)<.001 and abs(shaft.dimensions.z-10)<.001
    plate_reports = []
    for label in ('左','右'):
        plate = bpy.data.objects[f'{label}_固定片_27x11.4mm_雙4mm穿孔']
        pts = bounds([plate])
        # Conservative minimum over an enclosing XZ rectangle.
        near_x = min(abs(p.x-origin.x) for p in pts)
        bottom_z = min(p.z for p in pts)
        gap = math.hypot(near_x,bottom_z-origin.z)-38
        assert gap>=1.0
        plate_reports.append({'side':label,'conservative_clearance_mm':gap})
    rotation_samples = []
    for frame in (1,31,61,120):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        angle = drive.rotation_euler.y
        assert abs(root.rotation_euler.y+angle*38/5)<.0001
        assert all(abs(obj.rotation_euler.y-angle*38/6)<.0001 for obj in rollers)
        assert (root.matrix_world.translation-center).length < .001
        rotation_samples.append({'frame':frame,'drive_radians':angle,
                                 'umbrella_radians':root.rotation_euler.y})
    scene.frame_set(1)
    assert all(not obj.hide_render for obj in col.objects)
    report = {'units':'mm','source_blend':str(SOURCE),'shaft_diameter':10,
              'upper_center_spacing':2*HALF_SPACING,'upper_height_above_shaft':6.5,
              'upper_height_above_drive_axis':49.5,'shaft_center_above_drive_axis':43,
              'upper_centers_world':[list(c) for c in centers],
              'shaft_center_world':list(center),'plate_clearances':plate_reports,
              'motion_samples':rotation_samples,'animation_frames':[1,120],
              'umbrella_state':'closed; body and handle sizes illustrative',
              'motion_note':'Radius-ratio driven kinematic illustration, no preload/friction simulation.'}
    (OUT/'10mm含雨傘_尺寸與動畫檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('VALIDATION_PASSED',json.dumps(report,ensure_ascii=False))


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    scene.frame_set(1)
    drive = bpy.data.objects['驅動輪_基本圓柱']
    center = drive.matrix_world.translation+Vector((0,0,43))
    rollers = []
    for side,label in ((-1,'左'),(1,'右')):
        wheel = bpy.data.objects[f'{label}_橘色尼龍輪_直徑12_寬9mm']
        root = bpy.data.objects[f'{label}側定向滾輪_總成']
        desired = center+Vector((side*HALF_SPACING,0,6.5))
        delta = desired-wheel.matrix_world.translation
        root.location += delta
        root['wheel_center_xyz_mm'] = list(desired)
        root['mounting_surface_x_mm'] = side*(HALF_SPACING+7)
        root['upper_height_above_shaft_mm'] = HEIGHT
        rollers.append(wheel)
    bpy.context.view_layer.update()
    umbrella_col,umbrella_root,shaft = add_umbrella(center)
    configure_motion(drive,rollers,umbrella_root)
    scene.frame_start,scene.frame_end = 1,120
    scene.render.fps = 24
    scene['design_note'] = '10 mm shaft: upper centers +/-8.8741197, height above shaft 6.5, above drive 49.5. Closed umbrella added.'
    scene['motion_note'] = 'Drive +1 turn, casters +6.33333 turns, umbrella -7.6 turns over frames 1-120; kinematic illustration.'
    reference = bpy.data.objects.get('傘柄中心_參考_直徑10mm')
    if reference:
        reference.location = center
        reference.hide_viewport = True
    scene.frame_set(1)
    all_geometry = [o for o in scene.objects if o.type in ('MESH','CURVE')]
    target = Vector((10,105,center.z-10))
    full = new_camera('整體雨傘與夾持機構',target+Vector((600,-650,460)),target,700)
    scene.render.resolution_x,scene.render.resolution_y = 1600,1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    fit_camera(full,all_geometry,target,1600/1100)
    scene.camera = full
    scene.render.filepath = str(OUT/'10mm含雨傘_整體預覽.png')
    bpy.ops.render.render(write_still=True)

    # Detail previews leave the bare shaft visible and hide the remote cloth and
    # grip only during these renders, for an unobstructed engineering view.
    hidden = [o for o in umbrella_col.objects if o != shaft and o.type in ('MESH','CURVE')]
    for obj in hidden:
        obj.hide_render = True
    detail_target = Vector((0,0,drive.matrix_world.translation.z+14))
    close = new_camera('夾持細節_立體',detail_target+Vector((140,-180,120)),detail_target,142)
    scene.render.resolution_x,scene.render.resolution_y = 1100,1100
    scene.camera = close
    scene.render.filepath = str(OUT/'10mm含雨傘_夾持近照.png')
    bpy.ops.render.render(write_still=True)
    front = new_camera('夾持正視_含10mm傘柄',(0,-600,detail_target.z),detail_target,130)
    scene.camera = front
    scene.render.filepath = str(OUT/'10mm含雨傘_夾持正視.png')
    bpy.ops.render.render(write_still=True)
    for obj in hidden:
        obj.hide_render = False
    scene.camera = full
    scene.render.resolution_x,scene.render.resolution_y = 1600,1100
    scene.render.filepath = str(OUT/'10mm含雨傘_整體預覽.png')
    validate(drive,rollers,center,umbrella_col,umbrella_root,shaft)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space = area.spaces.active
                space.clip_end = 4000
                space.region_3d.view_location = Vector((0,100,center.z))
                space.region_3d.view_distance = 800
                space.region_3d.view_rotation = full.rotation_euler.to_quaternion()
                space.shading.type = 'SOLID'
                space.shading.color_type = 'MATERIAL'
                space.overlay.show_floor = False
    bpy.ops.object.select_all(action='DESELECT')
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.unit_settings.scale_length = .001
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print('SAVED_BLEND',BLEND)


if __name__=='__main__':
    main()
