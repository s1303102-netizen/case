from pathlib import Path
import bpy,ast
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
t=ast.parse((HERE.parent/'三路分流_共用接頭修正版/render_shared_previews.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'look','render'}],type_ignores=[]),'preview_helpers','exec'))
source='直通風刀_216x6mm.blend'
render(source,'01_直通風刀_完整外觀.png',.001,(.32,-.50,.36),(0,0,.12),.48)
render(source,'02_直線出口_頂部近看.png',.001,(.02,-.20,.48),(0,0,.232),.29)
bpy.ops.wm.open_mainfile(filepath=str(HERE/source));bpy.context.preferences.filepaths.save_version=0
o=next(iter(bpy.context.scene.objects));m=bpy.data.materials.new('預覽切面_橘色');m.use_nodes=True
m.diffuse_color=(.8,.25,.07,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.8,.25,.07,1)
o.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,150,120));c=bpy.context.object
c.dimensions=(700,300,700);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);c.data.materials.append(m)
for q in bpy.context.selected_objects:q.select_set(False)
o.select_set(True);bpy.context.view_layer.objects.active=o
mod=o.modifiers.new('僅預覽用剖面','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=c
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(c,do_unlink=True)
tmp='/private/tmp/straight_nozzle_half_preview.blend';bpy.ops.wm.save_as_mainfile(filepath=tmp)
render(tmp,'03_內部直通_剖面預覽.png',.001,(.12,-.52,.31),(0,0,.12),.46)
print('STRAIGHT_PREVIEWS_COMPLETE',flush=True)
