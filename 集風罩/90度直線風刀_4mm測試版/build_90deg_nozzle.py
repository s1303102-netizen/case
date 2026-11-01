"""Build a standalone single-piece 216 x 4 mm, 90-degree test nozzle in mm.

Geometry checks only: these are not airflow simulations or measured performance.
"""
from pathlib import Path
from array import array
import ast, bpy, bmesh, math, json, hashlib, struct
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
N = 256
WALL = 2.0
W = 216.0
GAP = 4.0
NECK = 12.0
TRANSITION = 145.0
BEND_Z = NECK + TRANSITION
R = 70.0
BEND_DEPTH = 28.0
CONTRACTION = 50.0
LIP = 10.0
OUTLET_Y = R + CONTRACTION + LIP
BEND_EXIT_Z = BEND_Z + R
OUTLET_Z = BEND_EXIT_Z + (BEND_DEPTH-GAP)/2
NAME = '90度直線風刀_216x4mm'

# Reuse the verified source's interface and mesh utilities, without running it.
source = HERE.parent/'直通長型風刀測試版/build_straight_nozzles.py'
tree = ast.parse(source.read_text())
names = {'ease','rect','mesh','loft','solid_surface','boolean','material',
         'dims','polygon_area','geohash','verify_mesh','bvh','export_stl'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name in names], type_ignores=[]), str(source), 'exec'))

protected = [ROOT/'第一版.blend', ROOT/'完整模型.blend',
             HERE.parent/'直通長型風刀測試版/直通風刀_216x4mm.blend',
             HERE.parent/'直通長型風刀測試版/STL_毫米/直通風刀_216x4mm_單件_mm.stl']
hashfile = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
hashes = {str(p): hashfile(p) for p in protected if p.exists()}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
s = bpy.context.scene
s.unit_settings.system = 'METRIC'
s.unit_settings.scale_length = .001
s.unit_settings.length_unit = 'MILLIMETERS'
mat = material()
outer, inner, stations = [], [], []

def add_section(stage, center, theta, width, depth, corner):
    c = Vector(center)
    normal = Vector((0, math.cos(theta), -math.sin(theta)))
    tangent = Vector((0, math.sin(theta), math.cos(theta)))
    def mapped(points):
        return [c + Vector((p.x, 0, 0)) + normal*p.y for p in points]
    ri = rect(width, depth, corner)
    inner.append(mapped(ri))
    outer.append(mapped(rect(width+2*WALL, depth+2*WALL, corner+WALL)))
    stations.append({'stage':stage, 'center_mm':list(c),
        'tangent':list(tangent), 'depth_normal':list(normal),
        'angle_deg':math.degrees(theta), 'width_mm':width,
        'depth_mm':depth, 'area_mm2':polygon_area(ri)})

for z in [0, 3, NECK]:
    add_section('original_inlet', (0,0,z), 0, 82,88,3)

# Width grows before the bend. Prescribe declining area, then derive depth.
for j in range(1,121):
    t = ease(j/120)
    width = 82+(W-82)*t
    nominal_area = 82*88+(W*BEND_DEPTH-82*88)*t
    add_section('width_distribution', (0,0,NECK+TRANSITION*j/120),
                0, width, nominal_area/width, 3*(1-t))

# Constant-section tangent 90-degree sweep; inner bend wall radius is 56 mm.
for j in range(1,97):
    theta = math.pi/2*j/96
    center = (0, R*(1-math.cos(theta)), BEND_Z+R*math.sin(theta))
    add_section('90_degree_bend', center, theta, W, BEND_DEPTH, 0)

for j in range(1,61):
    t = ease(j/60)
    depth = BEND_DEPTH+(GAP-BEND_DEPTH)*t
    # Keep the upper air wall level with the top of the bend, with no roof recess.
    center_z = BEND_EXIT_Z+(BEND_DEPTH-depth)/2
    add_section('final_contraction', (0,R+CONTRACTION*j/60,center_z),
                math.pi/2, W, depth, 0)
add_section('straight_outlet_lip', (0,OUTLET_Y,OUTLET_Z), math.pi/2, W,GAP,0)

areas = [a['area_mm2'] for a in stations]
assert max(b-a for a,b in zip(areas,areas[1:])) < .002
assert R > BEND_DEPTH/2 + WALL
o = solid_surface(outer,inner,mat)
flange = loft('暫用_原法蘭', [[p+Vector((0,0,z)) for p in
               rect(118,120,4,cx=2)] for z in [0,3]],mat)
boolean(o,flange,'UNION')
cut = loft('暫用_原入口',[[p+Vector((0,0,z)) for p in rect(82,88,3)]
                          for z in [-2,4]])
boolean(o,cut,'DIFFERENCE')
holes = [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),
         (-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]
for dy,dz in holes:
    radius = 3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
    circles = [[Vector((2+dz+radius*math.cos(2*math.pi*j/64),
                        dy+radius*math.sin(2*math.pi*j/64),z))
                for j in range(64)] for z in [-1,5]]
    boolean(o,loft('暫用_原安裝孔',circles),'DIFFERENCE')
o.name = NAME+'_完整單件'
o.data.name = o.name+'_Mesh'
check = verify_mesh(o)
bounds = dims(o)
assert all(abs(a-b)<.001 for a,b in zip(bounds['size'],[220,190,243])), bounds
assert bounds['size'][0]<=220.001 and bounds['size'][2]<=250
o['淨出風口_mm'] = [W,GAP]
o['最大外形_寬深高_mm'] = bounds['size']
o['進風淨口_mm'] = [82,88]
o['原法蘭_mm'] = [118,120,3]
o['轉向'] = '從 +Z 向上進風，轉 90 度，從 +Y 水平吹出'
o['彎管中心半徑_mm'] = R
o['彎管內側流道半徑_mm'] = R-BEND_DEPTH/2
o['彎管流道截面_mm'] = [W,BEND_DEPTH]
o['主截面壁厚_mm'] = WALL
o['出口'] = '216 mm 直線，4 mm 等縫；不是圓弧；出口在最前緣、沒有縮短長度'
o['列印'] = '完整單件；毫米100%；彎道支撐須在切片時檢查能否取出'
o['驗證範圍'] = '僅幾何與網格檢查；未做CFD、風速、均勻度或實體列印驗證'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            view = area.spaces.active
            view.region_3d.view_location = (0,25,120)
            view.region_3d.view_distance = 470
            view.region_3d.view_rotation = Vector((1.4,1.8,1)).to_track_quat('Z','Y')
            view.shading.type = 'MATERIAL'
            view.clip_end = 10000
for q in bpy.context.selected_objects:
    q.select_set(False)
o.select_set(True)
bpy.context.view_layer.objects.active = o
blend = HERE/(NAME+'.blend')
stl = HERE/(NAME+'_單件_mm.stl')
expected = geohash(o)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
export_stl(o,stl)
bpy.ops.wm.open_mainfile(filepath=str(blend))
assert len(bpy.data.objects)==1
o = next(iter(bpy.data.objects))
assert geohash(o)==expected
tree = bvh(o)

# Slot length/gap and horizontal outlet are checked independently of the sweep.
gaps = []
for j in range(43):
    x = -W/2+.5+(W-1)*j/42
    p = Vector((x,OUTLET_Y-.5,OUTLET_Z))
    up = tree.ray_cast(p,Vector((0,0,1)),10)
    down = tree.ray_cast(p,Vector((0,0,-1)),10)
    assert up[0] is not None and down[0] is not None
    gaps.append(up[3]+down[3])
    assert abs(gaps[-1]-GAP)<.005
    assert tree.ray_cast(p,Vector((0,1,0)),2)[0] is None
for dy,dz in holes:
    assert tree.ray_cast(Vector((2+dz,dy,-1)),Vector((0,0,1)),5)[0] is None

# Geometric clearance of 19 widthwise paths; these are not computed streamlines.
path_count = 0
for k in range(19):
    fraction = -.98+1.96*k/18
    points = [Vector(a['center_mm'])+Vector((fraction*a['width_mm']/2,0,0))
              for a in stations]
    for a,b in zip(points,points[1:]):
        v = b-a
        assert tree.ray_cast(a,v.normalized(),v.length*.99999)[0] is None, (k,a,b)
    path_count += 1

# Gap checks at intermediate sections catch accidental caps or inner obstructions.
section_gap_errors = []
for j in list(range(0,len(stations)-1,7))+[len(stations)-2]:
    a,b = stations[j:j+2]
    c = (Vector(a['center_mm'])+Vector(b['center_mm']))/2
    normal = (Vector(a['depth_normal'])+Vector(b['depth_normal'])).normalized()
    positive = tree.ray_cast(c,normal,150)
    negative = tree.ray_cast(c,-normal,150)
    assert positive[0] is not None and negative[0] is not None, (j,a['stage'],list(c))
    err = abs(positive[3]+negative[3]-(a['depth_mm']+b['depth_mm'])/2)
    section_gap_errors.append(err)
assert max(section_gap_errors)<.02, max(section_gap_errors)
for p,h in hashes.items():
    assert hashfile(p)==h
report = {'date':'2026-11-01','variant':'216 x 4 mm straight slot / 90-degree turn',
    'blend':str(blend),'STL':str(stl),'bounds_mm':bounds,'mesh':check,
    'saved_blend_reopened':True,'net_outlet_mm':[W,GAP],'outlet_area_mm2':W*GAP,
    'outlet_center_mm':[0,OUTLET_Y,OUTLET_Z],'outlet_normal':[0,1,0],
    'inlet_normal':[0,0,1],'direction_change_deg':90,
    'original_inlet_mm':[82,88],'original_flange_mm':[118,120,3],
    'original_hole_count':len(holes),'all_mounting_holes_clear':True,
    'neck_mm':NECK,'width_transition_height_mm':TRANSITION,
    'bend_center_radius_mm':R,'bend_inner_air_radius_mm':R-BEND_DEPTH/2,
    'bend_outer_air_radius_mm':R+BEND_DEPTH/2,'bend_section_mm':[W,BEND_DEPTH],
    'bend_hydraulic_diameter_mm':2*W*BEND_DEPTH/(W+BEND_DEPTH),
    'contraction_length_mm':CONTRACTION,'terminal_straight_mm':LIP,
    'contraction_style':'level upper air wall; lower wall rises smoothly; upper lip not recessed',
    'nominal_cross_section_wall_mm':WALL,'cross_section_area_nonincreasing':True,
    'slot_gap_range_mm':[min(gaps),max(gaps)],'slot_sample_count':len(gaps),
    'all_sampled_horizontal_exit_paths_clear':True,
    'clear_widthwise_geometric_paths':path_count,
    'geometric_paths_are_not_simulated_streamlines':True,
    'max_sampled_section_gap_error_mm':max(section_gap_errors),
    'source_hashes':hashes,'source_files_unchanged':True,
    'blend_sha256':hashfile(blend),'STL_sha256':hashfile(stl),
    'CFD_executed':False,'airflow_uniformity_or_speed_validated':False,
    'physical_print_validated':False,'sections':stations}
(HERE/'尺寸與流道檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('90_DEG_NOZZLE_COMPLETE',json.dumps({k:report[k] for k in
      ['bounds_mm','mesh','slot_gap_range_mm','clear_widthwise_geometric_paths']},ensure_ascii=False),flush=True)
