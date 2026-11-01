"""Produce useful views of the saved meshes without saving scene changes."""
from pathlib import Path
import bpy,ast
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'blender_build_right_hood.py').read_text())
helpers=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'look','preview'}],type_ignores=[])
exec(compile(helpers,'preview_helpers','exec'))
bpy.ops.wm.open_mainfile(filepath=str(HERE/'第一版_集風罩待檢查.blend'))
original_scene=bpy.context.scene
hood=bpy.data.objects['集風罩_右半邊_第二版_實體']
blower=bpy.data.objects['鼓風機_150FLJ330W_整體網格']
preview([bpy.data.objects['Cube'],blower,hood],.01,(-1.90,-.40,1.02),(-.20,-.04,.63),1.85,'集風罩_外殼內配置預覽.png')
bpy.ops.wm.open_mainfile(filepath=str(HERE/'集風罩_單體.blend'))
original_scene=bpy.context.scene
hood=bpy.data.objects['集風罩_右半邊_第二版_實體']
preview([hood],.001,(.80,1.20,.80),(0,.025,.25),.80,'集風罩_出風口側預覽.png')
