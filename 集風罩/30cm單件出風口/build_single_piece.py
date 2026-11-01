"""Build only the compact air duct and original blower flange, as one mesh."""
from pathlib import Path
import ast,hashlib,json,math,struct
HERE=Path(__file__).resolve().parent
source=HERE.parent/'30cm列印測試版/build_printable_test_hood.py'
# Reuse only the unchanged inlet, loft, bend and nozzle construction.
# Stop before any bypass, pressure pickup, joining lug or split is built.
prefix=source.read_text().split('# Rearward bypass keeps')[0]
exec(compile(prefix,str(source)+'_plain_geometry','exec'),globals())
body.name='單件出風口_240mm弧長_原接口'
collection.name='單件出風口'
bpy.data.collections.remove(alts)
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(body.data);bm.free()
check=solid_check(body)
for p in body.data.polygons:p.use_smooth=True
if hasattr(body.data,'set_sharp_from_angle'):body.data.set_sharp_from_angle(angle=math.radians(32))
body['尺寸單位']='mm'
body['列印方式']='單件；進風法蘭朝下；不分片'
body['進風淨口_mm']=[82.,88.];body['法蘭_mm']=[118.,120.,3.]
body['出風弧長_mm']=240.;body['出風縫_mm']=2.;body['主壁厚_mm']=2.
body['彎角_deg']=90.;body['彎道中心半徑_mm']=28.
body['性能狀態']='短弧測試件；風速及整體阻力尚未實測'
active(body);bpy.context.view_layer.update()
assert len(bpy.data.objects)==1 and body.type=='MESH' and not body.modifiers
for datablocks in [bpy.data.meshes,bpy.data.materials]:
    for data in list(datablocks):
        if data.users==0:datablocks.remove(data)
file=export_stl(body,'單件出風口_直接列印_mm')
bodybounds=bounds(body)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.region_3d.view_location=(0,15,140)
            space.region_3d.view_distance=500
            space.region_3d.view_rotation=Vector((1.3,1.8,.7)).to_track_quat('Z','Y')
            space.shading.type='MATERIAL';space.clip_end=10000
blend=HERE/'30cm單件出風口.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
saved_vertices=len(body.data.vertices);saved_faces=len(body.data.polygons)
bpy.ops.wm.open_mainfile(filepath=str(blend))
assert len(bpy.data.objects)==1
body=next(iter(bpy.data.objects));assert len(body.data.vertices)==saved_vertices and len(body.data.polygons)==saved_faces
solid_check(body)
body.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],
    [tuple(t.vertices) for t in body.data.loop_triangles],all_triangles=True)
assert tree.ray_cast(Vector((0,0,20)),Vector((0,0,-1)),30)[0] is None
gaps=[]
for i in range(1,40):
    u=i/40;a=(2*u-1)*halfangle;p=arc(u,2);p.z=slotZ
    up=tree.ray_cast(p,Vector((0,0,1)),10);down=tree.ray_cast(p,Vector((0,0,-1)),10)
    assert up[0] is not None and down[0] is not None
    gaps.append(up[3]+down[3]);assert abs(gaps[-1]-2)<.003
    assert tree.ray_cast(p,Vector((-math.sin(a),math.cos(a),0)),10)[0] is None
for dy,dz in holes:
    assert tree.ray_cast(Vector((2+dz,dy,-1)),Vector((0,0,1)),5)[0] is None
# Confirm removed fittings leave the original neck/upper walls closed.
for p,d,expected in [(Vector((0,0,38)),Vector((0,-1,0)),44),
                     (Vector((25,0,10)),Vector((0,1,0)),44),
                     (Vector((0,0,215)),Vector((0,-1,0)),h/2)]:
    hit=tree.ray_cast(p,d,100);assert hit[0] is not None and abs(hit[3]-expected)<.01
for p in protected:assert hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p)]
r={'assembled_size_mm':bodybounds['size'],'single_mesh':True,'split':False,
   'has_bypass':False,'has_pressure_pickups':False,'has_joining_lugs':False,
   'mesh':check,'original_blower_inlet_mm':[82,88],'original_flange_mm':[118,120,3],
   'original_mount_holes_preserved':True,'turn_degrees':90,'bend_center_radius_mm':28,
   'slot_span_mm':240,'slit_gap_sample_range_mm':[min(gaps),max(gaps)],
   'saved_blend_reopened_and_checked':True,'original_models_unchanged':True,
   'original_file_hashes':hashes,'STL':file,'blend_file':str(blend),
   'CFD_executed':False,'resistance_or_velocity_match_verified':False}
(HERE/'單件出風口_尺寸檢查.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
tree_ast=ast.parse((HERE.parent/'blender_build_right_hood.py').read_text())
helpers=ast.Module(body=[n for n in tree_ast.body if isinstance(n,ast.FunctionDef) and n.name in {'look','preview'}],type_ignores=[])
exec(compile(helpers,'preview_helpers','exec'))
original_scene=bpy.context.scene
preview([body],.001,(.52,.65,.42),(0,.015,.14),.39,'單件出風口_預覽.png')
print('SINGLE_PIECE_COMPLETE',json.dumps({'size_mm':bodybounds['size'],'slit_gap_mm':r['slit_gap_sample_range_mm']}),flush=True)
