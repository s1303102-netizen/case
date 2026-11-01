from pathlib import Path
import bpy,bmesh,ast,hashlib,json,shutil
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'三路分流_共用接頭修正版';ROOT=HERE.parent.parent
r=json.loads((HERE/'流道幾何檢查.json').read_text())
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'attribute_values','snapshot','units'}],type_ignores=[]),'snapshot_helpers','exec'))
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(o):return hashlib.sha256(json.dumps(snapshot(o),sort_keys=True).encode()).hexdigest()
def geohash(o):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in o.data.vertices],'f':[list(p.vertices) for p in o.data.polygons]},separators=(',',':')).encode()).hexdigest()
def geo(o,factor):
    o.data.calc_loop_triangles();M=Matrix.Scale(factor,4)@o.matrix_world
    return BVHTree.FromPolygons([M@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
def loadnew():
    with bpy.data.libraries.load(r['part_file'],link=False) as (available,loaded):loaded.objects=available.objects
    assert len(loaded.objects)==1;return loaded.objects[0]
checks=[];expectedhash=None
for src,dst,count,scale in [('01_第一版_共用分流接頭.blend','01_第一版_內流道平順版.blend',2,10),
    ('02_單側鼓風機_導管_集風罩.blend','02_單側組裝_內流道平順版.blend',1,1)]:
    assert digest(OLD/src)==r['input_hashes'][str(OLD/src)]
    bpy.ops.wm.open_mainfile(filepath=str(OLD/src));bpy.context.preferences.filepaths.save_version=0
    baseline={o.name:signature(o) for o in bpy.data.objects};u=units(bpy.context.scene)
    splitters=[o for o in bpy.context.scene.objects if o.name.startswith('三路分流接頭_')]
    assert len(splitters)==count,[o.name for o in splitters]
    old_transforms={o.name:[list(row) for row in o.matrix_world] for o in splitters}
    original_geos={o.name:geohash(o) for o in splitters}
    new=loadnew();newdata=new.data
    for o in splitters:
        o.data=newdata
        for k in new.keys():o[k]=new[k]
    bpy.data.objects.remove(new,do_unlink=True)
    names={o.name for o in splitters}
    for n,sig in baseline.items():
        if n not in names:assert signature(bpy.data.objects[n])==sig,n
    assert units(bpy.context.scene)==u
    if count==2:
        st=geo(bpy.data.objects['Cube'],scale)
        for o in splitters:assert not geo(o,scale).overlap(st),(o.name,'crosses shell')
    gh=geohash(splitters[0])
    if expectedhash:assert gh==expectedhash
    else:expectedhash=gh
    for o in splitters:
        assert geohash(o)==expectedhash and gh!=original_geos[o.name]
        assert [list(row) for row in o.matrix_world]==old_transforms[o.name]
    path=HERE/dst;bpy.ops.wm.save_as_mainfile(filepath=str(path))
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for n,sig in baseline.items():
        if n not in names:assert signature(bpy.data.objects[n])==sig,n
    for n in names:
        o=bpy.data.objects[n];assert geohash(o)==expectedhash
        assert [list(row) for row in o.matrix_world]==old_transforms[n]
    assert units(bpy.context.scene)==u
    checks.append({'file':str(path),'part_instances':count,'saved_reopened':True,
        'all_other_objects_preserved':True,'splitter_transforms_preserved':True,'splitter_mesh_matches_print_part':True})
shutil.copy2(OLD/'04_小型集風罩_共用款.blend',HERE/'04_小型集風罩_共用款.blend')
for f in (OLD/'STL_毫米').glob('小型集風罩*.stl'):shutil.copy2(f,HERE/'STL_毫米'/f.name)
bpy.ops.wm.open_mainfile(filepath=r['part_file']);assert len(bpy.context.scene.objects)==1
assert geohash(next(iter(bpy.context.scene.objects)))==expectedhash
checks.append({'file':r['part_file'],'part_instances':1,'saved_reopened':True})
bpy.ops.wm.open_mainfile(filepath=str(HERE/'04_小型集風罩_共用款.blend'))
assert len(bpy.context.scene.objects)==1
checks.append({'file':str(HERE/'04_小型集風罩_共用款.blend'),'unchanged_from_previous':True,'saved_reopened':True})
for p,h in r['input_hashes'].items():assert digest(p)==h
r['assembly_checks']=checks;r['saved_blends_verified']=True
r['output_blend_sha256']={Path(q['file']).name:digest(q['file']) for q in checks}
r['latest_user_saved_machine_preserved_except_splitter_meshes']=True
(HERE/'流道幾何檢查.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print('FOUR_UPDATED_BLENDS_REOPENED_AND_VERIFIED',json.dumps(checks,ensure_ascii=False),flush=True)
