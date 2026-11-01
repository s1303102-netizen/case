"""True sections of old/new delivery triangles, rendered as a dimensioned PNG."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
F='/System/Library/Fonts/STHeiti Medium.ttc'
font=lambda n:ImageFont.truetype(F,n)
def section(triangles,axis,value,coords):
    out=[]
    for tri in triangles:
        ds=[v[axis]-value for v in tri]
        if max(abs(v) for v in ds)<1e-8:continue
        points=[]
        for i in range(3):
            a=tri[i];b=tri[(i+1)%3];da=ds[i];db=ds[(i+1)%3]
            if abs(da)<1e-8:points.append(tuple(a[j] for j in coords))
            if da*db<0:
                t=da/(da-db);points.append(tuple(a[j]+t*(b[j]-a[j]) for j in coords))
        unique={tuple(round(p[i],7) for i in range(2)):p for p in points};points=list(unique.values())
        if len(points)>=2:
            pairs=[(sum((a[k]-b[k])**2 for k in range(2)),a,b) for i,a in enumerate(points) for b in points[i+1:]]
            _,a,b=max(pairs)
            if sum((a[k]-b[k])**2 for k in range(2))>1e-14:out.append((a,b))
    return out
im=Image.new('RGB',(1800,1710),(245,248,251));draw=ImageDraw.Draw(im)
draw.text((45,22),'分流接頭｜實際網格剖面比較',font=font(48),fill=(18,48,65))
draw.text((48,86),'比較矩形根部貼合與兩片分隔板前緣；尺寸單位 mm，剖面直接取自交付網格',font=font(25),fill=(65,83,97))
old=json.loads((HERE/'舊接頭三角面.json').read_text());new=json.loads((HERE/'新接頭三角面.json').read_text())
def panel(x,y,title,segments,xlim,ylim,color,fill,annotations,footer):
    w,h=825,710;canvas=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(canvas)
    d.text((23,13),title,font=font(30),fill=color)
    scale=min((w-110)/(xlim[1]-xlim[0]),(h-145)/(ylim[1]-ylim[0]))
    cx=(xlim[0]+xlim[1])/2;cy=(ylim[0]+ylim[1])/2
    def p(a):return (w/2+(a[0]-cx)*scale,75+(h-145)/2-(a[1]-cy)*scale)
    pix=[(p(a),p(b)) for a,b in segments]
    # Even-odd scan conversion fills only actual material between closed contours.
    for yy in range(75,h-60):
        v=yy+.5;xs=[]
        for a,b in pix:
            if (a[1]<=v<b[1]) or (b[1]<=v<a[1]):xs.append(a[0]+(v-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        xs.sort()
        for a,b in zip(xs[::2],xs[1::2]):d.line((max(0,a),yy,min(w-1,b),yy),fill=fill)
    for a,b in pix:d.line((a,b),fill=color,width=2)
    for a in range(math.ceil(xlim[0]/10)*10,math.floor(xlim[1]/10)*10+1,10):
        q=p((a,ylim[0]));d.text((q[0]-12,h-58),str(a),font=font(16),fill=(95,110,120))
    for text_,point,offset in annotations:
        a=p(point);b=(a[0]+offset[0],a[1]+offset[1]);d.line((a,b),fill=(195,79,38),width=2)
        d.ellipse((a[0]-4,a[1]-4,a[0]+4,a[1]+4),fill=(195,79,38))
        box=d.textbbox((0,0),text_,font=font(22));tw=box[2]-box[0]
        tx=max(8,min(w-tw-8,b[0]));ty=max(52,min(h-88,b[1]-24))
        d.rectangle((tx-4,ty-3,tx+tw+4,ty+28),fill='white')
        d.text((tx,ty),text_,font=font(22),fill=(150,64,35))
    d.rectangle((0,0,w,52),fill='white');d.text((23,13),title,font=font(30),fill=color)
    d.rectangle((0,h-30,w,h),fill=(242,246,249));d.text((17,h-29),footer,font=font(20),fill=(56,76,88))
    draw.rounded_rectangle((x-1,y-1,x+w+1,y+h+1),radius=9,outline=(205,216,225),width=2)
    im.paste(canvas,(x,y))
panel(50,155,'舊版｜橫剖 Z＝44.1',section(old,2,44.1,(0,1)),(-49,49),(-49,49),(85,95,105),(225,230,234),
      [('內側角落有較大的圓角材料',(-14,41),(38,-60))],'灰色為材料；白色為流道')
panel(925,155,'新版｜同一高度橫剖',section(new,2,44.1,(0,1)),(-49,49),(-49,49),(17,102,123),(195,227,231),
      [('分隔板接側壁，不再留大圓角墊塊',(-14,42),(15,-65))],'保留外側入口 R3；分隔處以直壁連續銜接')
panel(50,920,'舊版｜縱剖 Y＝0',section(old,1,0,(0,2)),(-46,46),(0,62),(85,95,105),(225,230,234),
      [('分流前緣約在 Z＝44，起始較鈍',(-14,44),(-60,-45))],'箭頭朝向位置為舊分流前緣；氣流由下往上')
panel(925,920,'新版｜同一縱剖',section(new,1,0,(0,2)),(-46,46),(0,62),(17,102,123),(195,227,231),
      [('圓弧鼻端 R0.4，基準厚 0.8',(-14,20.4),(-110,85)),('逐漸加厚至 2.0', (14,39.9),(28,-35))],
      'Z＝20 開始分流；至 Z＝40 平順接上三路')
draw.text((48,1657),'幾何修正版｜未進行 CFD、壓損或風速實測；不是流場模擬結果',font=font(23),fill=(60,79,94))
im.save(HERE/'01_內流道剖面_新舊比較.png')
print('ACTUAL_MESH_SECTION_COMPARISON_DRAWN',flush=True)
