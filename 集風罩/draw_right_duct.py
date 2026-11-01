"""Generate vector technical drawings and matching PNG/PDF previews."""
from pathlib import Path
import json
import math
import html
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
D=json.loads((HERE/'右半邊集風罩_計算.json').read_text())
G=json.loads((ROOT/'鼓風機/集風罩_現況幾何.json').read_text())
W,H=2600,1850
FACTOR=2
NAVY='#18334B';TEXT='#253D4F';MUTED='#64798A';BLUE='#137FA7'
LIGHT='#E6F5FA';TEAL='#128A78';ORANGE='#D97736';GREY='#ABB6BF';BORDER='#D6E1E8'
FONT='/System/Library/Fonts/STHeiti Medium.ttc'


class Canvas:
    def __init__(self):
        self.image=Image.new('RGB',(W*FACTOR,H*FACTOR),'white')
        self.d=ImageDraw.Draw(self.image)
        self.svg=[]
        self.fonts={}
    def font(self,size):
        if size not in self.fonts:self.fonts[size]=ImageFont.truetype(FONT,round(size*FACTOR))
        return self.fonts[size]
    def points(self,pts):return [(round(x*FACTOR),round(y*FACTOR)) for x,y in pts]
    def polygon(self,pts,fill=LIGHT,stroke=BLUE,width=2):
        pts=list(pts)
        if fill:self.d.polygon(self.points(pts),fill=fill)
        if stroke:self.d.line(self.points(pts+[pts[0]]),fill=stroke,width=round(width*FACTOR),joint='curve')
        self.svg.append('<polygon points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+
                        f'" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
    def line(self,pts,color=TEXT,width=2,dash=None):
        pts=list(pts)
        if dash:
            for a,b in zip(pts,pts[1:]):
                length=math.dist(a,b);n=max(1,math.ceil(length/(dash*2)))
                for i in range(n):
                    t0=i*dash*2/length if length else 0;t1=min(1,(i*dash*2+dash)/length) if length else 1
                    if t0>=1:continue
                    p=(a[0]+(b[0]-a[0])*t0,a[1]+(b[1]-a[1])*t0)
                    q=(a[0]+(b[0]-a[0])*t1,a[1]+(b[1]-a[1])*t1)
                    self.d.line(self.points([p,q]),fill=color,width=round(width*FACTOR))
        else:self.d.line(self.points(pts),fill=color,width=round(width*FACTOR),joint='curve')
        self.svg.append('<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+
                        f'" fill="none" stroke="{color}" stroke-width="{width}"'+
                        (f' stroke-dasharray="{dash},{dash}"' if dash else '')+'/>' )
    def rect(self,x,y,w,h,fill=None,stroke=BORDER,width=2):
        self.polygon([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],fill,stroke,width)
    def circle(self,x,y,r,fill=BLUE,stroke=None,width=1):
        self.d.ellipse([(round((x-r)*FACTOR),round((y-r)*FACTOR)),(round((x+r)*FACTOR),round((y+r)*FACTOR))],fill=fill,outline=stroke,width=round(width*FACTOR))
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
    def text(self,x,y,body,size=26,color=TEXT,anchor='left'):
        body=body.translate(str.maketrans('风头绘内减','風頭繪內減'))
        font=self.font(size);bbox=self.d.textbbox((0,0),body,font=font);tw=bbox[2]-bbox[0]
        offset=0 if anchor=='left' else (tw/FACTOR/2 if anchor=='center' else tw/FACTOR)
        self.d.text(((x-offset)*FACTOR,y*FACTOR-bbox[1]),body,font=font,fill=color)
        anch={'left':'start','center':'middle','right':'end'}[anchor]
        self.svg.append(f'<text x="{x}" y="{y+size*.86}" font-size="{size}" fill="{color}" text-anchor="{anch}">{html.escape(body)}</text>')
    def arrow(self,a,b,color=TEAL,width=3,head=12):
        self.line([a,b],color,width)
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        p=(b[0]-head*math.cos(angle)+head*.45*math.sin(angle),b[1]-head*math.sin(angle)-head*.45*math.cos(angle))
        q=(b[0]-head*math.cos(angle)-head*.45*math.sin(angle),b[1]-head*math.sin(angle)+head*.45*math.cos(angle))
        self.polygon([b,p,q],color,None)
    def dim(self,a,b,label,color=MUTED,offset=0,size=24):
        self.line([a,b],color,1.6)
        self.arrow((a[0]+(b[0]-a[0])*.15,a[1]+(b[1]-a[1])*.15),a,color,1.4,8)
        self.arrow((b[0]+(a[0]-b[0])*.15,b[1]+(a[1]-b[1])*.15),b,color,1.4,8)
        self.text((a[0]+b[0])/2,(a[1]+b[1])/2-29+offset,label,size,color,'center')
    def save(self,stem):
        self.image.save(HERE/(stem+'.png'),dpi=(300,300))
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="298.846mm" viewBox="0 0 2600 1850">'
        svg+='<rect width="2600" height="1850" fill="white"/><g font-family="STHeiti, PingFang TC, Noto Sans CJK TC, sans-serif">'
        svg+=''.join(self.svg)+'</g></svg>'
        (HERE/(stem+'.svg')).write_text(svg,encoding='utf-8')
        return self.image


def hull(points):
    points=sorted(set((round(p[0],4),round(p[1],4)) for p in points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def heading(c,title,subtitle,page):
    c.rect(0,0,W,14,NAVY,None)
    c.text(70,54,title,44,NAVY)
    c.text(70,119,subtitle,24,MUTED)
    c.line([(70,166),(2530,166)],BORDER,2)
    c.text(70,1788,'初步流道設計｜尺寸為通風淨尺寸，非製造圖｜一維估算，未做 CFD 或實測｜Blender 檔案未修改',23,MUTED)
    c.text(2530,1788,f'{page} / 2',25,MUTED,'right')


R=D['measured']['fitted_arc_radius_mm'];CY=D['measured']['fitted_arc_center_Y_mm']
t0,t1=[math.radians(a) for a in D['measured']['arc_theta_degrees']]
tf=math.radians(D['design']['feed_theta_degrees'])
pc=D['design']['plenum_feed_point_mm'];n=(math.sin(tf),math.cos(tf));tangent=(-math.cos(tf),math.sin(tf))
old=D['blower_position']['old_port_center_cm'];new=D['blower_position']['proposed_port_center_cm']
cosa,sina=math.cos(-tf),math.sin(-tf)
def moved(p):
    x,y,z=[p[i]-old[i] for i in range(3)]
    return [new[0]+cosa*x-sina*y,new[1]+sina*x+cosa*y,new[2]+z]
newverts=[moved(p) for p in G['blower']['verts']]
arc=lambda angle,depth=0:(-(R+depth)*math.sin(angle),CY-(R+depth)*math.cos(angle))
angles=[t0+(t1-t0)*i/160 for i in range(161)]
L=D['measured']['right_arc_length_mm']
leftlength,rightlength=D['design']['branch_lengths_mm']


c=Canvas()
heading(c,'右半邊集風罩｜俯視配置與出風口','右側＝現有鼓風機所在側（X 負側）；圖面右方以此側呈現。左右各一台鼓風機，中央保留 50 mm。',1)
c.text(90,207,'A　俯視配置',32,NAVY)
c.text(90,251,'俯視圖含不同高度零件的投影；藍色弧形罩位於 Z ≈ 700，鼓風機仍在底部。',24,MUTED)
def plan(p):return (775-p[0]*.90,650-p[1]*.90)
machine=[plan(p) for p in [(-700,-250),(700,-250),(700,250),(-700,250)]]
c.polygon(machine,'#FAFCFD',GREY,3)
c.text(160,897,'機器後壁 Y = −250',23,MUTED)
c.text(285,442,'機器前方 +Y',23,MUTED)
c.arrow((1420,735),(1420,652),MUTED,2)
c.text(1410,612,'+Y',23,MUTED,'center')
# The unbuilt mirror half is only a pale reference outline.
c.line([plan((-arc(a)[0],arc(a)[1])) for a in angles],GREY,2,8)
c.text(205,582,'另一半邊',28,GREY)
c.text(205,625,'本次不設計',23,GREY)
front=[arc(a) for a in angles];back=[arc(a,85) for a in reversed(angles)]
# Current and proposed blower footprints; neither is an actual 3-D edit.
oldhull=hull([(p[0]*10,p[1]*10) for p in G['blower']['verts']])
newhull=hull([(p[0]*10,p[1]*10) for p in newverts])
c.line([plan(p) for p in oldhull+[oldhull[0]]],GREY,2.6,8)
c.polygon([plan(p) for p in newhull],'#E8F3EF',TEAL,2.6)
c.polygon([plan(p) for p in front+back],LIGHT,BLUE,3)
c.line([plan(arc(a,35)) for a in angles],BLUE,1.7,6)
c.line([plan(arc(a)) for a in angles],BLUE,5)
for a in [t0+(t1-t0)*i/10 for i in range(1,10)]:
    p=arc(a);q=(p[0]+math.sin(a)*70,p[1]+math.cos(a)*70)
    c.arrow(plan(p),plan(q),TEAL,3,11)
# Bend envelope in plan; the riser becomes straight before the elbow.
local=lambda r,u:(pc[0]-n[0]*r+tangent[0]*u,pc[1]-n[1]*r+tangent[1]*u)
c.polygon([plan(local(r,u)) for r,u in [(85,-50),(185,-50),(185,50),(85,50)]],None,BLUE,2)
newp=plan((new[0]*10,new[1]*10));oldp=plan((old[0]*10,old[1]*10));upperp=plan(local(150,0))
c.line([newp,upperp,plan(local(85,0))],BLUE,2.5,5)
c.circle(*newp,7,TEAL);c.circle(*oldp,6,GREY)
c.arrow(oldp,newp,ORANGE,3,15)
c.text(1120,988,'出風口中心往開口中心移 260 mm',27,ORANGE,'center')
c.line([oldp,(1305,950)],ORANGE,1.5)
c.text(998,456,'新位置：平面內轉約 −30°',27,TEAL)
c.text(998,499,'出風口朝上、維持底部高度',24,TEAL)
c.line([(1085,544),newp],TEAL,1.5)
c.text(1348,814,'原位置',24,MUTED,'right')
c.text(935,839,'弧形罩總深 85',24,BLUE,'center')
gapl,gapr=plan((25,-149)),plan((-25,-149))
c.line([(775,415),(775,910)],GREY,1.3,7)
c.dim((gapl[0],955),(gapr[0],955),'中央 50',MUTED,42,23)
c.line([(gapl[0],gapl[1]),(gapl[0],955)],GREY,1)
c.line([(gapr[0],gapr[1]),(gapr[0],955)],GREY,1)
c.dim((plan((0,0))[0],1048),(plan((-550,0))[0],1048),'從開口中心到外端：550',MUTED,0,24)
c.text(845,1078,'有效右側：X = −25 至 −550；投影寬 525',25,BLUE)
c.dim((machine[1][0],351),(machine[0][0],351),'外殼全寬 1400',MUTED,0,25)

# An unfolded front view makes the 20-mm cutout and 2-mm exit gap legible.
c.text(90,1170,'B　右側出風口展開圖',32,NAVY)
c.text(90,1218,'沿圓弧展開；真正出風縫跟隨原圓弧，不是直線切開。',24,MUTED)
x0,y0=130,1340;scale=1.9;width=L*scale
c.rect(x0,y0,width,100,'#F2F5F7',GREY,2)
c.rect(x0,y0+45,width,10,BLUE,None)
c.dim((x0,y0-45),(x0+width,y0-45),f'有效弧長 {L:.0f}',MUTED,0,25)
c.text(x0,y0+125,'靠中央：離中心 25',24,MUTED)
c.text(x0+width,y0+125,'最外端：X = −550',24,MUTED,'right')
feedx=x0+leftlength*scale
c.arrow((feedx,y0+240),(feedx,y0+105),BLUE,3)
c.text(feedx,y0+260,'供氣接近中段',25,BLUE,'center')
c.dim((x0,y0+202),(feedx,y0+202),f'弧長 {leftlength:.0f}',MUTED,0,23)
c.dim((feedx,y0+202),(x0+width,y0+202),f'弧長 {rightlength:.0f}',MUTED,0,23)
c.text(1330,1347,'原洞口高 20',25,MUTED)
c.text(1330,1394,'新增出風縫高 2.0',25,BLUE)
c.text(1330,1441,'上下各約 9 封閉',23,MUTED)
c.text(90,1709,'箭頭代表出风方向，非 CFD 流線；各段皆水平朝圓弧內側吹出（+Y 且朝開口中心）。',23,MUTED)

# Right-side summary panel.
c.rect(1590,210,930,1485,'#F8FBFD',BORDER,2)
c.text(1630,251,'建議先採用的形狀',32,NAVY)
items=[('進風接口','原鼓風機淨口 82 × 88'),
       ('升風道','平滑偏移；截面逐漸變為 100 × 70'),
       ('90° 彎头','中心半徑 65；加 1 片彎曲導流片'),
       ('弧形均壓腔','淨高 70、直腔深 50'),
       ('末端收縮','深 35，平滑收至 2 mm'),
       ('全罩最大深','50 + 35 = 85；建議壁厚 2'),
       ('有效出風縫',f'沿弧 {L:.0f} × 高 2.0；可調 1.5–3.0')]
for i,(label,value) in enumerate(items):
    y=319+i*81
    c.text(1630,y,label,25,MUTED)
    c.text(1630,y+35,value,27,TEXT)
c.line([(1630,925),(2480,925)],BORDER,2)
c.text(1630,960,'鼓風機是否需移動？',30,NAVY)
c.text(1630,1010,'此方案建議移動；機身仍落地。',29,TEAL)
c.text(1630,1062,'舊出風口中心（cm）',23,MUTED)
c.text(1630,1096,f'({old[0]:.2f}, {old[1]:.2f}, {old[2]:.2f})',30,TEXT)
c.text(1630,1150,'建議出風口中心（cm）',23,MUTED)
c.text(1630,1184,f'({new[0]:.2f}, {new[1]:.2f}, {new[2]:.2f})',30,TEAL)
c.text(1630,1240,'先繞出風口中心旋轉，再移到上述位置。',24,TEXT)
c.text(1630,1280,'位移為接口中心的位移，不是物件原點值。',23,MUTED)
c.line([(1630,1338),(2480,1338)],BORDER,2)
c.text(1630,1370,'空間校核',30,NAVY)
c.text(1630,1420,'鼓風機、風道均在 1400 × 500 外殼内。',26,TEXT)
c.text(1630,1470,f'均壓罩最靠後處，距後壁約 {D["clearance"]["plenum_back_wall_clearance_mm"]:.0f} mm。',26,TEXT)
c.text(1630,1520,'需再扣除實際外殼板厚與安裝公差。',24,MUTED)
c.text(1630,1583,'若需保持原位置：仍可繞管接到此處，',24,MUTED)
c.text(1630,1626,'但管路更長，需另重算偏移及局部損失。',24,MUTED)
img1=c.save('右半邊集風罩_01平面圖')


c=Canvas()
heading(c,'右半邊集風罩｜90° 剖面與流體估算','所有標示為 mm；末端由均壓腔轉成薄片噴流。風壓、流量與風速必須同時符合工作點。',2)
c.text(90,208,'C　沿供氣中心線的垂直剖面',32,NAVY)
c.text(90,251,'升風道與接口部分為投影示意；主彎頭與噴嘴依標示尺寸绘製。',23,MUTED)
Z=pc[2];zc=Z-65
def sec(r,z):return (1110-r*1.7,1660-z*1.7)
# Floor and the back-envelope plane at the feed center.
backr=(250+pc[1])/n[1]
c.line([sec(backr,0),sec(backr,785)],GREY,2,8)
c.text(455,325,'外殼後壁',25,MUTED)
c.text(455,365,'須扣除板厚',23,MUTED)
c.line([sec(-100,0),sec(backr+25,0)],GREY,3)
c.text(850,1708,'底板 Z = 0',24,MUTED)
# Project the proposed blower in this section.
projected=[(sum((pc[i]-p[i]*10)*n[i] for i in range(2)),p[2]*10) for p in newverts]
c.polygon([sec(*p) for p in hull(projected)],'#EDF1F3',GREY,2.5)
c.text(1040,1490,'鼓風機',28,MUTED)
c.text(1040,1537,'出風口朝上',24,MUTED)
# Smooth offset rise; exact normal offsets keep a consistent normal section.
r0=sum((pc[i]-new[i]*10)*n[i] for i in range(2));z0=new[2]*10
neckend=z0+50;straightstart=zc-130
def S(t):return 10*t**3-15*t**4+6*t**5
def Sd(t):return 30*t*t-60*t**3+30*t**4
center=[(r0,z0),(r0,neckend)];side1=[(r0+44,z0),(r0+44,neckend)];side2=[(r0-44,z0),(r0-44,neckend)]
for j in range(1,101):
    tt=j/100;r=r0+(150-r0)*S(tt);z=neckend+(straightstart-neckend)*tt
    slope=(150-r0)*Sd(tt)/(straightstart-neckend);norm=math.sqrt(1+slope*slope)
    half=(88-18*S(tt))/2
    center.append((r,z));side1.append((r+half/norm,z-half*slope/norm));side2.append((r-half/norm,z+half*slope/norm))
center.append((150,zc));side1.append((185,zc));side2.append((115,zc))
c.polygon([sec(*p) for p in side1+list(reversed(side2))],LIGHT,BLUE,3)
c.line([sec(*p) for p in center],BLUE,1.5,5)
# Quarter-circle elbow: 100-mm outer, 30-mm inner radius, mean 65.
outer=[(85+100*math.cos(a),zc+100*math.sin(a)) for a in [math.pi/2*i/100 for i in range(101)]]
inner=[(85+30*math.cos(a),zc+30*math.sin(a)) for a in [math.pi/2*i/100 for i in range(100,-1,-1)]]
c.polygon([sec(*p) for p in outer+inner],LIGHT,BLUE,3)
rv=D['design']['vane_radius_mm']
c.line([sec(85+rv*math.cos(math.pi/2*i/100),zc+rv*math.sin(math.pi/2*i/100)) for i in range(101)],NAVY,2.2)
c.polygon([sec(r,z) for r,z in [(85,Z+35),(35,Z+35),(35,Z-35),(85,Z-35)]],LIGHT,BLUE,3)
noz_upper=[sec(r,Z+1+34*S(max(0,(r-4)/31))) for r in [35*i/100 for i in range(101)]]
noz_lower=[sec(r,Z-1-34*S(max(0,(r-4)/31))) for r in [35*i/100 for i in range(100,-1,-1)]]
c.polygon(noz_upper+noz_lower,LIGHT,BLUE,3)
c.line([sec(0,Z-10),sec(0,Z-1)],GREY,5)
c.line([sec(0,Z+1),sec(0,Z+10)],GREY,5)
c.line([sec(0,Z-85),sec(0,Z-10)],GREY,2,8)
c.line([sec(0,Z+10),sec(0,Z+85)],GREY,2,8)
c.arrow(sec(150,zc-95),sec(150,zc-40),TEAL,3,12)
c.arrow(sec(r0,z0+10),sec(r0,z0+44),TEAL,3,12)
c.arrow(sec(35,Z),sec(-75,Z),TEAL,4,17)
c.text(1150,508,'水平吹出',27,TEAL)
c.text(1150,550,'薄片噴流',25,TEAL)
# Leaders and dimension labels.
c.text(90,442,'90° 彎頭：R中 = 65',29,BLUE)
c.text(90,486,'R内 = 30；R外 = 100',26,TEXT)
c.text(90,530,'導流片 R ≈ 55、厚 1',26,TEXT)
c.line([(473,550),sec(85+rv*.7071,zc+rv*.7071)],BLUE,1.5)
c.text(90,658,'彎頭前直段：130',29,BLUE)
c.text(90,702,'淨截面 100 × 70',26,TEXT)
c.line([(480,721),sec(185,zc-65)],BLUE,1.5)
c.text(90,980,'平滑 S 形升風道',29,BLUE)
c.text(90,1024,'淨截面由 82 × 88',26,TEXT)
c.text(90,1068,'緩變至 100 × 70',26,TEXT)
c.text(90,1112,'有效面積減少約 3%',24,MUTED)
c.line([(475,1140),sec(r0+(150-r0)*.5,(neckend+straightstart)/2)],BLUE,1.5)
c.text(90,1370,'接口直段：50',29,BLUE)
c.text(90,1414,'對接原 120 × 118 法蘭',25,TEXT)
c.line([(505,1442),sec(r0+44,z0+25)],BLUE,1.5)
c.text(1080,620,'均壓腔 50 × 高70',25,BLUE)
c.line([(1160,602),sec(65,Z-35)],BLUE,1.5)
c.text(1080,708,'收縮深35 → 縫高2.0',25,BLUE)
c.line([(1210,689),sec(20,Z-15)],BLUE,1.5)
c.dim(sec(85,Z+83),sec(0,Z+83),'50 + 35 = 85',MUTED,-8,23)
c.line([sec(85,Z+35),sec(85,Z+83)],GREY,1)
c.line([sec(0,Z+10),sec(0,Z+83)],GREY,1)
c.line([(1410,sec(0,z0)[1]),(1410,sec(0,Z)[1])],MUTED,1.5)
c.arrow((1410,sec(0,z0)[1]-60),(1410,sec(0,z0)[1]),MUTED,1.5,8)
c.arrow((1410,sec(0,Z)[1]+60),(1410,sec(0,Z)[1]),MUTED,1.5,8)
c.text(1392,770,'升高',24,MUTED,'right')
c.text(1392,814,f'{Z-z0:.0f}',28,MUTED,'right')
c.text(1392,857,'mm',24,MUTED,'right')
c.text(1180,1315,f'接口 Z = {z0:.0f}',23,MUTED)
c.text(1130,423,f'出風縫 Z ≈ {Z:.0f}',24,MUTED)

# Calculation summary on the right.
c.rect(1590,210,930,1490,'#F8FBFD',BORDER,2)
c.text(1630,253,'資料與計算條件',32,NAVY)
c.text(1630,311,'規格圖：330 W／2800 rpm',28,TEXT)
c.text(1630,355,'11 m³/min／460 Pa 靜壓',28,TEXT)
c.text(1630,404,'沒有完整 Q–P 曲線；不把兩數值同時代入。',24,MUTED)
c.text(1630,463,'出風面積',25,MUTED)
c.text(1630,498,f'A = {L:.0f} × 2 = {L*2:.0f} mm²',31,BLUE)
c.text(1630,552,'公式：Q = A × V；q = ½ρV²',27,TEXT)
c.text(1630,597,'ρ = 1.2 kg/m³；沿程摩擦 + 局部損失',24,MUTED)
c.text(1630,638,'另計弧腔沿途出風，非只套伯努力方程。',24,MUTED)
c.line([(1630,694),(2480,694)],BORDER,2)
c.text(1630,730,'達到目標風速，需要的工作點',28,NAVY)
c.text(1630,781,'平均風速',25,MUTED)
c.text(1900,781,'單側流量',25,MUTED)
c.text(2210,781,'所需靜壓',25,MUTED)
for i,case in enumerate(D['required_cases'][1:4]):
    y=833+i*66
    c.text(1630,y,f'{case["mean_velocity_m_s"]:.0f} m/s',29,TEXT)
    c.text(1900,y,f'{case["flow_m3_min"]:.2f} m³/min',29,TEXT)
    c.text(2210,y,f'{case["fan_static_Pa"]:.0f} Pa',29,TEAL if i==1 else TEXT)
case=D['conditional_cases'][-1]
c.text(1630,1048,'若工作靜壓實際維持 460 Pa：',26,MUTED)
c.text(1630,1095,f'約 {case["mean_velocity_m_s"]:.1f} m/s；{case["flow_m3_min"]:.2f} m³/min',34,TEAL)
c.text(1630,1152,'這是條件估算，並非目前風機實測值。',25,MUTED)
c.line([(1630,1208),(2480,1208)],BORDER,2)
c.text(1630,1247,'為何先選 2 mm？',29,NAVY)
c.text(1630,1295,'縮小出口主要提高薄片性；流量同時下降。',24,TEXT)
c.text(1630,1338,'縫高减半不等於風速加倍，極限由風壓決定。',24,TEXT)
c.text(1630,1401,'建議用墊片調至 1.5–3 mm，首輪採 2 mm。',24,TEXT)
c.text(1630,1444,'刀口留 3–5 mm 平直段，內壁光滑、接縫密封。',23,TEXT)
c.text(1630,1505,'1-D 模型的風速沿弧差異約 2–3%；',24,MUTED)
c.text(1630,1548,'未包含彎頭渦流、入口衝擊與加工誤差。',24,MUTED)
c.text(1630,1608,'均勻性與最佳形狀需由 CFD／原型測試確認。',24,MUTED)
img2=c.save('右半邊集風罩_02剖面與計算')
img1.save(HERE/'右半邊集風罩_平面與剖面.pdf',save_all=True,append_images=[img2],resolution=314.476,quality=94)
print('DRAWINGS_WRITTEN',str(HERE))
