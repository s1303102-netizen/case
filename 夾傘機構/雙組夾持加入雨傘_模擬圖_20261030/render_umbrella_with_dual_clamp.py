"""PNG-only study using the latest complete model and the existing open umbrella.
No .blend file is saved. The third view is explicitly a disposable cutaway.
"""
from pathlib import Path
import bpy, bmesh, math, json, hashlib
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/alissachang/Desktop/大專')
SOURCE = ROOT / '完整模型.blend'
UMBRELLA_SCRIPT = ROOT / '雨傘架設預覽/折疊傘修正版/render_folding_umbrella_preview.py'
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original = bpy.context.scene
original.frame_set(1)
bpy.context.view_layer.update()
axis_z = bpy.data.objects['夾傘機構_總成_中心距60mm'].matrix_world.translation.z * .01
contacts = []
for obj in original.objects:
    role = obj.get('component_role')
    if role not in {'drive_wheel', 'passive_roller'}:
        continue
    center = obj.matrix_world.translation * .01
    wheel_radius = .038 if role == 'drive_wheel' else .006
    clearance = math.hypot(center.x, center.z-axis_z) - wheel_radius - .005
    contacts.append({'name': obj.name, 'center_m': list(center), 'shaft_contact_gap_mm': clearance*1000})
assert len(contacts) == 6
assert max(abs(c['shaft_contact_gap_mm']) for c in contacts) < .002, contacts
deps = bpy.context.evaluated_depsgraph_get()
sources = [(o.name, bpy.data.meshes.new_from_object(o.evaluated_get(deps), depsgraph=deps), o.matrix_world.copy(), o.get('component_role'))
           for o in original.objects if o.type == 'MESH' and not o.hide_render]
scene = bpy.data.scenes.new('加入雨傘_僅PNG模擬_不儲存原檔')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

# Reuse the existing authored eight-panel folding-umbrella construction, with
# the support axis measured from the current dual-clamp assembly instead.
prior = UMBRELLA_SCRIPT.read_text()
exec(compile(prior[prior.index('def mat('):prior.index('copies={}')], str(UMBRELLA_SCRIPT), 'exec'))
copies = {}
drive_mat = mat('模擬_深藍灰驅動輪', (.030,.065,.105), 0,.65)
roller_mat = mat('模擬_橘色尼龍輪', (.86,.12,.012), 0,.42)
for name, data, matrix, role in sources:
    obj = bpy.data.objects.new(name+'_模擬', data)
    scene.collection.objects.link(obj)
    obj.matrix_world = Matrix.Scale(.01,4) @ matrix
    use_mat = shellmat if name == 'Cube' else drive_mat if role == 'drive_wheel' else roller_mat if role == 'passive_roller' else None
    if use_mat:
        obj.data.materials.clear()
        obj.data.materials.append(use_mat)
        for face in obj.data.polygons:
            face.material_index = 0
    copies[name] = obj

construction = prior[prior.index('def mesh('):prior.index('bpy.context.view_layer.update()\nshell=copies')]
start = construction.index('support_vertices=')
end = construction.index('nphi=256;nr=64')
construction = construction[:start] + 'tip_y=-.110\n' + construction[end:]
exec(compile(construction, str(UMBRELLA_SCRIPT), 'exec'))
bpy.context.view_layer.update()
shell = copies['Cube']
shell.data.calc_loop_triangles()
fabric.data.calc_loop_triangles()
shelltree = BVHTree.FromPolygons([shell.matrix_world @ v.co for v in shell.data.vertices],
    [tuple(t.vertices) for t in shell.data.loop_triangles], all_triangles=True)
fabric_tree = BVHTree.FromPolygons([fabric.matrix_world @ v.co for v in fabric.data.vertices],
    [tuple(t.vertices) for t in fabric.data.loop_triangles], all_triangles=True)
fabric_crossings = fabric_tree.overlap(shelltree)
assert not fabric_crossings, 'Umbrella fabric intersects current shell'
sample_min_gap = min(shelltree.find_nearest(Vector(v))[3] for v in verts)

floor = mesh('模擬_地面',[(-3,-3,-.004),(3,-3,-.004),(3,3,-.004),(-3,3,-.004)],[(0,1,2,3)],mat('模擬_地面材質',(.69,.72,.74),0,.8))
def look(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
world = bpy.data.worlds.new('模擬_柔光環境')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.68,.74,.81,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
scene.world = world
for name, pos, energy, size in [('主光',(1.2,2.2,3.2),700,2.3),('補光',(-1.7,1.5,1.6),450,1.8),('輪廓',(.7,-1.9,2.6),520,1.8)]:
    d = bpy.data.lights.new('模擬_'+name,'AREA')
    d.energy = energy
    d.shape = 'DISK'
    d.size = size
    obj = bpy.data.objects.new(d.name,d)
    scene.collection.objects.link(obj)
    obj.location = pos
    look(obj,(0,.1,.68))
data = bpy.data.cameras.new('模擬鏡頭')
camera = bpy.data.objects.new(data.name,data)
scene.collection.objects.link(camera)
data.type = 'ORTHO'
data.clip_start = .001
data.clip_end = 100
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'

def render(filename, pos, target, scale, width, height, exposure):
    camera.location = pos
    look(camera,target)
    data.ortho_scale = scale
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.view_settings.exposure = exposure
    scene.render.filepath = str(HERE / filename)
    print('RENDERING', filename, flush=True)
    bpy.ops.render.render(write_still=True)

render('01_加入雨傘_整體擺放模擬.png',(2.1,2.85,1.90),(0,.06,.63),2.40,1600,1450,-.45)
render('02_加入雨傘_雙組夾持近照.png',(.07,.43,1.06),(0,.20,.683),.26,1600,1450,-.85)

# Only this third PNG removes the front wall in the disposable scene. The
# delivered source retains its complete nine-millimeter skin everywhere.
shell.data.transform(shell.matrix_world)
shell.matrix_world = Matrix.Identity(4)
bm = bmesh.new()
bm.from_mesh(shell.data)
panels = [f for f in bm.faces if (all(abs(v.co.y-.25)<1e-5 for v in f.verts) or all(abs(v.co.y-.241)<1e-5 for v in f.verts))
    and max(v.co.x for v in f.verts)-min(v.co.x for v in f.verts)>1.3
    and max(v.co.z for v in f.verts)-min(v.co.z for v in f.verts)>.65]
assert len(panels) == 2
bmesh.ops.delete(bm, geom=panels, context='FACES_ONLY')
bm.to_mesh(shell.data)
bm.free()
shell.data.update()
render('03_加入雨傘_夾持剖視示意.png',(.11,.57,.90),(0,.20,.680),.25,1600,1450,-.85)

assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
report = {'source':str(SOURCE),'source_sha256':source_hash,'source_modified':False,'blend_saved':False,
    'umbrella_geometry_reused_from':str(UMBRELLA_SCRIPT),
    'assumed_umbrella':{'open':True,'rib_length_mm':584.2,'open_tip_to_tip_mm':1030,'dome_depth_mm':dome_depth*1000,
        'shaft_contact_diameter_mm':10,'handle_length_mm':60,'overall_length_mm':650,
        'note':'Reused illustrative dimensions; not measured from user umbrella.'},
    'shaft_axis_m':[0,.20,axis_z], 'two_clamps_center_spacing_mm':60,
    'six_wheel_geometric_contacts':contacts,'fabric_shell_triangle_intersections':len(fabric_crossings),
    'sampled_fabric_shell_minimum_gap_mm':sample_min_gap*1000,
    'limits':'Static geometric placement only; not preload, friction, load, drive-torque or dynamic simulation.',
    'cutaway':'Image 03 only: temporary removal of two front-wall faces; actual model is unchanged.'}
(HERE / '雨傘加入模擬_定位與檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PREVIEW_COMPLETE_SOURCE_UNCHANGED',json.dumps(report,ensure_ascii=False),flush=True)
