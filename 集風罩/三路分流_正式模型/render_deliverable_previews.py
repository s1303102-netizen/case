from pathlib import Path
import bpy,ast,sys
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE.parent/'blender_build_right_hood.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'look','preview'}],type_ignores=[]),'preview_helpers','exec'))
for source,camera,target,scale,filename in [
    ('02_單側鼓風機_導管_集風罩.blend',(-1.15,1.25,.95),(-.33,-.07,.36),1.05,'單側組裝_實際模型預覽.png'),
    ('03_分流接頭_左右款.blend',(.60,-.82,.52),(0,-.02,.08),.70,'分流接頭_左右款預覽.png'),
    ('04_小型集風罩_共用款.blend',(.38,-.52,.35),(0,-.02,.12),.35,'共用小型集風罩_預覽.png')]:
    if '--assembly-only' in sys.argv and not source.startswith('02_'):continue
    bpy.ops.wm.open_mainfile(filepath=str(HERE/source));original_scene=bpy.context.scene
    preview(list(original_scene.objects),.001,camera,target,scale,filename)
print('DELIVERABLE_PREVIEWS_COMPLETE',flush=True)
