"""Reopen actual saved models, check preservation, connections and solid mesh."""
from pathlib import Path
import bpy,bmesh,ast,json,hashlib,math,struct,os
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=ROOT/'第一版.blend'
STAGED=HERE/'第一版_集風罩待檢查.blend'
BACKUP=HERE/'第一版_加入集風罩前備份.blend'
SINGLE=HERE/'集風罩_單體.blend'
REPORT=HERE/'集風罩_建模與定位檢查.json'
NAME='集風罩_右半邊_第二版_實體'
report=json.loads(REPORT.read_text())
spec=json.loads((HERE/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
arc=json.loads((HERE/'右半邊集風罩_計算.json').read_text())['measured']
tree=ast.parse((ROOT/'鼓風機/blender_verify_and_install_blower.py').read_text())
helpers=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'attribute_values','snapshot','units'}],type_ignores=[])
exec(compile(helpers,'snapshot_helpers','exec'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(SOURCE)==report['original_source_sha256']==digest(BACKUP)
bpy.ops.wm.open_mainfile(filepath=str(BACKUP))
before={o.name:snapshot(o) for o in bpy.data.objects}
oldunits=units(bpy.context.scene)
scenes=sorted(s.name for s in bpy.data.scenes)
bpy.ops.wm.open_mainfile(filepath=str(STAGED))
assert sorted(s.name for s in bpy.data.scenes)==scenes
assert units(bpy.context.scene)==oldunits
assert set(bpy.data.objects.keys())==set(before)|{NAME}
for name,baseline in before.items():
    current=snapshot(bpy.data.objects[name])
    if name=='鼓風機_150FLJ330W_整體網格':
        for key in ['matrix','location','rotation']:
            baseline.pop(key);current.pop(key)
    assert baseline==current,'Original data changed: '+name
hood=bpy.data.objects[NAME]
mesh_signature=snapshot(hood)['mesh']
def bvh(obj):
    obj.data.calc_loop_triangles()
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    triangles=[tuple(t.vertices) for t in obj.data.loop_triangles]
    return BVHTree.FromPolygons(vertices,triangles,all_triangles=True),vertices,triangles
hv,hpoints,htri=bvh(hood)
shell=bpy.data.objects['Cube']
sv,spoints,stri=bvh(shell)
intersections=hv.overlap(sv)
locations=[]
for hi,si in intersections:
    tri=[hpoints[i] for i in htri[hi]]
    locations.append({'hood_triangle':hi,'shell_triangle':si,
                      'hood_min_cm':[min(p[a] for p in tri) for a in range(3)],
                      'hood_max_cm':[max(p[a] for p in tri) for a in range(3)]})
report['shell_contact_check']={'triangle_contacts':len(intersections),'samples':locations[:20],
    'z_range_cm':[min(q['hood_min_cm'][2] for q in locations),max(q['hood_max_cm'][2] for q in locations)] if locations else None}
print('SHELL_CONTACT',json.dumps(report['shell_contact_check']),flush=True)
for q in locations:
    # The trim ends touch the top edge of the existing 20-mm opening.
    assert abs(q['hood_min_cm'][2]-(arc['opening_center_Z_mm']+10)/10)<.001
    assert abs(q['hood_max_cm'][2]-(arc['opening_center_Z_mm']+10)/10)<.001
report['shell_contact_check']['contacts_only_at_existing_opening_upper_trim_edge']=True
port=Vector(spec['blower']['proposed_port_center_cm'])
blower=bpy.data.objects['鼓風機_150FLJ330W_整體網格']
blower_tree,blower_points,blower_triangles=bvh(blower)
assert not blower_tree.overlap(sv),'Blower interferes with existing shell'
report['blower_shell_surface_intersections']=0
actual=blower.matrix_world@Vector((113,-1.5,159))
assert (actual-port).length<1e-4
assert (hood.location-port).length<1e-4
R=arc['fitted_arc_radius_mm'];CY=arc['fitted_arc_center_Y_mm']
t0,t1=[math.radians(v) for v in arc['arc_theta_degrees']]
Z=arc['opening_center_Z_mm']
for i in range(1,40):
    a=t0+(t1-t0)*i/40
    start=Vector((-(R+2)*math.sin(a)/10,(CY-(R+2)*math.cos(a))/10,Z/10))
    assert sv.ray_cast(start,Vector((math.sin(a),math.cos(a),0)),2)[0] is None,'Existing shell blocks outlet'
report['outlet_clear_through_existing_shell_samples']=39
report['saved_inlet_alignment_error_mm']=(actual-hood.location).length*10
bpy.ops.wm.open_mainfile(filepath=str(SINGLE))
assert list(bpy.data.objects.keys())==[NAME]
single=bpy.data.objects[NAME]
assert single.type=='MESH' and not single.modifiers
assert snapshot(single)['mesh']==mesh_signature
assert units(bpy.context.scene)==['METRIC',.0010000000474974513,'MILLIMETERS'] or abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
assert max(abs(single.matrix_world[i][j]-float(i==j)) for i in range(4) for j in range(4))<1e-8
bm=bmesh.new();bm.from_mesh(single.data)
assert all(e.is_manifold for e in bm.edges)
assert bm.calc_volume(signed=True)>0
# The material housing has one connected component, while its internal duct
# remains open at the intake and through the horizontal slit.
remaining=set(bm.verts);components=[]
while remaining:
    stack=[remaining.pop()];count=0
    while stack:
        vertex=stack.pop();count+=1
        for edge in vertex.link_edges:
            other=edge.other_vert(vertex)
            if other in remaining:remaining.remove(other);stack.append(other)
    components.append(count)
assert len(components)==1,components
bm.free()
tree,points,tris=bvh(single)
R=arc['fitted_arc_radius_mm'];CY=arc['fitted_arc_center_Y_mm']
t0,t1=[math.radians(v) for v in arc['arc_theta_degrees']]
Z=arc['opening_center_Z_mm'];portmm=port*10
def p(u,r,z):
    a=t0+(t1-t0)*u
    return Vector((-(R+r)*math.sin(a),CY-(R+r)*math.cos(a),z))-portmm
gaps=[]
for i in range(1,20):
    u=i/20;a=t0+(t1-t0)*u
    center=p(u,2,Z)
    upper=tree.ray_cast(center,Vector((0,0,1)),10)
    lower=tree.ray_cast(center,Vector((0,0,-1)),10)
    assert upper[0] is not None and lower[0] is not None
    gap=upper[3]+lower[3];gaps.append(gap)
    assert abs(gap-2)<.002,(u,gap)
    # Exit is clear toward the original circular opening.
    hit=tree.ray_cast(center,Vector((math.sin(a),math.cos(a),0)),8)
    assert hit[0] is None,('Outlet blocked',u,hit)
assert tree.ray_cast(Vector((0,0,20)),Vector((0,0,-1)),30)[0] is None,'Intake blocked'
with (HERE/'集風罩_單體_mm.stl').open('rb') as f:
    f.seek(80);n=struct.unpack('<I',f.read(4))[0]
assert n==len(single.data.loop_triangles)
assert (HERE/'集風罩_單體_mm.stl').stat().st_size==84+50*n
report.update({'saved_files_reopened_and_checked':True,'single_connected_material_body':True,
               'single_mesh_identical_to_integrated':True,'intake_and_outlet_clear':True,
               'slit_gap_sample_count':len(gaps),'measured_slit_gap_mm':[min(gaps),max(gaps)],
               'standalone_stl_triangle_count_checked':n})
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('REOPEN_AND_MODEL_CHECKS_PASS',flush=True)
