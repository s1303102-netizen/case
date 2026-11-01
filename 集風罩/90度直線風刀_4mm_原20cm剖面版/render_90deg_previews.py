from pathlib import Path
import bpy, ast
from mathutils import Vector, Matrix
HERE=Path(__file__).resolve().parent
source=HERE.parent/'三路分流_共用接頭修正版/render_shared_previews.py'
t=ast.parse(source.read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef)
    and n.name in {'look','render'}],type_ignores=[]),'preview_helpers','exec'))
filename='90度直線風刀_216x4mm_原20cm剖面.blend'
render(filename,'01_原20cm剖面_完整外觀.png',.001,(.34,.49,.31),(0,.012,.115),.40)
render(filename,'02_直線4mm刀口_近看.png',.001,(.02,.39,.30),(0,.063,.213),.29)
bpy.ops.wm.open_mainfile(filepath=str(HERE/filename))
bpy.context.preferences.filepaths.save_version=0
o=next(iter(bpy.context.scene.objects))
m=bpy.data.materials.new('僅預覽_橘色剖面');m.use_nodes=True
m.diffuse_color=(.86,.30,.06,1)
m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.86,.30,.06,1)
o.data.materials.append(m)
bpy.ops.mesh.primitive_cube_add(size=1,location=(200,0,200))
c=bpy.context.object;c.dimensions=(400,700,700)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
c.data.materials.append(m)
for q in bpy.context.selected_objects:q.select_set(False)
o.select_set(True);bpy.context.view_layer.objects.active=o
mod=o.modifiers.new('僅PNG預覽用剖面','BOOLEAN')
mod.operation='INTERSECT';mod.solver='EXACT';mod.object=c
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(c,do_unlink=True)
temp='/private/tmp/nozzle_20cm_profile_4mm_cutaway_preview.blend'
bpy.ops.wm.save_as_mainfile(filepath=temp)
render(temp,'03_薄流道轉彎_對稱緩收_剖面.png',.001,(-.52,.26,.27),(0,.012,.115),.40)
print('ALL_90_DEG_PREVIEWS_RENDERED',flush=True)
