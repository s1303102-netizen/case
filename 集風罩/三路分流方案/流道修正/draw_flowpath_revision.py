"""Code-native PNG/SVG explanatory flow-path diagrams; no Blender operations."""
from pathlib import Path
import ast,math,json,html,hashlib
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'第一版.blend'
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
W,H,FACTOR=2600,1850,2
NAVY='#18334B';TEXT='#253D4F';MUTED='#64798A';BLUE='#137FA7';LIGHT='#E6F5FA'
TEAL='#128A78';ORANGE='#D97736';GREY='#ABB6BF';BORDER='#D6E1E8'
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
tree=ast.parse((ROOT/'集風罩/draw_right_duct.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Canvas'],type_ignores=[]),'drawing_helpers','exec'))
spec=json.loads((ROOT/'集風罩/Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
def smooth(t):return 10*t**3-15*t**4+6*t**5
def header(c,title,sub,page):
    c.rect(0,0,W,14,NAVY,None);c.text(70,50,title,43,NAVY)
    c.text(70,116,sub,24,MUTED);c.line([(70,165),(2530,165)],BORDER,2)
    c.line([(70,1745),(2530,1745)],BORDER,2)
    c.text(70,1780,'流道構想修正｜箭頭僅表示預定方向，非 CFD 流線｜過渡長度與壓損未定案｜第一版.blend 未修改',23,MUTED)
    c.text(2525,1780,str(page)+'/2',24,MUTED,'right')

# Page 1: project actual continuously changing cross sections into an axonometric
# illustration. The long-rectangular channel progressively becomes a circle.
c=Canvas();header(c,'修正①｜矩形出口到圓管，使用連續漸變流道',
    '矩形轉圓形可以設計；需要讓分流隔板、截面形狀與支路中心線一起平順過渡。',1)
c.text(95,215,'A　漸變式三路分流接頭',32,NAVY)
c.text(95,265,'示意切開三路接頭的形狀演變；長度尚待配合機殼空間設計。',24,MUTED)
def project(p):
    x,y,z=p
    return (690+3.7*(x+.5*y),1190+3.7*(.3*x-.25*y-.95*z))
def superellipse(w,d,n,N=64):
    pts=[]
    for k in range(N):
        a=2*math.pi*k/N;co,si=math.cos(a),math.sin(a)
        pts.append((w/2*math.copysign(abs(co)**(2/n),co),d/2*math.copysign(abs(si)**(2/n),si)))
    return pts
def shade(rgb,f):
    return '#'+''.join(f'{max(0,min(255,round(v*f))):02x}' for v in rgb)
palette=[(31,134,178),(220,139,77),(40,154,127)]
faces=[];rings_by_branch=[]
root_area=26*88*math.gamma(1+1/8)**2/math.gamma(1+2/8)
for branch in range(3):
    rings=[]
    for j in range(37):
        t=j/36;s=smooth(t);n=8-6*s
        area=root_area+(math.pi*25**2-root_area)*s
        aspect=(26/88)**(1-s)
        coeff=math.gamma(1+1/n)**2/math.gamma(1+2/n)
        w=math.sqrt(area*aspect/coeff);d=math.sqrt(area/aspect/coeff)
        center=(branch-1)*(28+34*s);z=40+150*t
        ring=[(center+x,y,z) for x,y in superellipse(w+4,d+4,n)]
        rings.append(ring)
    rings_by_branch.append(rings)
    for j in range(36):
        for i in range(64):
            pts=[rings[j][i],rings[j][(i+1)%64],rings[j+1][(i+1)%64],rings[j+1][i]]
            dep=sum(p[1]-.25*p[0]+.08*p[2] for p in pts)/4
            f=.91+.13*math.sin(2*math.pi*i/64)
            faces.append((dep,[project(p) for p in pts],shade(palette[branch],f)))
for dep,pts,color in sorted(faces,key=lambda f:f[0],reverse=True):c.polygon(pts,color,None)
# Draw the common rectangular straight inlet neck below the developing branches.
neck0=[(x,y,0) for x,y in [(-43,-46),(43,-46),(43,46),(-43,46)]]
neck1=[(x,y,40) for x,y in [(-43,-46),(43,-46),(43,46),(-43,46)]]
for i in [1,2,3,0]:
    pts=[neck0[i],neck0[(i+1)%4],neck1[(i+1)%4],neck1[i]]
    c.polygon([project(p) for p in pts],'#D9E4EC',MUTED,1.5)
for branch,rings in enumerate(rings_by_branch):
    # Intermediate loops make the progressive change legible.
    for j in [9,18,27]:c.line([project(p) for p in rings[j]+rings[j][:1]],'#D4E6EC',1.4)
    top=rings[-1]
    c.polygon([project(p) for p in top],'#E8F0F4',NAVY,1.8)
    center=(branch-1)*62
    c.polygon([project((center+x,y,190)) for x,y in superellipse(50,50,2)],'#FFFFFF',shade(palette[branch],.8),2.2)
    px,py=project((center,0,190))
    c.text(px,py-78,'Ø50',26,NAVY,'center')
px,py=project((0,-46,0))
c.text(690,1370,'原接口：82 × 88 mm',29,NAVY,'center')
c.line([(690,1350),(px,py+12)],MUTED,1.6)
c.text(95,1490,'先保留矩形直段，再以薄隔板平順分成三路；',26,TEXT)
c.text(95,1536,'每路逐漸變成圓管，內壁不出現突縮台階。',26,TEXT)
c.text(95,1604,'不是只把外殼倒圓角：真正需要連續的是內部通道。',25,BLUE)

c.rect(1370,210,1150,1480,'#F8FBFD',BORDER,2)
c.text(1410,250,'B　單一路徑的截面演變',31,NAVY)
xs=[1510,1790,2070,2350]
labels=['圓角長矩形','逐漸變圓角','橢圓','圓形']
for i,(w,d,n) in enumerate([(26,88,8),(32,75,5),(42,58,2.8),(50,50,2)]):
    cx=xs[i];cy=530
    c.polygon([(cx+x*1.95,cy+y*1.95) for x,y in superellipse(w,d,n)],LIGHT,BLUE,3)
    c.text(cx,670,labels[i],23,TEXT,'center')
    if i<3:c.arrow((cx+85,530),(xs[i+1]-80,530),TEAL,3,12)
c.text(1410,755,'上圖為概念過程，不是各截面已定案的尺寸。',24,MUTED)
c.line([(1410,820),(2480,820)],BORDER,2)
items=[('形狀與截面積一起控制','避免先大幅放大、再突然縮成圓孔。'),
       ('分流鼻端與支路轉向也要平順','不能讓氣流先撞平板，再急轉進三支管。'),
       ('三支 Ø50 不是全程等截面','原接口 7216 mm²；三支圓管合計約 5890 mm²。'),
       ('分流比例仍需設計','出口速度分布及各路阻力會影響流量分配。')]
yy=865
for title,desc in items:
    c.text(1410,yy,title,29,NAVY);c.text(1410,yy+51,desc,23,TEXT);yy+=175
c.save('修正01_矩形到三路圓管的漸變接頭')

# Page 2: reproduce the original thin 90-degree bend and nozzle profile.
c=Canvas();header(c,'修正②｜末端改回原版「展寬 → 薄層彎道 → 收斂風刀」',
    '每支圓管接一個小型集風罩；保留原來的轉向與噴嘴剖面，縮短每段的弧向寬度。',2)
c.text(95,215,'A　側剖面：沿用原版流道',32,NAVY)
c.text(95,267,'剖面取自原版候選尺寸；側剖只顯示厚度方向，不代表噴嘴寬度。',23,MUTED)
h=spec['pre_nozzle_height_mm'];rb=spec['bend']['mean_radius_mm'];wall=2
Ln=spec['nozzle']['total_length_mm'];Lc=spec['nozzle']['converging_length_mm'];blend=6;lip=4
def integ(x):
    if x<=0:return 0
    if x>=Lc:return Lc-blend
    if x<blend:
        t=x/blend;return blend*(t**3-.5*t**4)
    if x<=Lc-blend:return x-blend/2
    t=(x-Lc+blend)/blend;return Lc-1.5*blend+blend*(t-t**3+.5*t**4)
def hh(r):return 1 if r<=lip else h/2-math.tan(math.radians(7))*integ(Ln-r)
def contour(add):
    upper=[(-h/2-add,-35),(-h/2-add,0)]
    upper += [(rb-(rb+h/2+add)*math.cos(a),(rb+h/2+add)*math.sin(a)) for a in [math.pi/2*j/64 for j in range(1,65)]]
    upper += [(rb+s,rb+hh(Ln-s)+add) for s in [Ln*j/100 for j in range(1,101)]]
    lower=[(rb+s,rb-hh(Ln-s)-add) for s in [Ln*(1-j/100) for j in range(101)]]
    lower += [(rb-(rb-h/2-add)*math.cos(a),(rb-h/2-add)*math.sin(a)) for a in [math.pi/2*(1-j/64) for j in range(1,65)]]
    lower += [(h/2+add,-35)]
    return upper+lower
def section(p):return (315+9*p[0],1080-9*p[1])
c.polygon([section(p) for p in contour(2)],'#BDCEDB',NAVY,2.5)
c.polygon([section(p) for p in contour(0)],LIGHT,BLUE,2.2)
# Show the open intake and open jet gap.
p=section((-h/2,-35));q=section((h/2,-35));c.line([p,q],LIGHT,4)
ex=section((rb+Ln,rb))[0];ey=section((rb+Ln,rb))[1]
c.line([(ex,ey-9),(ex,ey+9)],LIGHT,3)
c.arrow(section((0,-30)),section((0,-7)),TEAL,4,12)
curve=[section((rb-rb*math.cos(a),rb*math.sin(a))) for a in [math.pi/2*j/50 for j in range(51)]]
c.line(curve,TEAL,3.5)
c.arrow(curve[28],curve[34],TEAL,3.5,10)
c.arrow(section((rb+9,rb)),(ex+80,ey),TEAL,3.5,10)
c.text(95,390,'薄流道先完成轉向，',28,BLUE)
c.text(95,437,'再由收縮噴嘴形成薄片氣流。',28,BLUE)
c.text(90,1195,'向上來風',26,TEAL)
c.line([(230,1210),section((0,-18))],TEAL,1.5)
c.text(95,1450,'上游先完成圓轉扁與弧向展寬',27,NAVY)
c.text(95,1502,'此處接的是薄矩形流道，不是 Ø50 圓管直接轉彎壓扁。',23,MUTED)
c.dim((section((rb,rb))[0],610),(ex,610),'原噴嘴長約 51.4 mm',MUTED,0,23)
c.line([(ex+28,ey-9),(ex+110,ey-9)],MUTED,1)
c.line([(ex+28,ey+9),(ex+110,ey+9)],MUTED,1)
c.text(ex+125,ey-15,'2 mm 出風縫',25,BLUE)
c.text(95,1577,'原版參考：彎道中心 R28 mm；彎前厚約12.17 mm；收縮壁最大角約7°。',24,TEXT)
c.text(95,1625,'這些是沿用的候選幾何，並不代表分流後的風速與壓損已確認。',23,MUTED)

c.rect(1370,210,1150,1480,'#F8FBFD',BORDER,2)
c.text(1410,250,'B　每段小型集風罩的展寬',31,NAVY)
c.text(1410,310,'圓管 → 漸變展寬與變薄 → 接入左圖薄層彎道',24,TEXT)
cx=1945;ybase=1355;ytop=700;L=ybase-ytop
left=[];right=[]
for j in range(121):
    t=j/120;s=smooth(t);width=(50+(205-50)*s)*3.4
    left.append((cx-width/2,ybase-L*t));right.append((cx+width/2,ybase-L*t))
c.polygon(left+list(reversed(right)),LIGHT,BLUE,3)
c.rect(cx-85,ybase,170,125,'#D8E7EF',BLUE,3)
c.arrow((cx,ybase+82),(cx,ybase-60),TEAL,4,14)
c.arrow((cx,ybase-210),(cx,ybase-360),TEAL,4,14)
c.text(cx,565,'上緣接薄流道與 90° 彎道',26,BLUE,'center')
c.dim((left[-1][0],640),(right[-1][0],640),'每段出風弧長約20cm',MUTED,0,24)
c.text(cx,ybase+152,'下方由 Ø50 mm 圓管進風',25,NAVY,'center')
c.text(1410,1555,'過渡段需要足夠長度，才有空間平順展寬。',25,TEXT)
c.text(1410,1602,'這會比上一張圓背噴嘴略大，仍可縮短原大型罩體。',23,MUTED)
c.text(1410,1640,'圖為正視展寬示意，過渡長度尚未決定。',23,MUTED)
c.save('修正02_原版薄層彎道與風刀噴嘴剖面')

after=hashlib.sha256(SOURCE.read_bytes()).hexdigest();assert before==after
(HERE/'修正圖說明.md').write_text('''# 三路分流方案：流道修正說明

本次僅產生解釋流道的 PNG / SVG，未啟動 Blender，未修改第一版.blend。原本三路分流的配置 PNG 保留供比較；本次剖面圖修正其兩處尚未處理的流道。

1. 鼓風機的矩形接口先接直段，再由薄分流隔板把氣流導入三支連續漸變的支路。支路截面由長矩形逐漸變成橢圓、圓形。圖示不代表已定案的過渡長度、分流比或製造壁厚，亦沒有完成三支路的等阻力設計。
2. 每支圓管接回原版形態的小型集風罩：圓轉扁、弧向展寬、薄層90度彎道、平順收縮噴嘴、2mm狹縫。這次不沿用上一張配置圖的圓背儲氣管外觀。

沿用原版候選剖面：彎道中心半徑28mm、彎前流道厚約12.17mm、收縮段最大壁角7度、噴嘴總長約51.43mm。這些不是已驗證的最佳值。每段約20cm的展寬過渡仍需要足夠長度；新小罩的尺寸、外殼內走管與干涉需要在定案時重新安排，不能直接把本次剖面疊上先前配置圖就視為已完成。

矩形轉圓形可以用於風管，重點是內壁、截面積與流向的漸變，而不是只有外表倒圓角。參考：[AMCA 系統效應說明](https://www.amca.org/educate/articles-and-technical-papers/amca-inmotion-articles/mitigating-system-effect-to-optimize-fan-performance-efficiency.html)。圓背或水滴形風刀本身也有成熟應用，例如 [Sonic XE](https://www.sonicairsystems.com/products/sonic-xe-system)；此處改回原剖面，是配合本專案的90度導風與原設計意圖，並不表示圓背形狀本身無法形成風刀。

箭頭僅表示預定的氣流方向，不是求解流線。尚未進行CFD、實測或確認風速、壓損、出風均勻度。
''',encoding='utf-8')
(HERE/'原檔未修改檢查.json').write_text(json.dumps({'source_sha256_before':before,'source_sha256_after':after,'source_unchanged':True,'CFD_executed':False,'scope':'2D explanatory PNG/SVG only'},indent=2))
print('TWO_FLOWPATH_DIAGRAMS_COMPLETE_SOURCE_UNCHANGED')
