"""Restore the missing X- side panel and open the largest Y- rear panel."""
from pathlib import Path
from array import array
from collections import Counter
from datetime import datetime
import bpy,bmesh,json,math,hashlib,shutil,os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
SOURCE=ROOT/'完整模型.blend'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(SOURCE)
existing=[p for p in HERE.glob('完整模型_更改觀察面前備份_*.blend') if sha(p)==before]
backup=existing[0] if existing else HERE/('完整模型_更改觀察面前備份_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
if not existing:shutil.copy2(SOURCE,backup)
assert sha(backup)==before
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0

def fingerprint(o):
    h=hashlib.sha256()
    def text(x):h.update(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    text({'name':o.name,'type':o.type,'data':o.data.name if o.data else None,
        'matrix':[list(row) for row in o.matrix_world],'parent':o.parent.name if o.parent else None,
        'rotation_mode':o.rotation_mode,'location':list(o.location),'rotation':list(o.rotation_euler),
        'quaternion':list(o.rotation_quaternion),'scale':list(o.scale),'hide_render':o.hide_render,
        'hide_viewport':o.hide_viewport,'collections':sorted(c.name for c in o.users_collection),
        'modifiers':[(m.name,m.type) for m in o.modifiers],'properties':{k:repr(o[k]) for k in o.keys()}})
    def block(collection,field,n,kind):
        buf=array(kind,[0])*n;collection.foreach_get(field,buf);h.update(buf.tobytes())
    if o.type=='MESH':
        d=o.data;block(d.vertices,'co',len(d.vertices)*3,'f');block(d.edges,'vertices',len(d.edges)*2,'i')
        block(d.loops,'vertex_index',len(d.loops),'i');block(d.loops,'edge_index',len(d.loops),'i')
        block(d.polygons,'loop_start',len(d.polygons),'i');block(d.polygons,'loop_total',len(d.polygons),'i')
        block(d.polygons,'material_index',len(d.polygons),'i')
        text([p.use_smooth for p in d.polygons]);text([m.name if m else None for m in d.materials])
        for a in d.attributes:
            text([a.name,a.data_type,a.domain,len(a.data)])
            kinds={'FLOAT':('value',1,'f'),'INT':('value',1,'i'),'BOOLEAN':('value',1,'b'),
                'FLOAT_VECTOR':('vector',3,'f'),'FLOAT2':('vector',2,'f'),
                'FLOAT_COLOR':('color',4,'f'),'BYTE_COLOR':('color',4,'f'),
                'INT8':('value',1,'b'),'INT32_2D':('value',2,'i')}
            if a.data_type in kinds:
                field,n,kind=kinds[a.data_type];block(a.data,field,len(a.data)*n,kind)
            else:text([repr(v) for v in a.data])
    elif o.type=='CAMERA':text([o.data.type,o.data.lens,o.data.clip_start,o.data.clip_end,o.data.sensor_width,o.data.sensor_height])
    elif o.type=='LIGHT':text([o.data.type,o.data.energy,list(o.data.color),o.data.shadow_soft_size])
    return h.hexdigest()
shell=bpy.data.objects['Cube'];M=shell.matrix_world.copy();other={o.name:fingerprint(o) for o in bpy.data.objects if o!=shell}
units=[bpy.context.scene.unit_settings.system,bpy.context.scene.unit_settings.scale_length,bpy.context.scene.unit_settings.length_unit]
coords=[list(v.co) for v in shell.data.vertices]
def fkey(p):return (tuple(p.vertices),p.material_index,p.use_smooth)
oldfaces=Counter(fkey(p) for p in shell.data.polygons)
bm=bmesh.new();bm.from_mesh(shell.data);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table()
def loops():
    todo={e for e in bm.edges if e.is_boundary};out=[]
    while todo:
        e=todo.pop();stack=[e];edges={e};verts=set(e.verts)
        while stack:
            for v in stack.pop().verts:
                for nxt in v.link_edges:
                    if nxt in todo:todo.remove(nxt);edges.add(nxt);verts.update(nxt.verts);stack.append(nxt)
        out.append((edges,verts))
    return out
def boundary_signature(edges):
    return sorted(tuple(sorted((tuple(M@e.verts[0].co),tuple(M@e.verts[1].co)))) for e in edges)
beforeloops=loops()
side=[(ee,vv) for ee,vv in beforeloops if len(vv)>4 and all(abs((M@v.co).x+70)<1e-4 for v in vv)]
assert len(side)==1,'Missing side boundary is ambiguous'
ee,vv=side[0];retained_boundary=[boundary_signature(edges) for edges,verts in beforeloops if edges!=ee]
endpoints=[v for v in vv if sum(e in ee for e in v.link_edges)==1]
assert len(endpoints) in {0,2}
# This existing shell has a three-face seam along the lower ledge. The missing
# panel boundary is therefore an open chain whose closing edge already exists;
# reuse that seam just as the opposite side panel does, without welding vertices.
first=min(endpoints or vv,key=lambda v:v.index);ordered=[first];prev=None;cur=first
while True:
    adjacent=[e.other_vert(cur) for e in cur.link_edges if e in ee and e.other_vert(cur)!=prev]
    if not adjacent:
        assert endpoints and cur in endpoints and cur!=first
        assert any(e.other_vert(cur)==first for e in cur.link_edges)
        break
    nxt=adjacent[0]
    if nxt==first:break
    assert nxt not in ordered,'Boundary is not a simple loop'
    ordered.append(nxt);prev,cur=cur,nxt
assert len(ordered)==len(vv)
sideface=bm.faces.new(ordered);sideface.normal_update()
if (M.to_3x3().inverted().transposed()@sideface.normal).x>0:sideface.normal_flip()
sideface.material_index=next(f.material_index for f in bm.faces if f!=sideface and f.normal.x>.9)
sideface.smooth=False
sidekey=(tuple(v.index for v in sideface.verts),sideface.material_index,sideface.smooth)
def worldarea(f):
    return f.calc_area()*abs(M.to_3x3().determinant())*(M.to_3x3().inverted().transposed()@f.normal).length
back=max(bm.faces,key=worldarea)
backpoints=[M@v.co for v in back.verts]
assert len(back.verts)==4 and all(abs(p.y+25)<.0001 for p in backpoints)
assert abs(worldarea(back)-17500)<.1
backkey=(tuple(v.index for v in back.verts),back.material_index,back.smooth)
removed={'face_index':back.index,'world_y_cm':-25,'size_cm':[140,125],'area_cm2':worldarea(back),'vertices':[list(p) for p in backpoints]}
oldfaces.subtract([backkey]);oldfaces.update([sidekey])
bmesh.ops.delete(bm,geom=[back],context='FACES_ONLY')
afterloops=loops();after_signatures=[boundary_signature(edges) for edges,verts in afterloops]
for boundary in retained_boundary:assert boundary in after_signatures,'Original vent opening changed'
rear=[(edges,verts) for edges,verts in afterloops if all(abs((M@v.co).y+25)<1e-4 for v in verts)]
assert len(rear)==1 and len(rear[0][0])==4,'Rear opening is not exactly the intended rectangle'
assert not any(len(verts)>4 and all(abs((M@v.co).x+70)<1e-4 for v in verts) for edges,verts in afterloops)
bm.to_mesh(shell.data);bm.free();shell.data.update()
assert [list(v.co) for v in shell.data.vertices]==coords,'A shell vertex moved'
assert Counter(fkey(p) for p in shell.data.polygons)==+oldfaces,'An unrelated shell face changed'
for n,sig in other.items():assert fingerprint(bpy.data.objects[n])==sig,n
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            v=a.spaces.active.region_3d;v.view_location=(0,-3,55);v.view_distance=180
            v.view_rotation=Vector((1.1,-1.8,.8)).to_track_quat('Z','Y');v.view_perspective='PERSP'
staged=HERE/'完整模型_改背面開口_待核對.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(staged))
bpy.ops.wm.open_mainfile(filepath=str(staged));shell=bpy.data.objects['Cube']
assert Counter(fkey(p) for p in shell.data.polygons)==+oldfaces
assert [list(v.co) for v in shell.data.vertices]==coords
assert shell.matrix_world==M
assert {o.name for o in bpy.data.objects}==set(other)|{'Cube'}
for n,sig in other.items():assert fingerprint(bpy.data.objects[n])==sig,n
assert [bpy.context.scene.unit_settings.system,bpy.context.scene.unit_settings.scale_length,bpy.context.scene.unit_settings.length_unit]==units
assert sha(SOURCE)==before,'User saved the file during the operation; retaining staged output'
assert sha(backup)==before
os.replace(staged,SOURCE)
report={'source':str(SOURCE),'backup':str(backup),'source_sha256_before':before,'source_sha256_after':sha(SOURCE),
    'restored_side':'X=-70 cm','restored_face_vertices':len(ordered),'removed_back_face':removed,
    'all_shell_vertices_unchanged':True,'other_shell_faces_unchanged':True,
    'vent_and_umbrella_groove_preserved':True,'other_objects_verified':list(other),
    'other_object_fingerprints':other,'saved_file_reopened_and_verified':True,'original_units_preserved':units}
(HERE/'完整模型_外殼修改檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('COMPLETE_MODEL_UPDATED_AND_VERIFIED',json.dumps({'file':str(SOURCE),'backup':str(backup),'restored_side':'X=-70 cm','opened_back':'Y=-25 cm','other_objects_preserved':len(other)},ensure_ascii=False),flush=True)
