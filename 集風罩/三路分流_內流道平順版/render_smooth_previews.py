from pathlib import Path
import bpy,ast,json,math
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE.parent/'三路分流_共用接頭修正版/render_shared_previews.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'look','render'}],type_ignores=[]),'render_helpers','exec'))
part='03_共用分流接頭_內流道平順版.blend'
render(part,'02_平順接頭_完整外觀.png',.001,(.29,-.43,.27),(0,0,.075),.39)

# Temporary physical half-section: keep back half Y>=0 and color only cut faces.
bpy.ops.wm.open_mainfile(filepath=str(HERE/part));bpy.context.preferences.filepaths.save_version=0
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
orange=bpy.data.materials.new('僅供剖面預覽_切面橘色');orange.use_nodes=True
orange.diffuse_color=(.8,.25,.07,1)
orange.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.8,.25,.07,1)
orange.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.5
o.data.materials.append(orange)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,150,150));c=bpy.context.object
c.dimensions=(700,300,700);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
c.data.materials.append(orange)
for q in bpy.context.selected_objects:q.select_set(False)
o.select_set(True);bpy.context.view_layer.objects.active=o
m=o.modifiers.new('僅渲染用剖面','BOOLEAN');m.operation='INTERSECT';m.solver='EXACT';m.object=c
bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(c,do_unlink=True)
tmp=Path('/private/tmp/smooth_split_half_preview.blend');bpy.ops.wm.save_as_mainfile(filepath=str(tmp))
render(str(tmp),'03_內部剖開_薄前緣.png',.001,(.10,-.44,.22),(0,0,.075),.36)
render(str(tmp),'04_鼻端與矩形根部_近看.png',.001,(.025,-.20,.085),(0,0,.032),.125)
render('01_第一版_內流道平順版.blend','05_整機_平順接頭配置.png',.01,(1.7,-2.3,1.6),(0,-.015,.62),2.40,True)
print('SMOOTH_SPLITTER_PREVIEWS_RENDERED',flush=True)
