"""Render revised smooth splitter and original-profile short hoods. PNG only."""
from pathlib import Path
import math
HERE=Path(__file__).resolve().parent
base=(HERE.parent/'render_split_duct_concept.py').read_text()
prefix=base.split('for side,group,name in ')[0]
prefix=prefix.replace('ROOT=HERE.parent.parent','ROOT=HERE.parents[2]')
prefix=prefix.replace("HERE.parent/'右半邊集風罩_計算.json'","ROOT/'集風罩/右半邊集風罩_計算.json'")
prefix=prefix.replace("HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json'","ROOT/'集風罩/Airblade研究/Airblade原理_第二版候選尺寸.json'")
exec(compile(prefix,'preview_setup','exec'))

def hollow_loft(name,outer,inner,mat,group):
    count=len(outer[0]);nr=len(outer);vv=[];ff=[]
    for ro,ri in zip(outer,inner):vv.extend(ro);vv.extend(ri)
    for j in range(nr-1):
        for i in range(count):
            k=(i+1)%count;a=j*2*count+i;b=j*2*count+k
            ff.append((a,b,b+2*count,a+2*count))
            a+=count;b+=count;ff.append((b,a,a+2*count,b+2*count))
    for j in [0,nr-1]:
        for i in range(count):
            k=(i+1)%count;a=j*2*count+i;b=j*2*count+k
            ff.append((a,a+count,b+count,b))
    o=mesh(name,vv,ff,mat,group)
    for p in o.data.polygons:p.use_smooth=True
    return o
def S(t):return 10*t**3-15*t**4+6*t**5
def superpts(w,d,n,N=96):
    pts=[]
    for j in range(N):
        a=2*math.pi*j/N;co,si=math.cos(a),math.sin(a)
        pts.append((w/2*math.copysign(abs(co)**(2/n),co),d/2*math.copysign(abs(si)**(2/n),si)))
    return pts
Ln=spec['nozzle']['total_length_mm']/1000
Lc=spec['nozzle']['converging_length_mm']/1000
rb=spec['bend']['mean_radius_mm']/1000
h=spec['pre_nozzle_height_mm']/1000
rv=Ln+rb;bendZ=Z-rb;upperZ=bendZ-.012
entryZ=upperZ-.150
def integ(x):
    if x<=0:return 0
    if x>=Lc:return Lc-.006
    if x<.006:
        u=x/.006;return .006*(u**3-.5*u**4)
    if x<=Lc-.006:return x-.003
    u=(x-Lc+.006)/.006;return Lc-.009+.006*(u-u**3+.5*u**4)
def halfgap(r):return .001 if r<=.004 else h/2-math.tan(math.radians(7))*integ(Ln-r)
report.update({'revision':'Smooth rectangular-to-round splitter and original thin-turn/nozzle profile',
    'terminal_loft_length_mm':150,'terminal_straight_before_bend_mm':12,
    'terminal_inlet_center_z_mm':entryZ*1000,'bend_radius_mm':rb*1000,
    'nozzle_length_mm':Ln*1000,'max_nozzle_wall_angle_deg':7,
    'placement_note':'Existing blowers stay in place; revised routes are visual candidates, not optimized flow paths.'})
hood_objects=[];splitter_objects=[]
for side,group,name in [(-1,'right','鼓風機_150FLJ330W_整體網格'),(1,'left','鼓風機_150FLJ330W_左側_整體網格')]:
    src=bpy.data.objects[name];o=src.copy();o.data=src.data.copy();scene.collection.objects.link(o)
    o.name='PNG_'+name;o.matrix_world=Matrix.Scale(.01,4)@src.matrix_world;add_group(o,group)
    port=(src.matrix_world@port_local)*.01;port_locations[group]=list(port)
    tangent=Vector((side*math.cos(tf),math.sin(tf),0))
    back=Vector((side*math.sin(tf),-math.cos(tf),0));up=Vector((0,0,1))
    def loc(x,y,z):return port+tangent*x+back*y+up*z
    # Reuse the existing flange envelope; its aperture remains rectangular.
    outer=rect(.059,.060,.004);inner=rect(.041,.044,.003);vv=[];ff=[];n=len(outer)
    for z in [0,.003]:
        vv.extend(loc(x+.002,y,z) for x,y in outer);vv.extend(loc(x,y,z) for x,y in inner)
    for i in range(n):
        j=(i+1)%n
        ff.extend([(i,j,2*n+j,2*n+i),(n+i,3*n+i,3*n+j,n+j),(i,n+i,n+j,j),(2*n+i,2*n+j,3*n+j,3*n+i)])
    mesh('PNG_原矩形接口法蘭_'+group,vv,ff,lipmat,group)
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
        p=loc((dz+2)/1000,dy/1000,.0032)
        tube('PNG_接口螺孔_'+group+str((dy,dz)),[p,p+up*.0001],.0025,blackmat,group)
    hollow_loft('PNG_矩形直段_'+group,
        [[loc(x,y,z) for x,y in rect(.043,.046,.003)] for z in [.003,.040]],
        [[loc(x,y,z) for x,y in rect(.041,.044,.002)] for z in [.003,.040]],bodymat,group)
    for k in range(3):
        # Preserve central 50-mm exclusion; reserve small gaps only between modules.
        aa=t0+(t1-t0)*k/3+(.003/R if k>0 else 0)
        bb=t0+(t1-t0)*(k+1)/3-(.003/R if k<2 else 0)
        mid=(aa+bb)/2
        tm=Vector((side*math.cos(mid),math.sin(mid),0))
        bm=Vector((side*math.sin(mid),-math.cos(mid),0))
        inlet=arc(side,mid,rv,entryZ)
        branch_end=loc((k-1)*.070,0,.150)+Vector((0,-.090 if side==1 else 0,0))
        heading=(inlet-branch_end+up*.035).normalized()
        branch_start=loc((k-1)*.028,0,.040)
        p0=branch_start;p1=p0+up*.045;p3=branch_end;p2=p3-heading*.048
        ro=[];ri=[]
        area0=.026*.088*math.gamma(1+1/8)**2/math.gamma(1+2/8)
        for j in range(49):
            t=j/48;s=S(t)
            center=bez(p0,p1,p2,p3,t)
            deriv=3*(1-t)**2*(p1-p0)+6*(1-t)*t*(p2-p1)+3*t*t*(p3-p2)
            quat=up.rotation_difference(deriv.normalized());tx=quat@tangent;by=quat@back
            n=8-6*s;aspect=(.026/.088)**(1-s)
            area=area0+(math.pi*.025**2-area0)*s
            coeff=math.gamma(1+1/n)**2/math.gamma(1+2/n)
            w=math.sqrt(area*aspect/coeff);d=math.sqrt(area/aspect/coeff)
            ri.append([center+tx*x+by*y for x,y in superpts(w,d,n)])
            ro.append([center+tx*x+by*y for x,y in superpts(w+.004,d+.004,n)])
        splitter=hollow_loft('PNG_漸變分流支路_%s_%d'%(group,k+1),ro,ri,branchmats[k],group)
        splitter_objects.append(splitter)
        # The pipe meets the splitter tangent; the upper end meets a round collar.
        q0=branch_end;q1=q0+heading*.070;q3=inlet;q2=q3-up*.070
        points=[bez(q0,q1,q2,q3,j/100) for j in range(101)]
        pipe=tube('PNG_內徑50導管_%s_%d'%(group,k+1),points,.027,branchmats[k],group)
        all_pipe_meshes.append(pipe)
        tube('PNG_圓管端套_%s_%d'%(group,k+1),[inlet-up*.010,inlet+up*.008],.029,lipmat,group)
        # Circle -> progressively spread/thinned arc section -> original 90° turn.
        inner_rings=[];outer_rings=[]
        perimeter=superpts(2,2,8)
        def flat_profile(u,v,r,depth,z,wall):
            extra=.002/(R+r) if wall else 0
            a=(aa-extra)+(bb-aa+2*extra)*(u+1)/2
            return arc(side,a,r,z)+Vector((side*math.sin(a),-math.cos(a),0))*(v*(depth/2+(.002 if wall else 0)))
        for j in range(65):
            t=j/64;s=S(t);z=entryZ+(upperZ-entryZ)*t
            pair=[]
            for wall in [False,True]:
                ring=[]
                for m,(u,v) in enumerate(perimeter):
                    phi=2*math.pi*m/len(perimeter)
                    p0=inlet+tm*((.027 if wall else .025)*math.cos(phi))+bm*((.027 if wall else .025)*math.sin(phi))
                    pt=flat_profile(u,v,rv,h,z,wall)
                    p=p0*(1-s)+pt*s;p.z=z;ring.append(p)
                pair.append(ring)
            inner_rings.append(pair[0]);outer_rings.append(pair[1])
        for j in range(1,7):
            z=upperZ+.012*j/6
            inner_rings.append([flat_profile(u,v,rv,h,z,False) for u,v in perimeter])
            outer_rings.append([flat_profile(u,v,rv,h,z,True) for u,v in perimeter])
        for j in range(1,41):
            angle=math.pi/2*j/40
            pair=[]
            for wall in [False,True]:
                ring=[]
                for u,v in perimeter:
                    a=aa+(bb-aa)*(u+1)/2
                    if wall:a+=(.002/(R+rv))*u
                    radius=rb+v*(h/2+(.002 if wall else 0))
                    r=Ln+radius*math.cos(angle);z=bendZ+radius*math.sin(angle)
                    ring.append(arc(side,a,r,z))
                pair.append(ring)
            inner_rings.append(pair[0]);outer_rings.append(pair[1])
        for part,length,count in [('收縮',Lc,50),('短直唇',.004,8)]:
            for j in range(1,count+1):
                r=Ln-Lc*j/count if part=='收縮' else .004*(1-j/count)
                pair=[]
                for wall in [False,True]:
                    ring=[]
                    for u,v in perimeter:
                        a=aa+(bb-aa)*(u+1)/2
                        if wall:a+=(.002/(R+r))*u
                        ring.append(arc(side,a,r,Z+v*(halfgap(r)+(.002 if wall else 0))))
                    pair.append(ring)
                inner_rings.append(pair[0]);outer_rings.append(pair[1])
        hood=hollow_loft('PNG_原版剖面小型風刀罩_%s_%d'%(group,k+1),outer_rings,inner_rings,bodymat,group)
        all_nozzles.append(hood);hood_objects.append(hood)
        for sign in [-1,1]:
            rings=[[arc(side,aa+(bb-aa)*j/60,r,Z+sign*height) for r,height in [(0,.001),(.003,.001),(.003,.010),(0,.010)]] for j in range(61)]
            loft('PNG_弧形風刀面板_%s_%d_%d'%(group,k+1,sign),rings,lipmat,group)
        jetdir=Vector((-side*math.sin(mid),math.cos(mid),0));lateral=tm
        jp=arc(side,mid,-.005,Z);jq=jp+jetdir*.045
        tube('PNG_水平出風方向_%s_%d'%(group,k+1),[jp,jq],.0013,branchmats[k],group)
        for sign in [-1,1]:tube('PNG_箭頭_%s_%d_%d'%(group,k+1,sign),[jq-jetdir*.012+lateral*(sign*.005),jq],.0013,branchmats[k],group)
        low=[min(p[a] for p in points)-.027 for a in range(3)];high=[max(p[a] for p in points)+.027 for a in range(3)]
        assert low[0]>-.7 and high[0]<.7 and low[1]>-.25 and high[1]<.25
        report['branches'].append({'side':group,'branch':k+1,'hose_centerline_length_mm':sum((b-a).length for a,b in zip(points,points[1:]))*1000,
            'segment_outer_arc_length_mm':(bb-aa)*R*1000,'concept_active_slit_arc_length_mm':(bb-aa)*R*1000,
            'pipe_outer_bounds_m':[low,high],'nozzle_feed_m':list(inlet)})

# Reuse the rendering setup and source-preservation checks, with new captions.
tail=base[base.index("report['port_locations_m']="):]
tail=tail.replace("report['joints_note']='2-mm body gaps plus 2-mm end walls are shown; local weak blowing regions remain to be designed.'",
    "report['joints_note']='6-mm gaps between neighboring module flow paths; seam uniformity remains unverified.'")
tail=tail.replace("('三路分流_單側管路與噴嘴.png',(-1.1,1.35,1.02),(-.33,-.10,.39),1.25,'single')",
    "('平順修正版_單側立體配置.png',(-1.1,1.35,1.02),(-.33,-.10,.39),1.25,'single')")
tail=tail.replace('三路分流_雙側機殼內配置.png','平順修正版_雙側機殼內配置.png')
tail=tail.replace("('三路分流_正面配置.png',(0,2.8,.55),(0,-.04,.55),1.65,'front')",
    "('平順修正版_末端集風罩近照.png',(-.95,.92,.97),(-.33,-.12,.615),.77,'detail')")
tail=tail.replace("mode!='single'","mode not in ['single','detail']")
tail=tail.replace("'front':'正面排列'","'front':'正面排列','detail':'小型風刀罩近照'")
tail=tail.replace('三路分流導風方案｜','平順流道修正版｜')
tail=tail.replace('每台鼓風機 → 3支內徑50mm導管 → 3段短弧形狹縫噴嘴','矩形漸變分流 → 3支圓管 → 展寬變薄 → 90°彎道 → 收縮狹縫')
tail=tail.replace('短直段＋分流盒','矩形直段＋漸變圓管')
tail=tail.replace('每段約20cm；接縫需處理','原版剖面的小型集風罩')
tail=tail.replace('三路分流_配置假設與幾何檢查.json','平順修正版_配置假設與幾何檢查.json')
exec(compile(tail,'preview_render','exec'))
