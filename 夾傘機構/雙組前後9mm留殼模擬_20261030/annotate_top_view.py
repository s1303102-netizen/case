"""Deterministic engineering dimension plate, PNG + native SVG annotations.

The source rendering is embedded unchanged. Vector dimension lines are projected
from actual model coordinates with project_dimensions.py, not AI estimated.
"""
from pathlib import Path
import json,math,base64,hashlib
from html import escape
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'投影與尺寸資料.json').read_text())
source=Path(data['source_image'])
source_bytes=source.read_bytes()
source_hash=hashlib.sha256(source_bytes).hexdigest()
font_path='/System/Library/Fonts/STHeiti Light.ttc'
bold_path='/System/Library/Fonts/STHeiti Medium.ttc'
WIDTH,HEIGHT=2400,2020
OX,OY=475,220
BLUE='#285f9f'
ORANGE='#b66120'
GREEN='#087969'
GRAY='#526273'
INK='#172b42'
im=Image.new('RGB',(WIDTH,HEIGHT),'white')
src=Image.open(source).convert('RGB')
assert src.size==(1450,1450)
im.paste(src,(OX,OY))
draw=ImageDraw.Draw(im)
svg=[f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
     f'<image x="{OX}" y="{OY}" width="1450" height="1450" href="data:image/png;base64,{base64.b64encode(source_bytes).decode()}"/>']


def text(x,y,body,size=32,color=INK,bold=False,anchor='left',background=False):
    font=ImageFont.truetype(bold_path if bold else font_path,size)
    length=draw.textlength(body,font=font)
    xx=x-(length/2 if anchor=='center' else length if anchor=='right' else 0)
    if background:
        draw.rounded_rectangle((xx-7,y-5,xx+length+7,y+size+8),radius=5,fill='white')
        svg.append(f'<rect x="{xx-7}" y="{y-5}" width="{length+14}" height="{size+13}" rx="5" fill="white"/>')
    draw.text((xx,y),body,font=font,fill=color)
    sa={'left':'start','center':'middle','right':'end'}[anchor]
    svg.append(f'<text x="{x}" y="{y+size*.89}" font-family="Heiti SC, PingFang TC, Noto Sans CJK TC, sans-serif" font-size="{size}" font-weight="{600 if bold else 400}" text-anchor="{sa}" fill="{color}">{escape(body)}</text>')


def line(a,b,color,width=3,dashed=False):
    length=math.dist(a,b)
    if dashed and length:
        for start in range(0,math.ceil(length),14):
            t0,t1=start/length,min((start+7)/length,1)
            aa=tuple(a[i]+(b[i]-a[i])*t0 for i in range(2))
            bb=tuple(a[i]+(b[i]-a[i])*t1 for i in range(2))
            draw.line((aa,bb),fill=color,width=width)
    else:
        draw.line((a,b),fill=color,width=width)
    dash=' stroke-dasharray="7 7"' if dashed else ''
    svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{color}" stroke-width="{width}"{dash}/>')


def polyline(points,color,width=3):
    for a,b in zip(points,points[1:]):
        line(a,b,color,width)


def polygon(points,color):
    draw.polygon(points,fill=color)
    svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+f'" fill="{color}"/>')


def canvas_point(point):
    return (point[0]+OX,point[1]+OY)


def dimension(name,color,extensions=True):
    item=data['dimension_projection'][name]
    a,b,da,db=[canvas_point(item[k]) for k in ('a','b','da','db')]
    if extensions:
        line(a,da,color,2,True)
        line(b,db,color,2,True)
    line(da,db,color,3)
    theta=math.atan2(db[1]-da[1],db[0]-da[0])
    length=math.dist(da,db)
    head=min(13,length/3.2)
    wing=min(4.6,head*.4)
    for p,ang in ((da,theta),(db,theta+math.pi)):
        dx,dy=math.cos(ang),math.sin(ang)
        polygon([p,(p[0]+head*dx+wing*dy,p[1]+head*dy-wing*dx),
                   (p[0]+head*dx-wing*dy,p[1]+head*dy+wing*dx)],color)
    return ((da[0]+db[0])/2,(da[1]+db[1])/2)


def label(x,y,title,value,color,route,anchor='left'):
    polyline(route,color,2)
    text(x,y,title,30,color,False,anchor,True)
    text(x,y+41,value,42,color,True,anchor,True)


text(65,30,'雙驅動輪俯視尺寸標註',54,INK,True)
text(65,105,'單位：mm　｜　標註依模型座標投影；兩組機構與外殼位置維持不變。',30)
text(65,155,'藍：輪間距　　橘：驅動輪厚度　　綠：輪殼間隙　　灰：保留外殼厚度',29,GRAY)

# Centerline-to-centerline dimension, clearly distinct from the free face gap.
p=dimension('center',BLUE)
label(1995,835,'兩驅動輪中心距','60 mm',BLUE,[p,(1885,875),(1975,875)])

# The axial dimensions form an 82 mm internal chain: 2+18+42+18+2.
p=dimension('rear_thickness',ORANGE)
label(105,790,'後驅動輪厚度','18 mm',ORANGE,[p,(525,835),(440,835)])
p=dimension('front_thickness',ORANGE)
label(105,1300,'前驅動輪厚度','18 mm',ORANGE,[p,(550,1345),(440,1345)])
p=dimension('net_gap',BLUE)
label(105,1050,'兩輪輪面淨距','42 mm',BLUE,[p,(545,1095),(440,1095)])

p=dimension('rear_clearance',GREEN)
label(1975,465,'後輪輪面至後殼內面','2 mm',GREEN,[p,(1840,510),(1950,510)])
p=dimension('front_clearance',GREEN)
label(1975,1260,'前輪輪面至前殼內面','2 mm',GREEN,[p,(1860,1305),(1950,1305)])

# Radial side clearances: shortest distance from the D76 rim to the X=+/-45 wall.
p=dimension('left_clearance',GREEN,False)
text(p[0]+43,p[1]+10,'7 mm',32,GREEN,True,background=True)
p=dimension('right_clearance',GREEN,False)
text(p[0]-70,p[1]+27,'7 mm',32,GREEN,True,anchor='right',background=True)

p=dimension('rear_skin',GRAY)
label(105,505,'後側外殼厚度','9 mm',GRAY,[p,(640,610),(435,550)])
p=dimension('front_skin',GRAY)
label(1120,1530,'前側外殼厚度','9 mm',GRAY,[p,(1020,1505),(1100,1575)])

# Side clearance labels are repeated as a textual key to prevent mistaking
# the shaft/hub clearance for the large-wheel clearance.
text(1995,1055,'左右輪緣至殼內壁',29,GREEN,background=True)
text(1995,1097,'各 7 mm',37,GREEN,True,background=True)

line((65,1730),(2335,1730),'#d4dce4',2)
text(65,1754,'沿軸方向：9（殼）＋2（隙）＋18（後輪）＋42（淨距）＋18（前輪）＋2（隙）＋9（殼）＝100 mm',31,INK,True)
text(65,1813,'內部空間：長 82 mm、寬 90 mm；兩顆驅動輪均為 Ø76 × 厚18 mm。',30)
text(65,1869,'綠色 2 mm 指大輪輪面至殼內面；輪轂至殼內面約 0.4 mm，共用軸端至殼內面約 0.2 mm。',29,GREEN)
text(65,1922,'左右 7 mm 為輪緣最短間隙。底部間隙約 6 mm（俯視未顯示）。數值為模型名義尺寸，未含製作公差。',28,GRAY)

im.save(OUT/'05_俯視尺寸標註.png')
document=f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'+''.join(svg)+'</svg>'
(OUT/'05_俯視尺寸標註.svg').write_text(document,encoding='utf-8')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
report={'original_top_view_modified':False,'source_image_sha256':source_hash,
    'dimension_values_mm':data['values_mm'],'annotations':'Camera-projected engineering vector dimensions',
    'source_render_embedded_unchanged':True,'output_files':['05_俯視尺寸標註.png','05_俯視尺寸標註.svg']}
(OUT/'05_俯視尺寸標註_資料.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
