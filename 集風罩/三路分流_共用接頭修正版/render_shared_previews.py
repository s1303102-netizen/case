"""Render the delivered meshes without saving any preview-only scene changes."""
from pathlib import Path
import bpy,math,json,sys
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def render(source,name,scale,camera,target,ortho,transparent_shell=False,two_common=False):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/source))
    scene=bpy.data.scenes.new('僅供PNG渲染')
    originals=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in originals:
        if name.startswith('02_') and o.name.startswith(('小型集風罩','外購導風管')):continue
        c=o.copy();scene.collection.objects.link(c);c.matrix_world=Matrix.Scale(scale,4)@o.matrix_world
        if two_common:
            c.matrix_world.translation.x=-.145
            d=c.copy();scene.collection.objects.link(d);d.matrix_world.translation.x=.145
        if transparent_shell and o.name=='Cube':
            c.data=c.data.copy();c.data.materials.clear()
            m=bpy.data.materials.new('預覽用透明外殼');m.use_nodes=True;n=m.node_tree.nodes;n.clear()
            out=n.new('ShaderNodeOutputMaterial');mix=n.new('ShaderNodeMixShader')
            tr=n.new('ShaderNodeBsdfTransparent');bs=n.new('ShaderNodeBsdfPrincipled')
            bs.inputs['Base Color'].default_value=(.60,.70,.78,1);bs.inputs['Roughness'].default_value=.4
            mix.inputs[0].default_value=.025
            m.node_tree.links.new(tr.outputs[0],mix.inputs[1]);m.node_tree.links.new(bs.outputs[0],mix.inputs[2])
            m.node_tree.links.new(mix.outputs[0],out.inputs['Surface']);c.data.materials.append(m)
    bpy.context.window.scene=scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32
    scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
    scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('預覽背景');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.70,.78,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5;scene.world=world
    camdata=bpy.data.cameras.new('預覽相機');cam=bpy.data.objects.new('預覽相機',camdata)
    scene.collection.objects.link(cam);cam.location=camera;camdata.type='ORTHO';camdata.ortho_scale=ortho
    camdata.clip_start=.001;camdata.clip_end=100;look(cam,target);scene.camera=cam
    for name_,position,power,size in [('主光',(-1.5,-2,2.7),600,1.7),('補光',(1.6,-.2,1.6),430,1.5),('背光',(0,1.6,2.1),550,1.3)]:
        ld=bpy.data.lights.new(name_,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
        lo=bpy.data.objects.new(name_,ld);scene.collection.objects.link(lo);lo.location=position;look(lo,target)
    scene.render.film_transparent=False;scene.render.filepath=str(HERE/name)
    bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)

if '--single-only' in sys.argv:
    render('02_單側鼓風機_導管_集風罩.blend','03_單側完整組裝.png',.001,(-1.15,1.25,.95),(-.33,-.07,.36),1.45)
    sys.exit(0)
render('01_第一版_共用分流接頭.blend','01_雙側配置_透明外殼.png',.01,(1.7,-2.3,1.6),(0,-.015,.62),2.40,True)
render('01_第一版_共用分流接頭.blend','02_俯視_鼓風機對稱定位.png',.01,(0,-.03,2.8),(0,-.03,.25),1.70,True)
if '--layout-only' in sys.argv:sys.exit(0)
render('02_單側鼓風機_導管_集風罩.blend','03_單側完整組裝.png',.001,(-1.15,1.25,.95),(-.33,-.07,.36),1.45)
render('03_共用分流接頭.blend','04_同款分流接頭_兩件示意.png',.001,(.65,-.9,.65),(0,0,.075),.72,two_common=True)
render('04_小型集風罩_共用款.blend','05_共用小型集風罩.png',.001,(.38,-.52,.35),(0,-.02,.12),.45)
print('ALL_SHARED_PREVIEWS_RENDERED',flush=True)
