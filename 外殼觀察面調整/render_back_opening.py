from pathlib import Path
import bpy,ast,json,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
SOURCE=ROOT/'完整模型.blend';before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
shell=bpy.data.objects['Cube'];shell.data.calc_loop_triangles();M=shell.matrix_world
tree=BVHTree.FromPolygons([M@v.co for v in shell.data.vertices],[tuple(t.vertices) for t in shell.data.loop_triangles],all_triangles=True)
for y,z in [(-20,10),(0,50),(0,100),(-20,120)]:
    hit=tree.ray_cast(Vector((-100,y,z)),Vector((1,0,0)),31)
    assert hit[0] is not None and abs(hit[0].x+70)<.001,('Restored side has a gap',y,z)
for x in [-65,0,65]:
    for z in [5,60,120]:
        assert tree.ray_cast(Vector((x,-26,z)),Vector((0,1,0)),2)[0] is None,('Back is obstructed',x,z)
funcs=ast.parse((ROOT/'集風罩/三路分流_共用接頭修正版/render_shared_previews.py').read_text())
exec(compile(ast.Module(body=[n for n in funcs.body if isinstance(n,ast.FunctionDef) and n.name in {'look','render'}],type_ignores=[]),'preview_helpers','exec'))
render(str(SOURCE),'完整模型_背面開口預覽.png',.01,(-1.7,-2.3,1.6),(0,-.015,.62),2.4)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
r=json.loads((HERE/'完整模型_外殼修改檢查.json').read_text())
r['restored_side_surface_ray_checks_passed']=True;r['back_opening_ray_checks_passed']=True
r['preview_png']=str(HERE/'完整模型_背面開口預覽.png')
(HERE/'完整模型_外殼修改檢查.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print('OPAQUE_SHELL_PREVIEW_AND_OPENING_CHECK_COMPLETE',flush=True)
