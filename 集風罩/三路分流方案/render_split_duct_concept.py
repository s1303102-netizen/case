"""PNG arrangement concept only. No .blend or fabrication files are written."""
from pathlib import Path
import bpy,bmesh,math,json,hashlib
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
SOURCE=ROOT/'第一版.blend'
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_scene=bpy.context.scene
scene=bpy.data.scenes.new('僅PNG_三路分流配置構想')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def material(name,color,metal=0,rough=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m
bodymat=material('概念_噴嘴與分流盒',(.055,.115,.16),.25,.35)
lipmat=material('概念_狹縫口板',(.32,.39,.43),.65,.28)
blackmat=material('概念_孔內與密封',(.012,.019,.024),0,.65)
colors=[(.025,.35,.68),(.90,.33,.055),(.025,.48,.34)]
branchmats=[material('概念_分支%d'%(i+1),c,.15,.34) for i,c in enumerate(colors)]
edgemat=material('概念_機殼輪廓',(.31,.37,.41),.05,.6)
ghost=bpy.data.materials.new('概念_機殼半透明');ghost.use_nodes=True
nodes=ghost.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial')
trans=nodes.new('ShaderNodeBsdfTransparent');surf=nodes.new('ShaderNodeBsdfPrincipled')
surf.inputs['Base Color'].default_value=(.64,.72,.77,1);surf.inputs['Roughness'].default_value=.65
mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.065
ghost.node_tree.links.new(trans.outputs[0],mix.inputs[1]);ghost.node_tree.links.new(surf.outputs[0],mix.inputs[2])
ghost.node_tree.links.new(mix.outputs[0],out.inputs['Surface'])

groups={'context':[],'right':[],'left':[],'old':[],'overlay':[]}
def add_group(o,group):groups[group].append(o);return o
def mesh(name,verts,faces,mat,group):
    data=bpy.data.meshes.new(name+'_mesh');data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);data.materials.append(mat)
    return add_group(o,group)
def tube(name,points,radius,mat,group):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1
    c.bevel_depth=radius;c.bevel_resolution=3;c.use_fill_caps=True
    sp=c.splines.new('POLY');sp.points.add(len(points)-1)
    for p,co in zip(sp.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,c);scene.collection.objects.link(o);c.materials.append(mat)
    return add_group(o,group)
def bez(p0,p1,p2,p3,t):return (1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
def rect(hw,hd,r,n=8):
    pts=[]
    for x,y,a in [(hw-r,hd-r,0),(-hw+r,hd-r,90),(-hw+r,-hd+r,180),(hw-r,-hd+r,270)]:
        for i in range(n):
            b=math.radians(a+90*i/n);pts.append((x+r*math.cos(b),y+r*math.sin(b)))
    return pts
def loft(name,rings,mat,group,caps=True):
    count=len(rings[0]);verts=[p for ring in rings for p in ring];faces=[]
    for j in range(len(rings)-1):
        for i in range(count):
            a=j*count+i;b=j*count+(i+1)%count;faces.append((a,b,b+count,a+count))
    if caps:faces.extend([tuple(reversed(range(count))),tuple((len(rings)-1)*count+i for i in range(count))])
    o=mesh(name,verts,faces,mat,group)
    for p in o.data.polygons:p.use_smooth=True
    return o

shell_source=bpy.data.objects['Cube']
shell=shell_source.copy();shell.data=shell_source.data.copy();shell.name='PNG_半透明機殼'
scene.collection.objects.link(shell);shell.matrix_world=Matrix.Scale(.01,4)@shell_source.matrix_world
shell.data.materials.clear();shell.data.materials.append(ghost)
for p in shell.data.polygons:p.material_index=0
add_group(shell,'context')
outline=[(-.70,-.25,0),(.70,-.25,0),(.70,.25,0),(-.70,.25,0)]
for i in range(4):tube('PNG_底部輪廓_%d'%i,[outline[i],outline[(i+1)%4]],.0011,edgemat,'context')
for x in [-.70,.70]:
    tube('PNG_背側輪廓'+str(x),[(x,-.25,0),(x,-.25,1.25),(x,.041,1.25)],.0011,edgemat,'context')
tube('PNG_背部上緣',[(-.7,-.25,1.25),(.7,-.25,1.25)],.0011,edgemat,'context')
tube('PNG_較矮平面前緣',[(-.7,.25,.70),(.7,.25,.70)],.0011,edgemat,'context')

arcdata=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']
spec=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
R=arcdata['fitted_arc_radius_mm']/1000;CY=arcdata['fitted_arc_center_Y_mm']/1000
Z=arcdata['opening_center_Z_mm']/1000
t0,t1=map(math.radians,arcdata['arc_theta_degrees']);tf=(t0+t1)/2
def arc(side,a,r=0,z=Z):return Vector((side*(R+r)*math.sin(a),CY-(R+r)*math.cos(a),z))
for side in [-1,1]:
    for dz in [-.010,.010]:
        tube('PNG_既有開口邊緣_%d_%s'%(side,dz),[arc(side,t0+(t1-t0)*j/120,0,Z+dz) for j in range(121)],.0009,edgemat,'context')

port_local=Vector((113,-1.5,159))
report={'source_blend':str(SOURCE),'source_sha256_before':source_hash,
    'source_blend_modified':False,'output_scope':'PNG arrangement concept only; no .blend/STL/CAD export',
    'CFD_executed':False,'pressure_loss_or_velocity_validated':False,
    'not_for_fabrication':'Splitter interiors, nozzle feed junctions, assembly and fasteners require detailed design.',
    'branch_inner_diameter_mm':50,'concept_wall_mm':2,'nozzles_per_blower':3,'blowers':2,
    'original_outlet_arc_radius_mm':R*1000,'original_outlet_center_z_mm':Z*1000,
    'central_non_blowing_gap_mm':50,'slot_gap_mm':2,'branches':[]}
all_pipe_meshes=[];all_nozzles=[];port_locations={}
for side,group,name in [(-1,'right','鼓風機_150FLJ330W_整體網格'),(1,'left','鼓風機_150FLJ330W_左側_整體網格')]:
    source=bpy.data.objects[name]
    blower=source.copy();blower.data=source.data.copy();scene.collection.objects.link(blower)
    blower.name='PNG_'+name;blower.matrix_world=Matrix.Scale(.01,4)@source.matrix_world
    add_group(blower,group)
    port=(source.matrix_world@port_local)*.01;port_locations[group]=list(port)
    tangent=Vector((side*math.cos(tf),math.sin(tf),0))
    back=Vector((side*math.sin(tf),-math.cos(tf),0));up=Vector((0,0,1))
    def loc(x,y,z):return port+tangent*x+back*y+up*z
    def splitter_offset(z):
        u=max(0,min(1,(z-.035)/.070))
        s=10*u**3-15*u**4+6*u**5
        return Vector((0,-(.060 if side==1 else 0)*s,0))
    # Original rectangular blower interface and its 12-hole flange are retained.
    outer=rect(.059,.060,.004);inner=rect(.041,.044,.003)
    vv=[]
    for z in [0,.003]:
        for pts in [outer,inner]:vv.extend(loc(x+.002,y,z) if pts is outer else loc(x,y,z) for x,y in pts)
    n=len(outer);ff=[]
    for i in range(n):
        j=(i+1)%n
        ff.extend([(i,j,2*n+j,2*n+i),(n+i,3*n+i,3*n+j,n+j),
                   (i,n+i,n+j,j),(2*n+i,2*n+j,3*n+j,3*n+i)])
    flange=mesh('PNG_原接口法蘭_'+group,vv,ff,lipmat,group)
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
        p=loc((dz+2)/1000,dy/1000,.0032)
        tube('PNG_法蘭螺孔_'+group+str((dy,dz)),[p,p+up*.00015],.003 if abs(dz)==50 and abs(dy)==51 else .0021,blackmat,group)
    # A short inlet neck followed by a compact gradual-width splitter envelope.
    rings=[]
    for z,w,d in [(.003,.086,.092),(.035,.086,.092),(.055,.104,.086),(.080,.144,.068),(.105,.166,.058)]:
        rings.append([loc(x,y,z)+splitter_offset(z) for x,y in rect(w/2,d/2,.009)])
    loft('PNG_短直段與分流盒_'+group,rings,bodymat,group)
    # Terminal air-knife cross section: local rounded reservoir plus gentle lip.
    Ln=spec['nozzle']['total_length_mm']/1000;Lc=spec['nozzle']['converging_length_mm']/1000
    lip=.004;blend=.006;h=spec['pre_nozzle_height_mm']/1000
    def integ(x):
        if x<=0:return 0
        if x>=Lc:return Lc-blend
        if x<blend:
            u=x/blend;return blend*(u**3-.5*u**4)
        if x<=Lc-blend:return x-blend/2
        u=(x-Lc+blend)/blend;return Lc-1.5*blend+blend*(u-u**3+.5*u**4)
    def halfgap(r):return .001 if r<=lip else h/2-math.tan(math.radians(7))*integ(Ln-r)
    def contour(wall):
        top=[Vector((Ln*j/32,halfgap(Ln*j/32)+wall)) for j in range(33)]
        p0=top[-1];p1=Vector((.060,.007+wall));p2=Vector((.054,.024+wall));p3=Vector((.068,.024+wall))
        top.extend(bez(p0,p1,p2,p3,j/16) for j in range(1,17))
        rad=.024+wall
        bulb=[Vector((.068+rad*math.cos(math.pi/2-math.pi*j/40),rad*math.sin(math.pi/2-math.pi*j/40))) for j in range(1,41)]
        bottom=[Vector((p.x,-p.y)) for p in reversed(top[:-1])]
        return top+bulb+bottom
    outer=contour(.002);inner=contour(0)
    assert len(outer)==len(inner)
    for k in range(3):
        aa=t0+(t1-t0)*k/3+.001/R
        bb=t0+(t1-t0)*(k+1)/3-.001/R
        mid=(aa+bb)/2;N=52
        def section(a,profile):return [arc(side,a,float(p.x),Z+float(p.y)) for p in profile]
        # Hollow-render envelope; feeder intersections are illustrative joints.
        rings=[]
        for j in range(N+1):
            a=aa+(bb-aa)*j/N;rings.append(section(a,outer)+list(reversed(section(a,inner))))
        noz=loft('PNG_短弧形噴嘴_%s_%d'%(group,k+1),rings,bodymat,group)
        all_nozzles.append(noz)
        for end,angles in [('起點',[aa,aa+.002/R]),('終點',[bb-.002/R,bb])]:
            loft('PNG_噴嘴端板_%s_%d_%s'%(group,k+1,end),[section(a,outer) for a in angles],lipmat,group)
        for sign in [-1,1]:
            plate=[]
            for a in [aa,bb]:
                plate.append([arc(side,a,r,Z+sign*height) for r,height in [(0,.001),(.003,.001),(.003,.010),(0,.010)]])
            # Arc-following plate uses enough sections to match existing opening.
            plate=[[arc(side,aa+(bb-aa)*j/N,r,Z+sign*height) for r,height in [(0,.001),(.003,.001),(.003,.010),(0,.010)]] for j in range(N+1)]
            loft('PNG_出風口板_%s_%d_%d'%(group,k+1,sign),plate,lipmat,group)
        start=loc((k-1)*.055,0,.105)+splitter_offset(.105)
        end=arc(side,mid,.068,Z-.022)
        p0=start;p1=start+up*.125;p2=end-up*.125;p3=end
        points=[bez(p0,p1,p2,p3,j/100) for j in range(101)]
        path=tube('PNG_內徑50導管_%s_%d'%(group,k+1),points,.027,branchmats[k],group)
        all_pipe_meshes.append(path)
        tube('PNG_下接口套_%s_%d'%(group,k+1),[start-up*.006,start+up*.014],.029,bodymat,group)
        tube('PNG_噴嘴進風套_%s_%d'%(group,k+1),[end-up*.014,end+up*.008],.029,branchmats[k],group)
        # Indicate outgoing horizontal air direction at each segment center.
        jetdir=Vector((-side*math.sin(mid),math.cos(mid),0))
        jp=arc(side,mid,-.005,Z);jq=jp+jetdir*.055
        tube('PNG_水平出風箭頭_%s_%d'%(group,k+1),[jp,jq],.0015,branchmats[k],group)
        lateral=Vector((math.cos(mid),side*math.sin(mid),0))
        tube('PNG_箭頭左_%s_%d'%(group,k+1),[jq-jetdir*.013+lateral*.006,jq],.0015,branchmats[k],group)
        tube('PNG_箭頭右_%s_%d'%(group,k+1),[jq-jetdir*.013-lateral*.006,jq],.0015,branchmats[k],group)
        length=sum((b-a).length for a,b in zip(points,points[1:]))
        low=[min(p[a] for p in points)-.027 for a in range(3)]
        high=[max(p[a] for p in points)+.027 for a in range(3)]
        assert low[0]>-.70 and high[0]<.70 and low[1]>-.25 and high[1]<.25
        report['branches'].append({'side':group,'branch':k+1,'hose_centerline_length_mm':length*1000,
            'centerline_m':[list(p) for p in points],
            'segment_outer_arc_length_mm':(bb-aa)*R*1000,
            'concept_active_slit_arc_length_mm':((bb-aa)*R-.004)*1000,
            'pipe_outer_bounds_m':[low,high],'nozzle_feed_m':list(end)})

report['port_locations_m']=port_locations
report['concept_total_active_slit_per_side_mm']=sum(b['concept_active_slit_arc_length_mm'] for b in report['branches'] if b['side']=='right')
report['joints_note']='2-mm body gaps plus 2-mm end walls are shown; local weak blowing regions remain to be designed.'
report['flow_balance_note']='Branch lengths differ. Equal flow/velocity is not established and requires resistance matching.'

# Check the visible pipe envelopes against actual saved shell triangles. Contact
# at their terminal feed reservoirs is intended; no fluid-domain checks occur.
shell_source.data.calc_loop_triangles()
sp=[shell_source.matrix_world@v.co*.01 for v in shell_source.data.vertices]
st=[tuple(t.vertices) for t in shell_source.data.loop_triangles]
shelltree=BVHTree.FromPolygons(sp,st,all_triangles=True)
deps=bpy.context.evaluated_depsgraph_get();bpy.context.view_layer.update()
checks=[]
for pipe in all_pipe_meshes:
    ev=pipe.evaluated_get(deps);data=ev.to_mesh();data.calc_loop_triangles()
    pts=[ev.matrix_world@v.co for v in data.vertices]
    tree=BVHTree.FromPolygons(pts,[tuple(t.vertices) for t in data.loop_triangles],all_triangles=True)
    overlaps=tree.overlap(shelltree)
    count=len(overlaps);checks.append({'pipe':pipe.name,'surface_intersections':count})
    if count:
        print('SHELL_CROSSING',pipe.name,count,[[list(pts[v]) for v in data.loop_triangles[pi].vertices] for pi,si in overlaps[:4]],flush=True)
    ev.to_mesh_clear();assert count==0,'Concept route crosses shell: '+pipe.name
report['pipe_shell_surface_checks']=checks
print('CONCEPT_GEOMETRY',json.dumps({k:v for k,v in report.items() if k!='branches'},ensure_ascii=False),flush=True)

floor=mesh('PNG_地面',[(-3,-3,-.005),(3,-3,-.005),(3,3,-.005),(-3,3,-.005)],[(0,1,2,3)],material('PNG_地面材質',(.64,.68,.71),0,.75),'context')
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('PNG_環境');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.72,.79,.86,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
for name,pos,power,size in [('主光',(-1.5,2.0,2.6),650,2),('補光',(1.9,.4,1.8),450,1.8),('背光',(.2,-1.8,2.1),500,1.5)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;look(o,(0,-.05,.45))
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=1700;scene.render.resolution_y=1450;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.25
cd=bpy.data.cameras.new('PNG_鏡頭');cam=bpy.data.objects.new('PNG_鏡頭',cd);scene.collection.objects.link(cam)
cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100;scene.camera=cam

font=bpy.data.fonts.load('/System/Library/Fonts/STHeiti Medium.ttc')
ink=bpy.data.materials.new('PNG_文字');ink.use_nodes=True
ns=ink.node_tree.nodes;ns.clear();em=ns.new('ShaderNodeEmission');em.inputs['Color'].default_value=(.015,.028,.04,1)
out=ns.new('ShaderNodeOutputMaterial');ink.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
def screenpoint(x,y,depth=.25):
    q=cam.rotation_euler.to_quaternion();ratio=1450/1700
    return cam.location+q@Vector(((x-.5)*cd.ortho_scale,(.5-y)*cd.ortho_scale*ratio,-depth))
def text(label,x,y,size=.018):
    c=bpy.data.curves.new('PNG_註記','FONT');c.body=label;c.font=font;c.size=size*cd.ortho_scale
    c.space_character=1.05;c.align_y='TOP_BASELINE';c.materials.append(ink)
    o=bpy.data.objects.new('PNG_註記',c);scene.collection.objects.link(o)
    o.location=screenpoint(x,y);o.rotation_euler=cam.rotation_euler;groups['overlay'].append(o)
    o.visible_shadow=False
def label_at(label,point,dx,dy):
    q=world_to_camera_view(scene,cam,Vector(point));x=q.x+dx;y=1-q.y+dy
    text(label,x,y,.0135)
    line=tube('PNG_指示線',[screenpoint(q.x,1-q.y,.26),screenpoint(x,y+.008,.26)],.00055*cd.ortho_scale,ink,'overlay')
    line.visible_shadow=False
def clear_overlay():
    for o in groups['overlay']:bpy.data.objects.remove(o,do_unlink=True)
    groups['overlay']=[]
def visible(group,value):
    for o in groups[group]:o.hide_render=not value

views=[
    ('三路分流_雙側機殼內配置.png',(1.65,2.25,1.52),(0,-.02,.60),2.10,'full'),
    ('三路分流_單側管路與噴嘴.png',(-1.1,1.35,1.02),(-.33,-.10,.39),1.25,'single'),
    ('三路分流_正面配置.png',(0,2.8,.55),(0,-.04,.55),1.65,'front')]
report['views']=[]
for filename,position,target,scale,mode in views:
    clear_overlay();visible('context',mode=='full');visible('left',mode!='single');visible('right',True)
    # Use just the measured shell outlines so tubes and nozzles remain legible.
    shell.hide_render=True;floor.hide_render=True
    cam.location=position;cd.ortho_scale=scale;look(cam,target);bpy.context.view_layer.update()
    text('三路分流導風方案｜'+{'full':'雙側配置','single':'單側管路','front':'正面排列'}[mode],.055,.045,.025)
    text('每台鼓風機 → 3支內徑50mm導管 → 3段短弧形狹縫噴嘴',.055,.090,.014)
    text('藍／橘／綠：三條獨立支路　｜　中央5cm、2mm狹縫；灰線為機殼輪廓',.055,.120,.012)
    text('配置構想示意；風速、壓損與均勻度未確認。原始 .blend 未修改。',.055,.953,.012)
    if mode=='single':
        p=Vector(port_locations['right'])+Vector((0,0,.07))
        label_at('短直段＋分流盒',p,.05,.00)
        label_at('每段約20cm；接縫需處理',arc(-1,tf,0,Z),.02,-.09)
    elif mode=='front':
        label_at('中央保留5cm',Vector((0,-.149,Z)),.025,-.06)
    scene.render.filepath=str(HERE/filename);bpy.ops.render.render(write_still=True)
    report['views'].append(filename)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash,'Source changed externally during PNG generation.'
report['source_sha256_after']=source_hash
(HERE/'三路分流_配置假設與幾何檢查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PNG_SPLIT_DUCT_CONCEPT_COMPLETE_SOURCE_UNCHANGED',flush=True)
