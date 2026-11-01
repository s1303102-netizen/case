"""Use the old 20 cm thin-bend / symmetric 7-degree nozzle profile.

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
TRANSITION = 153.0
PRE_BEND_STRAIGHT = 20.0
BEND_Z = NECK + TRANSITION + PRE_BEND_STRAIGHT
R = 28.0
SPEC = json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
BEND_DEPTH = SPEC['pre_nozzle_height_mm']
HALF_ANGLE_DEG = 7.0
BLEND = 6.0
CONTRACTION = (BEND_DEPTH-GAP)/(2*math.tan(math.radians(HALF_ANGLE_DEG)))+BLEND
LIP = 4.0
FRAME_DEPTH = 2.0
FRAME_HALF_HEIGHT = 10.0
BODY_END_Y = R + CONTRACTION + LIP
OUTLET_Y = BODY_END_Y + FRAME_DEPTH
BEND_EXIT_Z = BEND_Z + R
OUTLET_Z = BEND_EXIT_Z
NAME = '90度直線風刀_216x4mm_原20cm剖面'

# Reuse the verified source's interface and mesh utilities, without running it.
source = HERE.parent/'直通長型風刀測試版/build_straight_nozzles.py'
tree = ast.parse(source.read_text())
names = {'ease','rect','mesh','loft','solid_surface','boolean','material',
         'dims','polygon_area','geohash','verify_mesh','bvh','export_stl'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name in names], type_ignores=[]), str(source), 'exec'))

protected = [ROOT/'第一版.blend', ROOT/'完整模型.blend',
             HERE.parent/'直通長型風刀測試版/直通風刀_216x4mm.blend',
             HERE.parent/'直通長型風刀測試版/STL_毫米/直通風刀_216x4mm_單件_mm.stl',
             HERE.parent/'20cm單件出風口_平順改善版/20cm單件出風口_平順改善版.blend',
             HERE.parent/'20cm單件出風口_平順改善版/平順改善版_單件出風口_直接列印_mm.stl',
             HERE.parent/'90度直線風刀_4mm測試版/90度直線風刀_216x4mm.blend']
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

# The improved 20 cm part's eased quadratic thinning schedule, retuned for W216.
DEPTH_B = 144.0
DEPTH_C = DEPTH_B-88+BEND_DEPTH
for j in range(1,121):
    t = ease(j/120)
    width = 82+(W-82)*t
    depth = 88-DEPTH_B*t+DEPTH_C*t*t
    add_section('width_distribution', (0,0,NECK+TRANSITION*j/120),
                0, width, depth, 3*(1-t))
for j in range(1,13):
    add_section('thin_pre_bend_straight',
                (0,0,NECK+TRANSITION+PRE_BEND_STRAIGHT*j/12),0,W,BEND_DEPTH,0)

# Same R28 / 12.173-mm thin passage as the earlier Airblade-inspired 20 cm part.
for j in range(1,97):
    theta = math.pi/2*j/96
    center = (0, R*(1-math.cos(theta)), BEND_Z+R*math.sin(theta))
    add_section('90_degree_bend', center, theta, W, BEND_DEPTH, 0)

def contraction_integral(x):
    if x<=0:return 0.0
    if x>=CONTRACTION:return CONTRACTION-BLEND
    if x<BLEND:
        t=x/BLEND
        return BLEND*(t**3-.5*t**4)
    if x<=CONTRACTION-BLEND:return x-BLEND/2
    t=(x-CONTRACTION+BLEND)/BLEND
    return CONTRACTION-1.5*BLEND+BLEND*(t-t**3+.5*t**4)

for j in range(1,81):
    distance = CONTRACTION*j/80
    depth = BEND_DEPTH-2*math.tan(math.radians(HALF_ANGLE_DEG))*contraction_integral(distance)
    add_section('symmetric_7deg_contraction', (0,R+distance,OUTLET_Z),
                math.pi/2, W, depth, 0)
add_section('straight_outlet_lip', (0,BODY_END_Y,OUTLET_Z), math.pi/2, W,GAP,0)

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
# Integrated straight knife-face, like the previous 20 cm model. Its inner edge
# remains exactly at +/- 2 mm; no rounded ramp or ledge intrudes into the slot.
frame = loft('暫用_一體刀口面',[[Vector((p.x,y,OUTLET_Z+p.y))
    for p in rect(W+2*WALL,2*FRAME_HALF_HEIGHT,0)]
    for y in [BODY_END_Y-.5,OUTLET_Y]],mat)
boolean(o,frame,'UNION')
frame_cut = loft('暫用_直線刀口淨孔',[[Vector((p.x,y,OUTLET_Z+p.y))
    for p in rect(W,GAP,0)] for y in [BODY_END_Y-.6,OUTLET_Y+1]])
boolean(o,frame_cut,'DIFFERENCE')
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
expected_size = [220,OUTLET_Y+60,OUTLET_Z+FRAME_HALF_HEIGHT]
assert all(abs(a-b)<.001 for a,b in zip(bounds['size'],expected_size)), bounds
assert bounds['size'][0]<=220.001 and bounds['size'][2]<=250
o['淨出風口_mm'] = [W,GAP]
o['最大外形_寬深高_mm'] = bounds['size']
o['進風淨口_mm'] = [82,88]
o['原法蘭_mm'] = [118,120,3]
o['轉向'] = '從 +Z 向上進風，轉 90 度，從 +Y 水平吹出'
o['彎管中心半徑_mm'] = R
o['彎管內側流道半徑_mm'] = R-BEND_DEPTH/2
o['彎管流道截面_mm'] = [W,BEND_DEPTH]
o['構造參考'] = '上一版20cm：先變薄，R28轉90度，末端上下對稱緩收；不復刻Dyson原廠尺寸'
o['末段兩壁最大半角_deg'] = HALF_ANGLE_DEG
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

nozzle_sections = [a for a in stations if a['stage']=='symmetric_7deg_contraction']
nozzle_sections.insert(0,next(a for a in reversed(stations) if a['stage']=='90_degree_bend'))
wall_angles = [math.degrees(math.atan(abs(b['depth_mm']-a['depth_mm'])/2/
               (b['center_mm'][1]-a['center_mm'][1])))
               for a,b in zip(nozzle_sections,nozzle_sections[1:])]
assert max(wall_angles)<=HALF_ANGLE_DEG+.001
assert abs(nozzle_sections[-1]['depth_mm']-GAP)<1e-6

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
report = {'date':'2026-11-01','variant':'Old 20cm thin-bend / symmetric nozzle; straight 216 x 4 mm outlet',
    'blend':str(blend),'STL':str(stl),'bounds_mm':bounds,'mesh':check,
    'saved_blend_reopened':True,'net_outlet_mm':[W,GAP],'outlet_area_mm2':W*GAP,
    'outlet_center_mm':[0,OUTLET_Y,OUTLET_Z],'outlet_normal':[0,1,0],
    'inlet_normal':[0,0,1],'direction_change_deg':90,
    'original_inlet_mm':[82,88],'original_flange_mm':[118,120,3],
    'original_hole_count':len(holes),'all_mounting_holes_clear':True,
    'neck_mm':NECK,'width_transition_height_mm':TRANSITION,
    'pre_bend_straight_mm':PRE_BEND_STRAIGHT,
    'bend_center_radius_mm':R,'bend_inner_air_radius_mm':R-BEND_DEPTH/2,
    'bend_outer_air_radius_mm':R+BEND_DEPTH/2,'bend_section_mm':[W,BEND_DEPTH],
    'bend_hydraulic_diameter_mm':2*W*BEND_DEPTH/(W+BEND_DEPTH),
    'contraction_length_mm':CONTRACTION,'terminal_straight_mm':LIP,
    'contraction_style':'symmetric upper and lower walls; 7-degree maximum half angle; 6-mm tangent blends',
    'nozzle_wall_max_half_angle_deg':max(wall_angles),
    'nozzle_blend_length_each_mm':BLEND,'integrated_knife_face_depth_mm':FRAME_DEPTH,
    'integrated_knife_face_total_height_mm':2*FRAME_HALF_HEIGHT,
    'original_20cm_cross_section_reference':True,
    'patent_reference':'https://patents.google.com/patent/EP1909627B1/en',
    'patent_usage':'symmetric converging nozzle principle only; R28 and 12.173mm are project dimensions, not Dyson dimensions',
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
