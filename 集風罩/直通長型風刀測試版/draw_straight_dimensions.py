from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,ast,math
HERE=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc';font=lambda n:ImageFont.truetype(FONT,n)
INK=(30,47,60);BLUE=(20,91,125);GRAY=(115,132,145);LIGHT=(210,220,227)
t=ast.parse((HERE.parent/'原版大型集風罩_尺寸圖/draw_dimensions.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'text','label','dash','dh','dv','arrow'}],type_ignores=[]),'dimension_helpers','exec'))
r=json.loads((HERE/'尺寸與流道檢查.json').read_text());q=next(q for q in r['variants'] if q['gap_mm']==6)
im=Image.new('RGB',(2400,1800),'white');d=ImageDraw.Draw(im)
text(im,(80,45),'直通長型風刀測試件｜尺寸圖',61)
text(im,(85,130),'向上直通，無 90° 彎道；出口為直線，位於最高處及最大寬度處。',31,GRAY)
text(im,(180,225),'正視圖',41);text(im,(1650,225),'側視圖（6 mm 版）',41)
s=4.15;xc=760;yb=1370
def pf(x,z):return (xc+x*s,yb-z*s)
def ps(y,z):return (1830+y*s,yb-z*s)
sec=q['sections']
front=[(-57,0),(61,0),(61,3),(43,3),(43,12)]+[(a['inner_width_mm']/2+2,a['z_mm']) for a in sec if a['z_mm']>12]
front += [(-110,240)]+[(-a['inner_width_mm']/2-2,a['z_mm']) for a in reversed(sec) if a['z_mm']>=12]
front += [(-43,3),(-57,3),(-57,0)]
d.line([pf(*p) for p in front],fill=INK,width=4)
side=[(-60,0),(60,0),(60,3),(46,3),(46,12)]+[(a['inner_depth_mm']/2+2,a['z_mm']) for a in sec if a['z_mm']>12]
side += [(-5,240)]+[(-a['inner_depth_mm']/2-2,a['z_mm']) for a in reversed(sec) if a['z_mm']>=12]
side += [(-46,3),(-60,3),(-60,0)]
d.line([ps(*p) for p in side],fill=INK,width=4)
dh(im,pf(-108,240)[0],pf(108,240)[0],300,pf(0,240)[1],pf(0,240)[1],'淨出風長 216 mm')
dh(im,pf(-110,0)[0],pf(110,0)[0],1470,yb,yb,'最大外寬 220 mm')
dv(im,pf(0,240)[1],yb,155,pf(-110,240)[0],pf(-57,0)[0],'總高度 240 mm')
dh(im,ps(-60,0)[0],ps(60,0)[0],1470,yb,yb,'最大深度 120 mm')
arrow(im,ps(0,238),ps(33,217),'向上出風 +Z',ps(18,201),30)
text(im,(130,1570),'淨口：216 × 2／4／6 mm，三種版本擇一列印。',37,BLUE)
text(im,(130,1640),'鼓風機接口：淨口 82 × 88 mm；法蘭 118 × 120 × 3 mm；原 12 孔保留。',31)
text(im,(130,1710),'單位 mm｜主截面壁厚 2 mm｜完整單件列印｜以標註尺寸為準，無性能保證。',28,GRAY)
out=HERE/'04_直通風刀_尺寸圖.png';im.save(out,dpi=(220,220))
im.save(HERE/'直通風刀_尺寸圖.pdf','PDF',resolution=220,title='直通長型風刀測試件尺寸圖')
print('STRAIGHT_DIMENSION_DRAWING_COMPLETE',flush=True)
