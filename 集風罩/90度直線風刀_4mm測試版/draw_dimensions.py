from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import ast,json,math
HERE=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
font=lambda n:ImageFont.truetype(FONT,n)
INK=(30,47,60);BLUE=(20,91,125);GRAY=(115,132,145);LIGHT=(210,220,227)
t=ast.parse((HERE.parent/'原版大型集風罩_尺寸圖/draw_dimensions.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef)
    and n.name in {'text','label','dash','dh','dv','arrow'}],type_ignores=[]),
    'dimension_helpers','exec'))
r=json.loads((HERE/'尺寸與流道檢查.json').read_text())
im=Image.new('RGB',(2400,1800),'white');d=ImageDraw.Draw(im)
text(im,(80,45),'90° 直線風刀測試件｜216 × 4 mm',60)
text(im,(85,132),'單位：mm　｜　向上進風 → 圓滑轉彎 → 水平出風　｜　完整單件',32,GRAY)
text(im,(300,235),'側視剖面（真實截面）',39)
s=3.75;xc=560;yb=1300
def p(y,z):return (xc+y*s,yb-z*s)
sec=r['sections']
def sides(offset):
    pos=[];neg=[]
    for a in sec:
        c=a['center_mm'];n=a['depth_normal'];half=a['depth_mm']/2+offset
        pos.append((c[1]+half*n[1],c[2]+half*n[2]))
        neg.append((c[1]-half*n[1],c[2]-half*n[2]))
    return pos,neg
outer_pos,outer_neg=sides(2)
inner_pos,inner_neg=sides(0)
for path in [outer_pos,outer_neg]:d.line([p(*a) for a in path],fill=INK,width=4)
for path in [inner_pos,inner_neg]:d.line([p(*a) for a in path],fill=BLUE,width=3)
d.line([p(*outer_pos[-1]),p(*inner_pos[-1])],fill=INK,width=4)
d.line([p(*outer_neg[-1]),p(*inner_neg[-1])],fill=INK,width=4)
for side in [-1,1]:
    d.line([p(side*46,3),p(side*60,3),p(side*60,0),p(side*44,0)],fill=INK,width=4)
dh(im,p(-60,0)[0],p(130,0)[0],1430,p(-60,0)[1],p(130,239)[1],'總深度 190 mm')
dv(im,p(0,243)[1],yb,190,p(70,243)[0],p(-60,0)[0],'總高 243 mm')
dh(im,p(70,227)[0],p(130,239)[0],330,p(70,227)[1],p(130,239)[1],'收縮 50 + 直段 10')
for a,b in zip(sec,sec[1:]):
    ca=a['center_mm'];cb=b['center_mm']
    dash(d,p(ca[1],ca[2]),p(cb[1],cb[2]),GRAY,width=2)
arrow(im,p(0,55),p(0,20),'向上進風',p(0,76),28)
arrow(im,p(158,239),p(130,239),'水平出風',p(147,215),28)
arrow(im,p(70-70/math.sqrt(2),157+70/math.sqrt(2)),p(57,167),
      '彎道中心 R70',p(50,146),28)
text(im,(1390,235),'出口端視圖（沿 −Y 方向看）',36)
text(im,(1390,292),'薄縫局部放大；寬高使用相同比例',25,GRAY)
ec=1805;ey=640;es=3.6
def e(x,z):return (ec+x*es,ey-z*es)
d.rectangle([e(-110,4),e(110,-4)],fill=(43,105,130),outline=INK,width=3)
d.rectangle([e(-108,2),e(108,-2)],fill='white',outline=INK,width=2)
dh(im,e(-108,0)[0],e(108,0)[0],500,ey-8,ey-8,'淨長 216 mm')
dh(im,e(-110,0)[0],e(110,0)[0],785,ey+15,ey+15,'最大外寬 220 mm')
dv(im,e(0,2)[1],e(0,-2)[1],2285,e(108,0)[0],e(108,0)[0],'縫寬 4 mm')
text(im,(1390,930),'接口與結構',36,BLUE)
for i,line in enumerate(['進風淨口：82 × 88 mm（原接口）',
                         '法蘭：118 × 120 × 3 mm；保留原 12 孔',
                         '主截面壁厚：2 mm',
                         '彎道截面：216 × 28 mm',
                         '出口中心高度：239 mm',
                         '彎道內側流道半徑：56 mm']):
    text(im,(1390,1000+59*i),line,28)
text(im,(130,1550),'外形：220 × 190 × 243 mm（寬 × 深 × 高）｜出口：216 × 4 mm',39,BLUE)
text(im,(130,1630),'出口是直線；僅在氣流方向轉 90°。入口與原風機相同，沒有測壓口或內部分隔板。',29)
text(im,(130,1700),'幾何與網格已檢查；未執行 CFD、均勻度／風速量測或實體試印。',28,GRAY)
im.save(HERE/'04_90度風刀_尺寸圖.png',dpi=(220,220))
im.save(HERE/'90度直線風刀_尺寸圖.pdf','PDF',resolution=220)
print('90_DEG_DIMENSIONS_SAVED',flush=True)
