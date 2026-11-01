"""Read original Blender meshes; measure millimetres and project visible CAD edges."""
from pathlib import Path
import bpy,bmesh,math,json,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;SOURCE=ROOT/'第一版.blend'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();before=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
spec=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
arc=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']
R=arc['fitted_arc_radius_mm'];CY=arc['fitted_arc_center_Y_mm'];Z=arc['opening_center_Z_mm']
t0,t1=map(math.radians,arc['arc_theta_degrees']);tf=(t0+t1)/2
out=Vector((-math.sin(tf),-math.cos(tf),0));tangent=Vector((-math.cos(tf),math.sin(tf),0))
def bb(points):
    lo=[min(v[i] for v in points) for i in range(3)];hi=[max(v[i] for v in points) for i in range(3)]
    return {'min':lo,'max':hi,'size':[b-a for a,b in zip(lo,hi)]}
iso=Vector((1.4,-1.8,1.1)).normalized();iu=Vector((0,0,1)).cross(iso).normalized();iv=iso.cross(iu)
views={'front':(Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0))),
    'side':(Vector((0,1,0)),Vector((0,0,1)),Vector((1,0,0))),
    'top':(Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))),
    'iso':(iu,iv,iso)}
report={'source':str(SOURCE),'source_sha256':before,'unit':'mm','coordinate_interpretation':'original scene numerical centimetres ×10',
    'parts':{},'nominal_design':spec,'arc_design':arc,'note':'Outer envelopes and views measured from mesh; nominal interfaces checked against mesh.'}
allworld=[]
for side,name in [('右側','集風罩_右半邊_第二版_實體'),('左側','集風罩_左半邊_第二版_實體')]:
    o=bpy.data.objects[name];M=o.matrix_world;port=M.translation*10
    pts=[(M@v.co)*10 for v in o.data.vertices];allworld+=pts
    local=[p-port for p in pts]
    o.data.calc_loop_triangles();triangles=[tuple(t.vertices) for t in o.data.loop_triangles]
    tree=BVHTree.FromPolygons(pts,triangles,all_triangles=True)
    nM=M.to_3x3().inverted().transposed()
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
    normals={f:(nM@f.normal).normalized() for f in bm.faces}
    record={'object':name,'port_world_mm':list(port),'bounds_world_mm':bb(pts),'bounds_relative_to_port_mm':bb(local),
        'properties':{k:repr(o[k]) for k in o.keys()},'views':{}}
    for view,(u,v,n) in views.items():
        if side=='左側' and view in {'side','iso'}:continue
        segments=[]
        for e in bm.edges:
            if not e.link_faces:continue
            p=pts[e.verts[0].index];q=pts[e.verts[1].index];length=(q-p).length
            if length<.08:continue
            ns=[normals[f] for f in e.link_faces];ds=[nn.dot(n) for nn in ns]
            silhouette=min(ds)<-1e-7 and max(ds)>1e-7
            sharp=len(ns)==1 or (len(ns)==2 and ns[0].dot(ns[1])<math.cos(math.radians(28)))
            if not (silhouette or sharp):continue
            if max(ds)<-1e-5:continue
            pieces=min(8,max(1,math.ceil(length/25)))
            for j in range(pieces):
                a=p.lerp(q,j/pieces);b=p.lerp(q,(j+1)/pieces);mid=(a+b)/2
                if tree.ray_cast(mid+n*.04,n,2000)[0] is not None:continue
                a-=port;b-=port
                segments.append([[round(a.dot(u),5),round(a.dot(v),5)],[round(b.dot(u),5),round(b.dot(v),5)]])
        p2=[[p.dot(u),p.dot(v)] for p in local]
        record['views'][view]={'segments':segments,'bounds':[[min(p[i] for p in p2) for i in range(2)],[max(p[i] for p in p2) for i in range(2)]]}
        print('PROJECTED',side,view,len(segments),flush=True)
    gaps=[]
    sign=-1 if side=='右側' else 1
    for j in range(1,20):
        a=t0+(t1-t0)*j/20
        p=Vector((sign*(R+1)*math.sin(a),CY-(R+1)*math.cos(a),Z))
        hu=tree.ray_cast(p,Vector((0,0,1)),10);hd=tree.ray_cast(p,Vector((0,0,-1)),10)
        assert hu[0] is not None and hd[0] is not None
        gap=hu[3]+hd[3];assert abs(gap-2)<.01;gaps.append(gap)
    record['slit_gap_sampled_mm']=[min(gaps),max(gaps)]
    if side=='右側':
        for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
            p=port+tangent*(2+dz)+out*(-dy)+Vector((0,0,-1))
            assert tree.ray_cast(p,Vector((0,0,1)),5)[0] is None
        record['flange_12_hole_paths_clear']=True
        # Actual mesh cross-section through the middle of the arc; r is radial
        # distance beyond the outlet radius, z is relative to outlet centre.
        sections=[];C=Vector((0,CY,0))
        for tri in triangles:
            pp=[pts[i] for i in tri];d=[(p-C).dot(tangent) for p in pp]
            if min(d)>0 or max(d)<0 or max(abs(x) for x in d)<1e-8:continue
            hits=[]
            for i in range(3):
                a=pp[i];b=pp[(i+1)%3];da=d[i];db=d[(i+1)%3]
                if abs(da)<1e-8:hits.append(a)
                if da*db<0:hits.append(a.lerp(b,da/(da-db)))
            unique={tuple(round(c,5) for c in p):p for p in hits};hits=list(unique.values())
            if len(hits)==2:
                a,b=hits
                if max(a.z,b.z)<Z-85 or min(a.z,b.z)>Z+22:continue
                sections.append([[round((p-C).dot(out)-R,5),round(p.z-Z,5)] for p in [a,b]])
        record['nozzle_section']=sections
    bm.free();report['parts'][side]=record
report['combined_bounds_world_mm']=bb(allworld)
report['inlet_fore_aft_difference_mm']=report['parts']['左側']['port_world_mm'][1]-report['parts']['右側']['port_world_mm'][1]
assert abs(report['inlet_fore_aft_difference_mm']-80)<.01
assert before==sha(SOURCE);report['source_unchanged']=True
(HERE/'尺寸量測與視圖.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':')))
print('MEASURED',json.dumps({side:r['bounds_world_mm']['size'] for side,r in report['parts'].items()},ensure_ascii=False),flush=True)
print('SOURCE_UNCHANGED',flush=True)
