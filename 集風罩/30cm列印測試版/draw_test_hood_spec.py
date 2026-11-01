"""Dimension and test-principle sheet, built as editable SVG plus PNG/PDF."""
from pathlib import Path
import ast,math,json,html
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
W,H,FACTOR=2600,1850,2
NAVY='#18334B';TEXT='#253D4F';MUTED='#64798A';BLUE='#137FA7'
LIGHT='#E6F5FA';TEAL='#128A78';ORANGE='#D97736';GREY='#ABB6BF';BORDER='#D6E1E8'
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
tree=ast.parse((HERE.parent/'draw_right_duct.py').read_text())
defs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Canvas'],type_ignores=[])
exec(compile(defs,'drawing_primitives','exec'))
spec=json.loads((HERE.parent/'Airblade研究/Airblade原理_第二版候選尺寸.json').read_text())
arcdata=json.loads((HERE.parent/'右半邊集風罩_計算.json').read_text())['measured']
R=arcdata['fitted_arc_radius_mm'];h=spec['pre_nozzle_height_mm'];rb=28.
Lc=spec['nozzle']['converging_length_mm'];Ln=Lc+4;rv=Ln+rb;angle=240/(2*R)
def S(t):return 10*t**3-15*t**4+6*t**5
def integral(x):
    b=6.
    if x<=0:return 0.
    if x>=Lc:return Lc-b
    if x<b:
        t=x/b;return b*(t**3-.5*t**4)
    if x<=Lc-b:return x-b/2
    t=(x-Lc+b)/b;return Lc-1.5*b+b*(t-t**3+.5*t**4)
def hh(r):return 1 if r<=4 else h/2-math.tan(math.radians(7))*integral(Ln-r)
def arc(u,r):
    a=(2*u-1)*angle;return ((R+r)*math.sin(a),(R+rv)-(R+r)*math.cos(a))
def span(lam):
    pts=[((1-lam)*82*(i/300-.5)+lam*arc(i/300,rv)[0],lam*arc(i/300,rv)[1]) for i in range(301)]
    return sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
toparea=span(1)*h
c=Canvas();c.rect(0,0,W,14,NAVY,None)
c.text(70,52,'30 cm 列印測試罩｜保留原剖面，縮短出風弧',43,NAVY)
c.text(70,118,'尺寸單位 mm；原接口不縮放。旁通用於實測調整，尚未證明與原版等阻力／同風速。',24,MUTED)
c.line([(70,165),(2530,165)],BORDER,2)
c.text(90,222,'A　正面尺寸示意',31,NAVY)
c.text(90,272,'組裝約 270.8 × 182.6 × 278.0',25,BLUE)
c.text(90,315,'有效弧長 240；縫高 2；曲率半徑 749.7',24,TEXT)
c.text(980,222,'B　中央剖面：原尺寸轉彎與收縮',31,NAVY)
c.text(980,272,'彎前直段 55；R 中 28；厚度 12.173',25,BLUE)
c.text(980,315,'緩收 47.426 + 末端直段 4；兩壁最大各 7°',24,TEXT)

def front(x,z):return (490+x*2.65,1410-z*2.65)
right=[(43,0),(43,50)]
for i in range(1,61):
    lam=S(i/60);x=(1-lam)*41+lam*(R+rv)*math.sin(angle)+2
    right.append((x,50+135*i/60))
right.extend([(135.4,240),(133,268),(120,278)])
outline=[front(-x,z) for x,z in right]+[front(x,z) for x,z in reversed(right)]
c.polygon(outline,LIGHT,BLUE,3)
c.line([front(0,0),front(0,278)],GREY,1.5,8)
c.line([front(-119.5,268),front(119.5,268)],NAVY,5)
c.rect(*front(-57,3),118*2.65,3*2.65,LIGHT,BLUE,2)
c.dim(front(-135.4,-20),front(135.4,-20),'整體最大寬 270.8',size=24)
c.line([(100,1410),(100,1410-278*2.65)],MUTED,1.5)
c.text(76,1000,'高',24,MUTED);c.text(58,1040,'278',24,MUTED)
c.arrow(front(0,70),front(0,130),TEAL,4,13)
c.arrow(front(0,160),front(0,220),TEAL,4,13)
c.text(90,1550,'原接口：82 × 88；法蘭：118 × 120 × 3',25,TEXT)
c.text(90,1600,'保留原 12 孔；法蘭中心偏置 +2',24,MUTED)
c.text(90,1650,'中心切成兩片，外側 M3 對合座固定',24,MUTED)

def sec(y,z):return (1250+y*2.45,1410-z*2.45)
back=[(-44,0),(-44,50)];forward=[(44,0),(44,50)]
for i in range(1,81):
    lam=S(i/80);depth=(7216+(toparea-7216)*lam)/span(lam);z=50+135*i/80
    back.append((-depth/2,z));forward.append((depth/2,z))
back.append((-h/2,240));forward.append((h/2,240))
for i in range(1,81):
    a=math.pi/2*i/80
    back.append((rv-(Ln+(rb+h/2)*math.cos(a)),240+(rb+h/2)*math.sin(a)))
    forward.append((rv-(Ln+(rb-h/2)*math.cos(a)),240+(rb-h/2)*math.sin(a)))
for i in range(1,101):
    r=Ln*(1-i/100);back.append((rv-r,268+hh(r)));forward.append((rv-r,268-hh(r)))
c.polygon([sec(y,z) for y,z in back]+[sec(y,z) for y,z in reversed(forward)],LIGHT,BLUE,3)
# Bypass port lies on the rear of the lower neck; front-side inlet tap is offset in X.
c.polygon([sec(y,z) for y,z in [(-90,16),(-44,16),(-44,60),(-90,60)]],'#FFF0E3',ORANGE,2)
c.line([sec(-90,6),sec(-90,70)],ORANGE,8)
c.arrow(sec(-48,38),sec(-100,38),ORANGE,3,11)
c.text(980,1460,'後向旁通：Ø44 管口＋可換孔片',24,ORANGE)
c.line([sec(-10,215),(1530,870)],MUTED,1.3)
c.text(1490,820,'彎前測壓口',23,MUTED)
c.text(1490,858,'Z＝215',22,MUTED)
c.line([sec(44,10),(1570,1340)],MUTED,1.3)
c.text(1470,1275,'入口測壓口',23,MUTED)
c.text(1470,1312,'Z＝10',22,MUTED)
c.arrow(sec(0,95),sec(0,145),TEAL,3,12)
c.arrow(sec(rv,268),sec(rv+30,268),TEAL,3,12)
c.text(1430,690,'2 mm',24,BLUE)
c.text(980,1550,'側壁測壓：外徑 6／內孔 3',24,TEXT)
c.text(980,1600,'測壓口未接管時，裝封帽並密封',24,MUTED)
c.text(980,1650,'示意省略外壁厚度與對合座',23,MUTED)

c.rect(1770,210,760,1490,'#F8FBFD',BORDER,2)
c.text(1810,252,'保留原版的局部風刀條件',30,NAVY)
lines=[('2 mm 縫、90° 彎角','同風速時，縫尺度 Reynolds 數保留'),
       ('相同 R／厚度與收縮剖面','彎曲與噴嘴局部形狀保留'),
       ('弧長改為 240 mm','不能代表原 593 mm 全弧均勻度')]
y=320
for a,b in lines:
    c.text(1810,y,a,27,BLUE);c.text(1810,y+45,b,23,TEXT);y+=120
c.line([(1810,700),(2490,700)],BORDER,2)
c.text(1810,740,'假設平均風速 25 m/s：',28,NAVY)
c.text(1810,800,'原版需要：約 1.778 m³/min',27,TEXT)
c.text(1810,850,'測試主縫：約 0.720 m³/min',27,TEXT)
c.text(1810,900,'旁通差額：約 1.058 m³/min',27,ORANGE)
c.text(1810,960,'以上是尺寸換算，並非風速預測。',23,MUTED)
c.line([(1810,1015),(2490,1015)],BORDER,2)
c.text(1810,1055,'旁通孔片：',28,NAVY)
c.text(1810,1110,'封閉／28／32／36／38／40／44',25,TEXT)
c.text(1810,1160,'先試 38 mm，再按壓力與風速更換。',24,ORANGE)
c.text(1810,1210,'每次只裝一片；孔徑不等於等效阻力。',23,MUTED)
c.line([(1810,1265),(2490,1265)],BORDER,2)
c.text(1810,1305,'建議列印左右半片',28,NAVY)
c.text(1810,1365,'每片約 278 × 179.3 × 135.4',25,TEXT)
c.text(1810,1415,'各自一盤；STL 已將切面朝下。',24,TEXT)
c.text(1810,1465,'旁通片印 1 片；封帽印 2 個。',24,TEXT)
c.text(1810,1525,'接合後量測實際 2 mm 窄縫。',24,MUTED)
c.text(1810,1580,'切片時確認搭橋與支撐可移除。',23,MUTED)
c.text(1810,1630,'未經實體試印與阻力校準。',23,MUTED)
c.line([(70,1750),(2530,1750)],BORDER,2)
c.text(70,1780,'可直接接原鼓風機的短弧測試件｜原模型未修改｜幾何檢查通過；未執行 CFD 或實測',24,MUTED)
im=c.save('測試罩_尺寸與原理圖')
im.save(HERE/'測試罩_尺寸與原理圖.pdf','PDF',resolution=300)
print('SPEC_SHEET_SAVED')
