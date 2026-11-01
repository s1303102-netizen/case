"""Render the original machine with the same camera and translucent shell as the split version."""
from pathlib import Path
import bpy,ast,hashlib,json
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
SOURCE=ROOT/'第一版.blend'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(SOURCE)
tree=ast.parse((HERE.parent/'三路分流_共用接頭修正版/render_shared_previews.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'look','render'}],type_ignores=[]),'render_helpers','exec'))
camera=(1.7,-2.3,1.6);target=(0,-.015,.62);ortho=2.4
render(str(SOURCE),'原版大型集風罩_整機透視.png',.01,camera,target,ortho,True)
assert before==sha(SOURCE)
original_scene=next(s for s in bpy.data.scenes if s.name!='僅供PNG渲染')
hoods=[o.name for o in original_scene.objects if o.name.startswith('集風罩_') and o.type=='MESH']
assert len(hoods)>=2,hoods
report={'source':str(SOURCE),'source_sha256_before':before,'source_sha256_after':sha(SOURCE),
    'original_file_unchanged':True,'original_hoods':hoods,
    'preserved_original_blower_locations':True,'camera_m':list(camera),'target_m':list(target),
    'orthographic_scale_m':ortho,'same_camera_as':'三路分流_內流道平順版/05_整機_平順接頭配置.png',
    'transparent_shell_only_in_preview':True,'fluid_simulation_performed':False}
(HERE/'原檔與視角核對.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('ORIGINAL_HOOD_PREVIEW_COMPLETE_SOURCE_UNCHANGED',flush=True)
