from pathlib import Path
import bpy,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'流道幾何檢查.json').read_text())
bpy.ops.wm.open_mainfile(filepath=r['part_file']);o=next(iter(bpy.context.scene.objects));o.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)
hole_checks=[]
for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
    hit=tree.ray_cast(Vector((2+dz,dy,-1)),Vector((0,0,1)),5)
    assert hit[0] is None,(dy,dz);hole_checks.append([2+dz,dy])
walls=[]
for z in [19.9,20.4,30,37.9,38,38.1,39.9,40,40.1,41,44,45.9,46.1]:
    for x in [-28,28]:
        for direction in [Vector((-1 if x<0 else 1,0,0)),Vector((0,1,0)),Vector((0,-1,0))]:
            first=tree.ray_cast(Vector((x,.123,z)),direction,80)
            assert first[0] is not None,(x,z,list(direction),'no inner wall')
            second=tree.ray_cast(first[0]+direction*.02,direction,15)
            assert second[0] is not None,(x,z,list(direction),'no outer wall')
            thick=second[3]+.02
            assert thick>1.5,(x,z,list(direction),thick)
            walls.append({'x_mm':x,'z_mm':z,'direction':list(direction),'thickness_along_ray_mm':thick})
r['flange_12_bolt_paths_clear']=True;r['flange_bolt_centers_mm']=hole_checks
r['root_external_wall_continuity_samples']=walls
r['root_wall_minimum_sampled_thickness_mm']=min(q['thickness_along_ray_mm'] for q in walls)
(HERE/'流道幾何檢查.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print('FLANGE_AND_ROOT_WALL_CONTINUITY_VERIFIED',len(walls),r['root_wall_minimum_sampled_thickness_mm'],flush=True)
