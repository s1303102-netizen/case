"""Render the verified model. Front-panel removal is preview-only for cutaway."""
from pathlib import Path
import bpy,bmesh,json,hashlib,sys
from mathutils import Vector,Matrix

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'完整模型_雙組夾傘_前方中空9mm.blend'
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original=bpy.context.scene
original.frame_set(1)
deps=bpy.context.evaluated_depsgraph_get()
source_meshes=[(obj,bpy.data.meshes.new_from_object(obj.evaluated_get(deps),depsgraph=deps),obj.matrix_world.copy())
               for obj in original.objects if obj.type=='MESH' and not obj.hide_render]
scene=bpy.data.scenes.new('正式模型_核對渲染_不儲存')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1

def material(name,rgb,metal=0,rough=.45):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.diffuse_color=(*rgb,1)
    bsdf=mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value=(*rgb,1)
    bsdf.inputs['Metallic'].default_value=metal
    bsdf.inputs['Roughness'].default_value=rough
    return mat

white=material('核對_白色外殼',(.76,.79,.82),.02,.43)
drive=material('核對_深藍灰驅動輪',(.030,.065,.105),0,.65)
orange=material('核對_橘色尼龍輪',(.86,.12,.012),0,.42)
shell=None
for src,mesh,matrix in source_meshes:
    obj=bpy.data.objects.new(src.name+'_核對',mesh)
    scene.collection.objects.link(obj)
    obj.matrix_world=Matrix.Scale(.01,4)@matrix
    mat=None
    if src.name=='Cube':
        mat=white
        shell=obj
    elif src.get('component_role')=='drive_wheel':mat=drive
    elif src.get('component_role')=='passive_roller':mat=orange
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        for face in obj.data.polygons:face.material_index=0
assert shell

def look(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

world=bpy.data.worlds.new('核對_環境')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.68,.74,.81,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
scene.world=world
for name,pos,power,size in [('主光',(1.2,2.2,3.2),700,2.3),
    ('補光',(-1.7,1.5,1.6),450,1.8),('輪廓',(.7,-1.9,2.6),520,1.8)]:
    data=bpy.data.lights.new('核對_'+name,'AREA')
    data.energy=power
    data.size=size
    data.shape='DISK'
    obj=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(obj)
    obj.location=pos
    look(obj,(0,.1,.68))
mesh=bpy.data.meshes.new('核對地面_mesh')
mesh.from_pydata([(-3,-3,-.004),(3,-3,-.004),(3,3,-.004),(-3,3,-.004)],[],[(0,1,2,3)])
floor=bpy.data.objects.new('核對地面',mesh)
scene.collection.objects.link(floor)
mesh.materials.append(material('核對_地面',(.69,.72,.74),0,.8))
data=bpy.data.cameras.new('核對_鏡頭')
camera=bpy.data.objects.new('核對_鏡頭',data)
scene.collection.objects.link(camera)
data.type='ORTHO'
data.clip_start=.001
data.clip_end=100
scene.camera=camera
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'

def render(name,position,target,scale,w,h,exposure):
    camera.location=position
    data.ortho_scale=scale
    look(camera,target)
    scene.render.resolution_x=w
    scene.render.resolution_y=h
    scene.view_settings.exposure=exposure
    scene.render.filepath=str(HERE/name)
    print('RENDERING',name,flush=True)
    bpy.ops.render.render(write_still=True)

if '--section-only' not in sys.argv:
    render('01_正式整合_整體外觀.png',(1.7,2.65,1.78),(0,.04,.64),2.2,1600,1400,-.55)
    render('02_正式整合_雙組共軸近照.png',(.025,.43,1.08),(0,.20,.663),.245,1600,1450,-.95)

# In this disposable rendering copy only, hide the outer and inner front wall
# surfaces so the full-width empty interior and 9 mm bottom are visible.
shell.data.transform(shell.matrix_world)
shell.matrix_world=Matrix.Identity(4)
bm=bmesh.new()
bm.from_mesh(shell.data)
panels=[f for f in bm.faces if (all(abs(v.co.y-.25)<1e-5 for v in f.verts)
        or all(abs(v.co.y-.241)<1e-5 for v in f.verts))
        and max(v.co.x for v in f.verts)-min(v.co.x for v in f.verts)>1.3
        and max(v.co.z for v in f.verts)-min(v.co.z for v in f.verts)>.65]
assert len(panels)==2,len(panels)
bmesh.ops.delete(bm,geom=panels,context='FACES_ONLY')
bm.to_mesh(shell.data)
bm.free()
shell.data.update()
# False-color only the section image's inner surfaces to distinguish the
# empty cavity from the original white exterior. Saved model stays white.
interior_mat=material('剖視核對_內壁辨識色',(.32,.46,.55),0,.72)
shell.data.materials.append(interior_mat)
interior_index=len(shell.data.materials)-1
for face in shell.data.polygons:
    points=[shell.data.vertices[i].co for i in face.vertices]
    is_inner=(all(abs(p.y-.159)<1e-5 for p in points)
        or all(abs(abs(p.x)-.691)<1e-5 for p in points)
        or all(abs(p.z-.009)<1e-5 for p in points)
        or all(abs(p.z-.691)<1e-5 for p in points))
    if is_inner:face.material_index=interior_index
render('03_正式整合_全中空與9mm底殼剖視.png',(.65,2.3,1.1),(0,.19,.38),1.64,1700,1150,-.65)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
(HERE/'渲染說明.json').write_text(json.dumps({'model_modified_by_render':False,
    'rendered_from_verified_staged_file':True,
    'cutaway_front_panel_removal':'Only in image 03 disposable preview; saved model retains both front skins.',
    'cutaway_inner_surface_color':'Blue-gray inspection color in image 03 only; production model is unchanged.',
    'images':['01_正式整合_整體外觀.png','02_正式整合_雙組共軸近照.png','03_正式整合_全中空與9mm底殼剖視.png']},ensure_ascii=False,indent=2))
print('PREVIEWS_COMPLETE_VERIFIED_MODEL_UNCHANGED',flush=True)
