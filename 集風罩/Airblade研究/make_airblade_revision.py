"""Airblade-referenced concept: continuous span spreading + thin 90-degree turn.

No Blender edits. Geometry and pressure figures are candidate-design estimates,
not measured Dyson geometry, a fan performance prediction, or validated CFD.
"""
from pathlib import Path
import ast
import json
import math
import hashlib
import html
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
OLD=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())
G=json.loads((ROOT/'鼓風機/集風罩_現況幾何.json').read_text())
assert hashlib.sha256((ROOT/'第一版.blend').read_bytes()).hexdigest()==OLD['source_sha256']
L=OLD['measured']['right_arc_length_mm']
A=82*88
height=A/L
gap=2.0
alpha=math.radians(7)
blend=6.0
lip=4.0
# Symmetric nozzle wall slope: smooth onset/end, then a straight 7-degree portion.
# Both transition ramps average half the maximum wall slope over 6 mm each.
converging=(height-gap)/2/math.tan(alpha)+blend
nozzle_length=converging+lip
Rbend=28.0
Rinner=Rbend-height/2
Router=Rbend+height/2
rvertical=nozzle_length+Rbend
R=OLD['measured']['fitted_arc_radius_mm'];CY=OLD['measured']['fitted_arc_center_Y_mm']
t0,t1=[math.radians(x) for x in OLD['measured']['arc_theta_degrees']]
tf=(t0+t1)/2
Z=OLD['measured']['opening_center_Z_mm'];bendZ=Z-Rbend
outdepth=nozzle_length+Router+2
clearance=250+CY-(R+outdepth)*math.cos(t0)
assert clearance>8
mean_sin=(math.cos(t0)-math.cos(t1))/(t1-t0)
newport=[-(R+rvertical)*mean_sin/10,-10.0,OLD['blower_position']['old_port_center_cm'][2]]
oldport=OLD['blower_position']['old_port_center_cm']
c,s=math.cos(-tf),math.sin(-tf)
def moved(p):
    x,y,z=[p[i]-oldport[i] for i in range(3)]
    return [newport[0]+c*x-s*y,newport[1]+s*x+c*y,newport[2]+z]
newverts=[moved(p) for p in G['blower']['verts']]
blowerbounds={'min':[min(p[i]*10 for p in newverts) for i in range(3)],
              'max':[max(p[i]*10 for p in newverts) for i in range(3)]}
matrix=G['blower']['matrix']
neworigin=moved([matrix[i][3] for i in range(3)])
assert blowerbounds['min'][0]>-700 and blowerbounds['max'][0]<0
assert blowerbounds['min'][1]>-250 and blowerbounds['max'][1]<250


def smooth(t):return 10*t**3-15*t**4+6*t**5


def profile(h,d,lam,N=140):
    """Horizontal cross-section center curve, width lofted along the real arc."""
    out=[]
    for i in range(N+1):
        u=i/N; theta=t0+u*(t1-t0)
        p0=(newport[0]*10-82*(u-.5)*math.cos(tf),newport[1]*10+82*(u-.5)*math.sin(tf))
        pt=(-(R+rvertical)*math.sin(theta),CY-(R+rvertical)*math.cos(theta))
        out.append(tuple((1-lam)*p0[k]+lam*pt[k] for k in range(2)))
    return out


def curve_length(points):return sum(math.dist(a,b) for a,b in zip(points,points[1:]))


# The 593-mm slot follows radius R. At the upstream vertical plane R+rvertical,
# the arc is longer. Use that actual width when sizing its thickness.
uppercurve=profile(0,0,1)
upperwidth=curve_length(uppercurve)
turnheight=A/upperwidth
# A radial fan of ducts stretches an upstream arc into the smaller outlet arc.
# To avoid quietly treating those two spans as equal, size the pre-turn passage
# conservatively using the slot span (12.17 mm). Its actual upper area is larger.
# The nominal constant-area law is a concept target, not a solved 3-D streamtube.
stations=[]; envelope=[]
neckend=oldport[2]*10+50
upperstart=bendZ-55
for j in range(121):
    z=neckend+(upperstart-neckend)*j/120
    lam=smooth(j/120)
    points=profile(0,0,lam)
    width=curve_length(points)
    # Slightly increasing area, ending at actual upstream span * 12.17 mm.
    area=A+(upperwidth*height-A)*lam
    depth=area/width
    for k,p in enumerate(points):
        prev=points[max(0,k-1)];nxt=points[min(len(points)-1,k+1)]
        tx,ty=nxt[0]-prev[0],nxt[1]-prev[1];mag=math.hypot(tx,ty)
        normal=(ty/mag,-tx/mag)
        envelope.extend([(p[0]+normal[0]*(depth/2+2),p[1]+normal[1]*(depth/2+2),z),
                         (p[0]-normal[0]*(depth/2+2),p[1]-normal[1]*(depth/2+2),z)])
    if j in [0,30,60,90,120]:stations.append({'Z_mm':z,'span_mm':width,'depth_mm':depth,'area_mm2':area})
loftbounds={'min':[min(p[i] for p in envelope) for i in range(3)],
            'max':[max(p[i] for p in envelope) for i in range(3)]}
assert loftbounds['min'][0]>-700 and loftbounds['max'][0]<0
assert loftbounds['min'][1]>-250 and loftbounds['max'][1]<250


def slope_drop_integral(x):
    """Integral of a smooth 0..1..0 slope multiplier over converging length."""
    if x<=0:return 0
    if x>=converging:return converging-blend
    if x<blend:
        t=x/blend
        return blend*(t**3-.5*t**4)
    if x<=converging-blend:return x-blend/2
    t=(x-(converging-blend))/blend
    return converging-1.5*blend+blend*(t-t**3+.5*t**4)


def halfheight(r):
    # r=0 at the sharp exit; r=lip begins the converging section.
    if r<=lip:return gap/2
    x=nozzle_length-r
    return height/2-math.tan(alpha)*slope_drop_integral(x)


assert abs(halfheight(nozzle_length)-height/2)<1e-7
assert abs(halfheight(lip)-gap/2)<1e-7
oldangle=math.degrees(math.atan((70-2)/2/(35-4)))
rho=1.2
targetflow=L/1000*gap/1000*25
qin=rho*(targetflow/(A*1e-6))**2/2
Cd=.94;K=1.2
required_static=rho/2*(25/Cd)**2+(K-1)*qin
defaultV=math.sqrt(460/(rho/2*(1/Cd**2+(K-1)*(L*gap/A)**2)))
results={'concept':'Full-width thin passage before turning, gentle final nozzle; inspired by Airblade principles, not a reproduction.',
         'source_blend_sha256':OLD['source_sha256'],
         'unchanged_blender':True,'slot_span_mm':L,'slot_gap_mm':gap,
         'pre_nozzle_height_mm':height,'actual_upstream_arc_span_mm':upperwidth,
         'nominal_inlet_area_mm2':A,'upper_actual_area_mm2':upperwidth*height,
         'nozzle':{'wall_max_angle_degrees':7,'included_reference_degrees':14,
                   'converging_length_mm':converging,'straight_lip_mm':lip,
                   'total_length_mm':nozzle_length,'blend_length_each_mm':blend},
         'bend':{'mean_radius_mm':Rbend,'inner_radius_mm':Rinner,'outer_radius_mm':Router,
                 'R_over_passage_height':Rbend/height,'integrated_vane_required_in_this_concept':False,
                 'vertical_center_r_mm':rvertical,'start_Z_mm':bendZ},
         'back_wall_envelope_clearance_mm':clearance,
         'blower':{'proposed_port_center_cm':newport,'port_shift_cm':[newport[i]-oldport[i] for i in range(3)],
                   'Z_rotation_about_port_degrees':-math.degrees(tf),
                   'proposed_object_origin_cm':neworigin,'proposed_euler_degrees':[0,-90,-math.degrees(tf)],
                   'bounds_mm':blowerbounds},
         'loft_stations':stations,'loft_bounds_mm':loftbounds,
         'old_comparison':{'max_half_angle_degrees':oldangle,'old_bend_R_over_height':65/70},
         'pressure_sizing':{'assumed_Cd':Cd,'assumed_transport_K':K,'target_velocity_m_s':25,
                            'required_flow_m3_min':targetflow*60,'required_static_Pa':required_static,
                            'conditional_V_if_static_460Pa_m_s':defaultV,
                            'validated_pressure_loss':False,'uniformity_prediction':None,
                            'note':'Scalar sizing only; does not resolve lateral expansion or secondary flow.'}}
(HERE/'Airblade原理_第二版候選尺寸.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

# Reuse drawing primitives without running or overwriting the earlier drawings.
W,H=2600,1850;FACTOR=2
NAVY='#18334B';TEXT='#253D4F';MUTED='#64798A';BLUE='#137FA7'
LIGHT='#E6F5FA';TEAL='#128A78';ORANGE='#D97736';GREY='#ABB6BF';BORDER='#D6E1E8'
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
tree=ast.parse((HERE.parent/'draw_right_duct.py').read_text())
defs=ast.Module(body=[node for node in tree.body if (isinstance(node,ast.ClassDef) and node.name=='Canvas')
                     or (isinstance(node,ast.FunctionDef) and node.name=='hull')],type_ignores=[])
exec(compile(defs,'drawing_primitives','exec'))


def heading(c,title,subtitle,page):
    c.rect(0,0,W,14,NAVY,None)
    c.text(70,54,title,43,NAVY);c.text(70,119,subtitle,24,MUTED)
    c.line([(70,166),(2530,166)],BORDER,2)
    c.text(70,1788,'借用公開 Airblade 原理的候選設計；並非 Dyson 原廠尺寸圖｜未做 CFD｜Blender 檔案未修改',23,MUTED)
    c.text(2530,1788,f'{page} / 2',25,MUTED,'right')


cvs=Canvas()
heading(cvs,'Airblade 原理｜更平順的第二版導風管','以封閉流道導向、漸收噴嘴加速、精密窄縫成形；右半邊與中央 50 mm 保留段沿用。',1)
cvs.rect(70,210,760,1470,'#F8FBFD',BORDER,2)
cvs.text(105,253,'從 Airblade 公開資料學到什麼',30,NAVY)
cvs.text(105,324,'① 末端收縮要緩',29,BLUE)
cvs.text(105,373,'乾手機專利的一個實施例：',25,TEXT)
cvs.text(105,415,'兩壁各約 7°，夾角約 14°。[1]',27,TEXT)
cvs.text(105,459,'這是特定實施例，並非所有型號的剖面。',22,MUTED)
cvs.text(105,537,'② 窄縫與刀口要精準',29,BLUE)
cvs.text(105,586,'Airblade V 官方標示窄縫 0.55 mm。[2]',26,TEXT)
cvs.text(105,630,'噴嘴製造專利強調控制長縫寬度。[3]',25,TEXT)
cvs.text(105,674,'此案先保留 2 mm，搭配您的工作風壓。',25,TEAL)
cvs.text(105,752,'③ 支撐件不能形成粗大阻擋',29,BLUE)
cvs.text(105,803,'公開剖面使用流線形的縫寬支撐件。[1]',25,TEXT)
cvs.text(105,847,'若本罩需支撐，採圓鼻、細尾並留恢復段。',24,TEXT)
cvs.text(105,930,'④ 高風速需要足夠的風壓',29,BLUE)
cvs.text(105,980,'V 官方標示 690 km/h；供氣系統不同。[2]',25,TEXT)
cvs.text(105,1024,'您的 460 Pa 工作情境，速度仍約 25–26 m/s。',24,TEAL)
cvs.text(105,1068,'窄縫不能憑空補出高壓，也不保證提高風速。',23,MUTED)
cvs.line([(105,1134),(795,1134)],BORDER,2)
cvs.text(105,1170,'此版的主要改變',30,NAVY)
cvs.text(105,1224,'展寬與變薄，移到整段上升風道完成。',25,TEXT)
cvs.text(105,1269,'整條薄氣流平順轉 90°，不再先進厚腔。',25,TEXT)
cvs.text(105,1314,'末段只由約 12.2 mm 緩收至 2 mm。',26,BLUE)
cvs.text(105,1359,'關注曲面連續、局部分離與縫寬一致性。',25,TEXT)
cvs.text(105,1439,'[1] EP1909627B1：圖 7a–7c 及對應說明',21,MUTED)
cvs.text(105,1483,'[2] Dyson 台灣 Airblade V 官方資料',21,MUTED)
cvs.text(105,1527,'[3] WO2013057476A1 / EP2768369B1',21,MUTED)
cvs.text(105,1575,'原文網址與適用限制見同資料夾研究說明。',21,MUTED)

# Front elevation unfolded: the side boundaries are smooth, not a boxed riser.
cvs.text(910,220,'A　連續展寬的扇形風道（展開示意）',31,NAVY)
cvs.text(910,267,'展開寬度以實際上游弧長表示；收縮後貼合原 593 mm 出風弧。',23,MUTED)
cx=1630;floor=1470;scale=1.52
xs=[];zs=[]
for j in range(101):
    tt=j/100;lam=smooth(tt)
    span=curve_length(profile(0,0,lam))
    z=neckend+(upperstart-neckend)*tt
    xs.append(span);zs.append(z)
left=[(cx-span*scale/2,floor-z*scale) for span,z in zip(xs,zs)]
right=[(cx+span*scale/2,floor-z*scale) for span,z in reversed(list(zip(xs,zs)))]
cvs.polygon(left+right,LIGHT,BLUE,3)
neckwidth=82*scale
cvs.rect(cx-neckwidth/2,floor-neckend*scale,neckwidth,50*scale,LIGHT,BLUE,3)
top_y=floor-upperstart*scale
fullwidth=upperwidth*scale
cvs.rect(cx-fullwidth/2,top_y-55*scale,fullwidth,55*scale,LIGHT,BLUE,3)
cvs.line([(cx-fullwidth/2,top_y-55*scale),(cx+fullwidth/2,top_y-55*scale)],BLUE,5)
cvs.arrow((cx,floor-neckend*scale+36),(cx,top_y+80),TEAL,3,15)
for frac in [.15,.3,.7,.85]:
    # Direction illustrations only, not computed streamlines.
    points=[]
    for j in range(101):
        points.append((cx+(frac-.5)*xs[j]*scale,floor-zs[j]*scale))
    cvs.line(points,TEAL,1.6,6)
cvs.text(cx,top_y-55*scale-106,f'上游弧長約 {upperwidth:.0f} × 厚 {height:.1f}',29,BLUE,'center')
cvs.text(cx,top_y-55*scale-61,'整段上緣轉 90°，再緩收成水平氣流',25,TEXT,'center')
cvs.text(cx,floor-oldport[2]*10*scale+34,'對接鼓風機：82 × 88',27,BLUE,'center')
cvs.text(cx,floor-oldport[2]*10*scale+80,'出風口維持向上，機身仍在底部',24,MUTED,'center')
for index,st in enumerate(stations[1:-1]):
    y=floor-st['Z_mm']*scale
    cvs.text(2180,y-10,f'{st["span_mm"]:.0f} × {st["depth_mm"]:.1f}',26,BLUE)
    cvs.text(2180,y+28,'弧向寬 × 徑向厚',21,MUTED)
    span=st['span_mm'];cvs.line([(cx+span*scale/2,y),(2150,y)],BLUE,1.2)
cvs.text(950,1320,'展寬過程面積約 7200 → 8000 mm²；不在入口突然擴腔或急缩。',25,TEXT)
cvs.text(950,1370,'截面面積只是設計約束，三維流動分配與展寬損失仍需校核。',24,MUTED)
cvs.text(950,1445,'原弧形出風口保持：右側 X = −550 至 −25 mm，中央不出風。',25,TEXT)
cvs.text(950,1497,'氣流方向保持水平，沿圓弧的內向法線吹出。',25,TEXT)
cvs.text(950,1585,'圖中箭頭／虛線僅說明導向，不是 CFD 流線。',23,MUTED)
image1=cvs.save('Airblade原理_第二版01連續展寬')


cvs=Canvas()
heading(cvs,'第二版剖面｜薄截面轉彎、末端缓收','尺寸單位 mm；局部放大圖。借用 Airblade 收縮噴嘴原理，依目前鼓風機與外殼空間重新定尺寸。',2)
cvs.text(90,223,'B　末段放大剖面',32,NAVY)
cvs.text(90,271,'先展寬變薄，再轉彎；內外壁與相鄰流道保持切線連續。',24,MUTED)
scale2=6.4
def sec(r,z):return (1325-r*scale2,985-(z-Z)*scale2)
# Upper 55 mm straight and thin turn.
verts2=[sec(rvertical+height/2,bendZ-25),sec(rvertical+height/2,bendZ),
        sec(rvertical-height/2,bendZ),sec(rvertical-height/2,bendZ-25)]
cvs.polygon(verts2,LIGHT,BLUE,3)
outer=[(nozzle_length+Router*math.cos(a),bendZ+Router*math.sin(a)) for a in [i*math.pi/2/160 for i in range(161)]]
inner=[(nozzle_length+Rinner*math.cos(a),bendZ+Rinner*math.sin(a)) for a in [i*math.pi/2/160 for i in range(160,-1,-1)]]
cvs.polygon([sec(*p) for p in outer+inner],LIGHT,BLUE,3)
top=[sec(r,Z+halfheight(r)) for r in [nozzle_length*i/240 for i in range(241)]]
bottom=[sec(r,Z-halfheight(r)) for r in [nozzle_length*i/240 for i in range(240,-1,-1)]]
cvs.polygon(top+bottom,LIGHT,BLUE,3)
cvs.line([sec(0,Z+10),sec(0,Z+gap/2)],GREY,6)
cvs.line([sec(0,Z-10),sec(0,Z-gap/2)],GREY,6)
cvs.line([sec(0,Z+20),sec(0,Z+10)],GREY,2,7)
cvs.line([sec(0,Z-10),sec(0,Z-20)],GREY,2,7)
cvs.arrow(sec(rvertical,bendZ-21),sec(rvertical,bendZ-7),TEAL,3,14)
cvs.text(620,1337,'下接連續扇形升風道',24,MUTED)
centerturn=[sec(nozzle_length+Rbend*math.cos(i*math.pi/2/100),bendZ+Rbend*math.sin(i*math.pi/2/100)) for i in range(101)]
cvs.line(centerturn,TEAL,2,5)
cvs.arrow(sec(nozzle_length-12,Z),sec(-28,Z),TEAL,3.6,17)
cvs.text(1370,921,'水平氣流',26,TEAL)
cvs.text(1370,1021,'縫高 2.0',26,BLUE)
cvs.text(790,643,f'末端總長 {nozzle_length:.1f}',27,BLUE)
cvs.dim(sec(nozzle_length,Z+39),sec(0,Z+39),f'緩收 {converging:.1f} + 平直 {lip:.0f}',MUTED,-5,24)
cvs.line([sec(nozzle_length,Z+height/2),sec(nozzle_length,Z+39)],GREY,1)
cvs.line([sec(0,Z+10),sec(0,Z+39)],GREY,1)
cvs.text(90,722,f'轉彎前厚度約 {height:.1f}',29,BLUE)
cvs.text(90,770,f'R中 {Rbend:.0f}；R內 {Rinner:.1f}；R外 {Router:.1f}',26,TEXT)
cvs.text(90,818,f'R中 / 厚度 ≈ {Rbend/height:.2f}',27,TEAL)
cvs.text(90,865,'這裡的半徑雖小，對薄截面仍屬較緩轉彎。',23,MUTED)
cvs.line([(510,839),sec(nozzle_length+Rbend*.7071,bendZ+Rbend*.7071)],BLUE,1.2)
cvs.text(940,1075,'兩壁最大各 7°，首尾有平滑過渡',25,BLUE)
cvs.line([(1100,1060),sec(nozzle_length*.45,Z-halfheight(nozzle_length*.45))],BLUE,1.2)
cvs.text(90,1404,'整體改變',31,NAVY)
cvs.text(90,1463,f'上一版局部收縮半角可達約 {oldangle:.0f}°；這版末段限制到約 7°。',27,TEXT)
cvs.text(90,1516,'出口內側留清楚分離邊，避免把噴流帶向罩壁；縫寬用可更換墊片控制。',25,TEXT)
cvs.text(90,1569,'薄截面曲面接續；目前不設上一版彎頭中央導流片，是否增設依 CFD 決定。',24,MUTED)
cvs.text(90,1638,'噴嘴附近如需支撐，採流線形圓鼻細尾，並避免支撐件直接切斷出風縫。',24,MUTED)

cvs.rect(1610,215,910,1455,'#F8FBFD',BORDER,2)
cvs.text(1650,258,'第二版候選尺寸',31,NAVY)
rows=[('原淨接口','82 × 88'),('上游厚度',f'約 {height:.1f}；沿弧展寬至約 {upperwidth:.0f}'),
      ('90° 轉彎',f'R中 {Rbend:.0f}；R / 厚度約 {Rbend/height:.1f}'),
      ('末端噴嘴',f'約 {nozzle_length:.1f} 長，最大各 7°'),
      ('右側出風縫',f'{L:.0f} × 2；中央保留 50'),
      ('最深處',f'約 {outdepth:.0f}（含初擬 2 mm 壁厚）')]
for i,(a,b) in enumerate(rows):
    y=326+i*91;cvs.text(1650,y,a,24,MUTED);cvs.text(1650,y+36,b,28,TEXT)
cvs.text(1650,912,f'距外殼後壁包絡约 {clearance:.0f} mm。',26,TEAL)
cvs.text(1650,954,'需再扣除外殼板厚及安裝公差。',24,MUTED)
cvs.line([(1650,1009),(2480,1009)],BORDER,2)
cvs.text(1650,1043,'鼓風機仍建議往開口中心移',29,NAVY)
cvs.text(1650,1095,f'接口中心（cm）：({newport[0]:.2f}, −10.00, 20.80)',25,TEXT)
cvs.text(1650,1143,f'沿 +X 移約 {(newport[0]-oldport[0]):.1f} cm；+Y 約 2.6 cm。',25,TEXT)
cvs.text(1650,1191,f'繞接口中心平面旋轉约 −{math.degrees(tf):.1f}°。',25,TEXT)
cvs.text(1650,1247,'機身落地，向上吹；最終定位隨三維流道校核。',23,MUTED)
cvs.line([(1650,1303),(2480,1303)],BORDER,2)
cvs.text(1650,1341,'風速仍由工作風壓限制',29,NAVY)
cvs.text(1650,1397,'25 m/s 需要約 1.78 m³/min、430 Pa。',27,TEAL)
cvs.text(1650,1445,'係數是假設，不能宣稱風速已勝過上一版。',24,MUTED)
cvs.text(1650,1504,'本次完成結構研究與尺寸草案。',25,TEXT)
cvs.text(1650,1552,'展寬損失、流量分配和均勻性仍待三維驗證。',23,MUTED)
image2=cvs.save('Airblade原理_第二版02平順噴嘴剖面')
image1.save(HERE/'Airblade原理_第二版圖面.pdf',save_all=True,append_images=[image2],resolution=314.476,quality=94)
assert hashlib.sha256((ROOT/'第一版.blend').read_bytes()).hexdigest()==OLD['source_sha256']
print(json.dumps(results,ensure_ascii=False,indent=2))
