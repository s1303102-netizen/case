"""Add the photographed 150FLJ330W blower without changing existing objects.

All construction coordinates below are mm. The assembly parent scales them by
0.1 because the existing 140 x 50 x 125 model represents centimeters, as
confirmed by the user. Existing scene unit settings are deliberately preserved.
Run with Blender --background 第一版.blend --python this_script.py.
"""
from pathlib import Path
import bpy
import bmesh
import math
import json
import hashlib
import shutil
from mathutils import Vector, Quaternion

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '第一版.blend'
STAGED = HERE / '第一版_鼓風機待驗證.blend'
BACKUP = HERE / '第一版_新增鼓風機前備份.blend'
REPORT = HERE / '鼓風機_尺寸與原物件檢查.json'
TAU = math.tau


def fingerprint(obj):
    result = {'type': obj.type, 'data': obj.data.name if obj.data else None,
              'matrix': [list(row) for row in obj.matrix_world],
              'parent': obj.parent.name if obj.parent else None,
              'collections': sorted(c.name for c in obj.users_collection),
              'hide_viewport': obj.hide_viewport, 'hide_render': obj.hide_render,
              'modifiers': [(m.name, m.type) for m in obj.modifiers]}
    if obj.type == 'MESH':
        payload = {'vertices': [list(v.co) for v in obj.data.vertices],
                   'edges': [list(e.vertices) for e in obj.data.edges],
                   'polygons': [list(p.vertices) for p in obj.data.polygons],
                   'materials': [m.name if m else None for m in obj.data.materials],
                   'material_indices': [p.material_index for p in obj.data.polygons]}
        result['mesh_sha256'] = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        result['counts'] = [len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)]
    elif obj.type == 'LIGHT':
        result['settings'] = [obj.data.type, obj.data.energy, list(obj.data.color), obj.data.shadow_soft_size]
    elif obj.type == 'CAMERA':
        result['settings'] = [obj.data.type, obj.data.lens, obj.data.clip_start, obj.data.clip_end]
    return result


original_scene = bpy.context.scene
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
original_units = {'system': original_scene.unit_settings.system,
                  'scale_length': original_scene.unit_settings.scale_length,
                  'length_unit': original_scene.unit_settings.length_unit}
assert not bpy.data.collections.get('鼓風機_150FLJ330W'), 'Blower already exists; refusing to duplicate it.'
if not BACKUP.exists():
    shutil.copy2(SOURCE, BACKUP)
collection = bpy.data.collections.new('鼓風機_150FLJ330W')
original_scene.collection.children.link(collection)
root = bpy.data.objects.new('鼓風機_總成_公分場景比例', None)
collection.objects.link(root)
root.location = (99.3, -12.0, 0.0)
root.scale = (0.1, 0.1, 0.1)
root.empty_display_type = 'PLAIN_AXES'
root.empty_display_size = 15
root['型號'] = '150FLJ330W（依照片與尺寸圖建模）'
root['來源尺寸單位'] = 'mm'
root['原模型實際單位'] = 'cm（使用者確認）'
root['每毫米場景長度'] = 0.1
root['主要尺寸_mm'] = '側向206 × 軸向242 × 高220；殼寬95；进風Ø120；馬達Ø124'
root['未標示尺寸'] = '板厚、葉輪、散熱鰭片、線材與小五金依照片估計，非製造圖。'


def material(name, color, metal=0.0, rough=0.4):
    mat = bpy.data.materials.new('鼓風機_' + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    return mat


black = material('黑色烤漆鋼板', (0.014, 0.017, 0.021), 0.38, 0.35)
motor_black = material('馬達黑色鋁合金', (0.018, 0.021, 0.026), 0.45, 0.30)
steel = material('銀色鋼絲護網', (0.56, 0.61, 0.65), 0.90, 0.23)
aluminum = material('鋁製離心葉輪', (0.43, 0.48, 0.50), 0.84, 0.30)
rubber = material('橡膠電線', (0.009, 0.011, 0.014), 0, 0.52)
white = material('接線端子', (0.79, 0.80, 0.77), 0, 0.38)
label_mat = material('銀白銘牌', (0.76, 0.77, 0.73), 0.28, 0.43)
ink = material('銘牌字樣', (0.014, 0.019, 0.025), 0, 0.55)
wire_mats = [material('電線_' + name, color, 0, 0.45) for name, color in
             [('黃', (0.88, 0.55, 0.016)), ('藍', (0.018, 0.11, 0.57)), ('紅', (0.53, 0.022, 0.012))]]


def link(obj, mat=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.parent = root
    if mat:
        obj.data.materials.append(mat)
    return obj


def mesh(name, verts, faces, mat=black, smooth=False):
    data = bpy.data.meshes.new('鼓風機_' + name + '_Mesh')
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new('鼓風機_' + name, data)
    link(obj, mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for p in data.polygons:
        p.use_smooth = smooth
    return obj


def bevel(obj, width=0.35, segments=3):
    mod = obj.modifiers.new('折邊與倒角', 'BEVEL')
    mod.width, mod.segments = width, segments
    mod.limit_method = 'ANGLE'
    mod = obj.modifiers.new('金屬面法線', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    return obj


def active(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def box(name, location, size, mat=black, edge=0.3):
    x, y, z = (s / 2 for s in size)
    verts = [(a*x, b*y, c*z) for a, b, c in
             [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
              (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
    obj = mesh(name, verts, [(0,3,2,1), (4,5,6,7), (0,1,5,4),
                            (1,2,6,5), (2,3,7,6), (3,0,4,7)], mat)
    obj.location = location
    if edge:
        bevel(obj, edge)
    return obj


def cylinder(name, center, radius, depth, mat=steel, axis='Y', n=96, edge=0.2):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=radius, depth=depth)
    obj = bpy.context.object
    obj.name = '鼓風機_' + name
    link(obj, mat)
    obj.location = center
    if axis == 'Y':
        obj.rotation_euler.x = math.pi / 2
    elif axis == 'X':
        obj.rotation_euler.y = math.pi / 2
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    if edge:
        bevel(obj, edge)
    return obj


def tube(name, points, radius, mat=steel, cyclic=False, bezier=False):
    curve = bpy.data.curves.new('鼓風機_' + name + '_Curve', 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 16
    curve.bevel_depth, curve.bevel_resolution = radius, 3
    curve.use_fill_caps = True
    spline = curve.splines.new('BEZIER' if bezier else 'POLY')
    if bezier:
        spline.bezier_points.add(len(points)-1)
        for p, coord in zip(spline.bezier_points, points):
            p.co = coord
            p.handle_left_type = p.handle_right_type = 'AUTO'
    else:
        spline.points.add(len(points)-1)
        for p, coord in zip(spline.points, points):
            p.co = (*coord, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new('鼓風機_' + name, curve)
    return link(obj, mat)


def ring(name, radius, y, z=93, wire=0.7, mat=steel, x=0):
    return tube(name, [(x+radius*math.cos(TAU*i/128), y,
                        z+radius*math.sin(TAU*i/128)) for i in range(128)], wire, mat, True)


def lathe_y(name, profile, center=(0,0,93), mat=black, n=128):
    verts = []
    for r, y in profile:
        for i in range(n):
            a = TAU*i/n
            verts.append((center[0]+r*math.cos(a), center[1]+y, center[2]+r*math.sin(a)))
    faces = []
    for j in range(len(profile)-1):
        for i in range(n):
            k = (i+1)%n
            faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
    return mesh(name, verts, faces, mat, True)


def cut(obj, cutter):
    mod = obj.modifiers.new('真實開孔', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    obj.modifiers.move(len(obj.modifiers)-1, 0)
    bpy.context.view_layer.update()
    active(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def rounded_rect(width, height, r, center=(0,0), steps=8):
    points = []
    for cx, cy, start in [(width/2-r, height/2-r, 0), (-width/2+r,height/2-r,90),
                          (-width/2+r,-height/2+r,180), (width/2-r,-height/2+r,270)]:
        for j in range(steps+1):
            a=math.radians(start+90*j/steps)
            points.append((center[0]+cx+r*math.cos(a), center[1]+cy+r*math.sin(a)))
    return points


def extrude(name, profile, low, high, axis='Y', mat=black, edge=0):
    def vertex(u, v, d):
        return (u,d,v) if axis == 'Y' else ((d,u,v) if axis == 'X' else (u,v,d))
    verts = [vertex(u,v,d) for d in (low,high) for u,v in profile]
    n=len(profile)
    faces = [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    obj=mesh(name,verts,faces,mat)
    if edge:
        bevel(obj,edge)
    return obj


def screw(name, center, axis='Y', radius=2.8, mat=steel):
    obj=cylinder(name,center,radius,1.7,mat,axis,n=32,edge=0.25)
    x,y,z=center
    # Recessed cross rendered as dark narrow inserts.
    if axis=='Y':
        face_y=y-0.91 if y<0 else y+0.91
        box(name+'_十字槽橫',(x,face_y,z),(radius*1.2,0.07,0.46),rubber,0.08)
        box(name+'_十字槽直',(x,face_y,z),(0.46,0.07,radius*1.2),rubber,0.08)
    elif axis=='Z':
        box(name+'_槽',(x,y,z+0.91),(radius*1.25,0.55,0.08),rubber,0.08)
    return obj


# Smooth volute outline: 186 mm body silhouette, 204 mm body height.
def cubic(a,b,c,d,steps=16):
    pts=[]
    for i in range(steps):
        t=i/steps; s=1-t
        pts.append((s*s*s*a[0]+3*s*s*t*b[0]+3*s*t*t*c[0]+t*t*t*d[0],
                    s*s*s*a[1]+3*s*s*t*b[1]+3*s*t*t*c[1]+t*t*t*d[1]))
    return pts


segments=[((110,204),(86,204),(50,204),(20,204)),
          ((20,204),(-48,204),(-93,162),(-93,102)),
          ((-93,102),(-93,44),(-55,0),(0,0)),
          ((0,0),(51,0),(93,36),(93,89)),
          ((93,89),(93,99),(93,110),(93,118)),
          ((93,118),(100,118),(106,118),(110,118))]
outline=[p for segment in segments for p in cubic(*segment)]+[(110,118)]
front=extrude('蝸殼_進風側板',outline,-47.5,-45.9)
cut(front,cylinder('暫用_進風孔',(0,-46.7,93),60,12,None,edge=0))
bevel(front,0.28)
front['進風孔直徑_mm']=120.0
rear=extrude('蝸殼_馬達側板',outline,45.9,47.5,edge=0.28)
cut(rear,cylinder('暫用_軸孔',(0,46.7,93),12,12,None,edge=0))
rear['殼體軸向寬度_mm']=95.0

# A folded sheet follows the profile, with the rectangular outlet left open.
verts=[]
for i,(x,z) in enumerate(outline):
    prev=Vector(outline[max(0,i-1)]); nxt=Vector(outline[min(len(outline)-1,i+1)])
    tangent=(nxt-prev).normalized()
    inward=Vector((-tangent.y,tangent.x))
    for y,d in [(-45.9,0),(45.9,0),(-45.9,1.6),(45.9,1.6)]:
        verts.append((x+inward.x*d,y,z+inward.y*d))
faces=[]
for i in range(len(outline)-1):
    a=i*4;b=(i+1)*4
    faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),
                  (a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
faces += [(0,1,3,2),(len(verts)-4,len(verts)-2,len(verts)-1,len(verts)-3)]
bevel(mesh('蝸殼_連續曲面折板',verts,faces,black,True),0.22)
for y in (-46.5,46.5):
    seam=[]
    for i,(x,z) in enumerate(outline):
        tangent=(Vector(outline[min(len(outline)-1,i+1)])-
                 Vector(outline[max(0,i-1)])).normalized()
        seam.append((x-tangent.y*0.75,y,z+tangent.x*0.75))
    tube('蝸殼_折邊接縫_'+str(y),seam,0.65,black)

# Outlet plate 120 x 118; aperture 88 x 82; hole pitches 102, 100, 50.
flange=extrude('出風口_120x118法蘭',rounded_rect(120,118,4,(-1.5,161)),111,113,'X')
opening=extrude('暫用_88x82出風口',rounded_rect(88,82,3,(-1.5,159)),106,117,'X',None)
cut(flange,opening)
hole_positions=[(-51,50),(51,50),(-51,-50),(51,-50),
                (-25,50),(25,50),(-25,-50),(25,-50),
                (-51,-25),(-51,25),(51,-25),(51,25)]
for i,(dy,dz) in enumerate(hole_positions):
    cut(flange,cylinder('暫用_法蘭孔'+str(i),(112,-1.5+dy,161+dz),
                        3.2 if abs(dy)==51 and abs(dz)==50 else 2.2,10,None,'X',32,0))
bevel(flange,0.38)
flange['外框_mm']=[120.0,118.0]
flange['開口_mm']=[88.0,82.0]
flange['孔距_mm']=[102.0,100.0,50.0]
box('出風口_上緣風道',(110.6,-1.5,201),(2.6,91,2),black,0.2)
box('出風口_下緣風道',(110.6,-1.5,117),(2.6,91,2),black,0.2)

# Rolled intake lip, real opening, and 110 mm square guard mounting pattern.
lathe_y('進風口_捲邊圓環',[(60,-45.9),(60,-48.5),(61,-50),(63,-50),(65,-48),(65,-47.5)],mat=black)
for i,(x,dz) in enumerate([(-55,-55),(-55,55),(55,-55),(55,55)]):
    cylinder('護網_螺絲座'+str(i),(x,-48.1,93+dz),4.5,2.3,black,edge=0.2)
    screw('護網_固定螺絲'+str(i),(x,-52.5,93+dz),radius=3.1)
for i,r in enumerate([8,16,24,32,40,48,56,64,69]):
    ring('進風護網_同心圈%02d'%i,r,-51.5-6*(1-(r/72)**2),wire=0.68)
for i,a in enumerate([math.pi/4,3*math.pi/4]):
    pts=[]
    for j in range(41):
        r=-math.sqrt(2)*55+2*math.sqrt(2)*55*j/40
        pts.append((r*math.cos(a),-51.5-6*max(0,1-(abs(r)/72)**2),93+r*math.sin(a)))
    tube('進風護網_十字支撐'+str(i),pts,0.85)

# Forward-curved centrifugal wheel, separate aluminum blades visible in outlet.
lathe_y('葉輪_前端環',[(42,-39),(73,-39),(73,-37.5),(42,-37.5)],mat=aluminum)
lathe_y('葉輪_後端盤',[(12,37.5),(73,37.5),(73,39),(12,39)],mat=aluminum)
lathe_y('葉輪_中心導流輪轂',[(0,-43),(10,-43),(18,-39),(25,-30),(32,-22),(37,-18)],mat=aluminum)
cylinder('葉輪_中心軸帽',(0,-44,93),7.0,2.0,steel,edge=0.4)
for i in range(36):
    angle=TAU*i/36
    section=[]
    for j in range(9):
        t=j/8
        r=59+14*t
        a=angle+0.18*t*t
        section.append((r*math.cos(a),93+r*math.sin(a)))
    section += [(x+0.8*math.cos(angle+math.pi/2),z+0.8*math.sin(angle+math.pi/2))
                for x,z in reversed(section)]
    blade=extrude('離心葉輪_葉片%02d'%i,section,-37.5,37.5,mat=aluminum,edge=0.15)
    blade['尺寸依據']='葉輪內部細節依照片估計'

# Motor mounting ring, shaft and cooling fins.
lathe_y('馬達_固定圓盤',[(12,47.6),(49,47.6),(49,51),(42,54),(12,54)],mat=black)
lathe_y('馬達_銀色端蓋',[(11,51),(43,51),(46,55),(46,58),(11,58)],mat=aluminum)
cylinder('馬達_驅動軸',(0,8,93),10,100,steel,edge=0.4)
for i in range(4):
    a=math.pi/4+i*math.pi/2
    screw('馬達_蝸殼鎖固'+str(i),(68*math.cos(a),48.6,93+68*math.sin(a)),radius=2.7)
cylinder('馬達_圓柱本體',(0,101,93),50,90,motor_black,edge=0.8)
for i in range(32):
    a=TAU*i/32
    fin=box('馬達_散熱鰭片%02d'%i,(54*math.cos(a),102,93+54*math.sin(a)),
            (8,89,1.45),motor_black,0.22)
    fin.rotation_euler.y=-a
lathe_y('馬達_後端散熱罩',[(56,145),(61,147),(62,154),(62,162),
                          (60,171),(56,177),(51,180.5),(47,180.5),(50,176),
                          (54,169),(57,160),(57,149),(56,145)],mat=motor_black)
cap=cylinder('馬達_後端通風格柵',(0,179.7,93),50,1.6,black,n=128,edge=0)
for row in range(-4,5):
    for col in range(-4,5):
        x=col*9.5; z=93+row*9.5
        if x*x+(z-93)**2 < 40**2:
            cutter=box('暫用_馬達通風孔',(x,179.7,z),(5.2,8,6.4),None,0)
            cut(cap,cutter)
bevel(cap,0.25)
lathe_y('馬達_後罩折邊',[(48,177.3),(50,177.3),(50,180.5),(48,180.5)],mat=black)
for i in range(8):
    a=TAU*i/8
    fan=box('馬達_後端冷卻葉片'+str(i),(25*math.cos(a),174,93+25*math.sin(a)),
            (25,2,5),aluminum,0.2)
    fan.rotation_euler.y=-a
for i in range(3):
    a=math.pi/2+i*TAU/3
    screw('馬達_後罩螺絲'+str(i),(60*math.cos(a),152,93+60*math.sin(a)),radius=2.8)
root['馬達直徑_mm']=124.0

# 80 mm mounting foot, with real bolt holes and folded inclined supports.
foot=extrude('底座_80mm長安裝腳',rounded_rect(82,80,7,(0,98.5)),0,3,'Z')
for x in (-33,33):
    for y in (66.5,130.5):
        cut(foot,cylinder('暫用_腳座安裝孔',(x,y,1.5),3.3,12,None,'Z',32,0))
bevel(foot,0.4)
foot['軸向長度_mm']=80.0
for side in (-1,1):
    coords=[(side*35,3),(side*28,3),(side*18,37),(side*22,43),(side*26,36)]
    support=extrude('底座_折彎支架'+str(side),coords,76,121,mat=black,edge=0.5)
    cut(support,cylinder('暫用_支架螺孔',(side*29,98.5,17),2.3,25,None,'X',32,0))
box('底座_馬達承接座',(0,98.5,37),(37,49,4),black,0.7)
for x in (-12,12):
    screw('底座_承接螺絲'+str(x),(x,85,40),axis='Z',radius=2.8)

# Photo-based wiring details; kept inside the main envelope except cable/plug.
cylinder('接線_橡膠出線套',(34,67,54),5,9,rubber,'X',edge=0.8)
for i,mat in enumerate(wire_mats):
    pts=[(38,67+i*1.8,54),(48,66+i*2,47),(53+i*2,71,30),(53+i*2,77,21)]
    tube('接線_彩色導線'+str(i),pts,0.9,mat,bezier=True)
    tube('接線_白色絕緣端子'+str(i),[(53+i*2,76,22),(53+i*2,82,19)],2,white)
box('接線_黑色電容盒',(53,105,11),(22,47,17),rubber,2)
tube('接線_束線帶',[(49,71,27),(63,72,26),(63,76,27),(49,75,29)],0.55,white,True)
tube('接線_束線帶尾端',[(63,72,26),(81,86,14)],0.55,white)
tube('電源線_彎曲線材',[(52,104,16),(65,109,7),(84,135,3.6),(81,157,3.6),
                         (39,166,3.6),(24,146,3.6),(53,138,3.6)],2.1,rubber,bezier=True)
plug=box('電源插頭_黑色本體',(52,128,7),(16,20,11),rubber,2)
for i,x in enumerate((48,56)):
    box('電源插頭_雙扁插腳'+str(i),(x,111.5,7),(1.3,13,5.5),steel,0.15)

# Plate on the upper shell. Only the known model/power is written as a value.
plate=box('機身_型號銘牌',(55,0,204.13),(43,34,0.22),label_mat,0.9)
for y in (-10,-5,1,7,12):
    box('銘牌_表格橫線'+str(y),(55,y,204.29),(38,0.18,0.035),ink,0)
for x in (36,48,74):
    box('銘牌_表格直線'+str(x),(x,1,204.29),(0.18,24,0.035),ink,0)
def label(body,loc,size):
    curve=bpy.data.curves.new('鼓風機_銘牌文字','FONT')
    curve.body=body; curve.size=size; curve.align_x='CENTER'
    curve.align_y='CENTER'; curve.extrude=0
    obj=bpy.data.objects.new('鼓風機_銘牌_'+body,curve)
    link(obj,ink); obj.location=loc
    return obj
label('150FLJ330W',(55,-13,204.33),3.6)
label('330 W',(60,-7,204.33),2.8)
label('CENTRIFUGAL BLOWER',(55,10,204.33),1.8)

# Collection-level separation and exact geometry bounds in millimeters.
bpy.context.view_layer.update()
assert all(fingerprint(bpy.data.objects[name])==fp for name,fp in originals.items())
bounds=[]
for obj in collection.objects:
    if obj.type in {'MESH','CURVE','FONT'}:
        for corner in obj.bound_box:
            bounds.append(root.matrix_world.inverted() @ obj.matrix_world @ Vector(corner))
mins=[min(v[i] for v in bounds) for i in range(3)]
maxs=[max(v[i] for v in bounds) for i in range(3)]
report={'原物件檢查':{'全部保持原樣':True,'物件':originals},
        '原場景單位設定':original_units,
        '換算':{'原模型實際單位':'cm','圖面單位':'mm','每mm場景座標':0.1},
        '鼓風機':{'集合':collection.name,'物件數':len(collection.objects),
                  '位置_cm':list(root.location),'尺寸_mm':{'側面總寬':206,'側面總高':220,
                  '軸向總長':242,'殼體寬':95,'進風直徑':120,'馬達直徑':124,
                  '法蘭寬':120,'法蘭高':118,'出風口寬':88,'出風口高':82,
                  '進風護網螺絲孔距':110,'底座軸向長':80},
                  '實際零件包絡_mm':{'min':mins,'max':maxs,'size':[maxs[i]-mins[i] for i in range(3)]},
                  '原物體右側間隙_cm':root.location.x+mins[0]*0.1-70,
                  '未標示尺寸':'板厚、內部葉片、散熱鰭片、線材、細部螺孔依照片估計。'},
        '備份檔案':str(BACKUP),'已驗證儲存後原物件':False}

# Convenient opening view: blower close-up with the original object's side nearby.
for obj in original_scene.objects:
    obj.select_set(False)
root.select_set(True)
bpy.context.view_layer.objects.active=root
direction=Vector((1.05,-1.7,0.85))
rotation=direction.to_track_quat('Z','Y')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_location=(96,-7,11)
            space.region_3d.view_distance=59
            space.region_3d.view_rotation=rotation
            space.region_3d.view_perspective='PERSP'
            space.clip_end=max(space.clip_end,1000)
            space.shading.type='MATERIAL'
            space.shading.studiolight_rotate_z=0.45
bpy.ops.wm.save_as_mainfile(filepath=str(STAGED))
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLOWER_MODEL_SAVED',json.dumps(report['鼓風機'],ensure_ascii=False))

# Render previews in a temporary scene; original cameras, lights and world stay intact.
preview=bpy.data.scenes.new('鼓風機_臨時預覽場景')
preview.collection.children.link(collection)
bpy.context.window.scene=preview
preview.render.engine='CYCLES'
preview.cycles.device='CPU'
preview.cycles.samples=40
preview.cycles.use_denoising=True
preview.render.resolution_x=1300
preview.render.resolution_y=1100
preview.render.resolution_percentage=100
preview.render.image_settings.file_format='PNG'
preview.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('鼓風機_預覽世界')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.34,0.39,0.45,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.35
preview.world=world


def worldpos(mm):
    return root.matrix_world @ Vector(mm)


def preview_object(name,data):
    obj=bpy.data.objects.new(name,data)
    preview.collection.objects.link(obj)
    return obj


cam=preview_object('鼓風機_預覽相機',bpy.data.cameras.new('鼓風機_預覽相機'))
preview.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=34.5
cam.data.clip_end=10000
def look(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for name,pos,energy,size in [('主光',(120,-240,420),42000,32),
                             ('柔光',(-240,-80,190),19000,25),
                             ('輪廓光',(40,330,320),53000,24)]:
    data=bpy.data.lights.new('鼓風機_預覽'+name,'AREA')
    data.energy=energy; data.shape='DISK';data.size=size
    obj=preview_object('鼓風機_預覽'+name,data)
    obj.location=worldpos(pos);look(obj,worldpos((0,45,100)))
grounddata=bpy.data.meshes.new('鼓風機_預覽地面')
grounddata.from_pydata([(-5000,-5000,-0.04),(5000,-5000,-0.04),(5000,5000,-0.04),(-5000,5000,-0.04)],[],[(0,1,2,3)])
ground=preview_object('鼓風機_預覽地面',grounddata)
ground.matrix_world=root.matrix_world.copy()
groundmat=material('預覽背景',(0.19,0.22,0.25),0.15,0.6)
ground.data.materials.append(groundmat)
for filename,pos in [('鼓風機_進風側預覽.png',(380,-490,320)),
                     ('鼓風機_馬達側預覽.png',(390,460,315))]:
    cam.location=worldpos(pos)
    look(cam,worldpos((5,45,103)))
    preview.render.filepath=str(HERE/filename)
    bpy.ops.render.render(write_still=True)
bpy.context.window.scene=original_scene
print('BLOWER_PREVIEWS_COMPLETE')
