"""Two-page dimension drawing, built from measured mesh projections and checked interfaces."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,json,hashlib,zipfile
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'尺寸量測與視圖.json').read_text());right=r['parts']['右側'];left=r['parts']['左側']
FONT='/System/Library/Fonts/STHeiti Medium.ttc';W,H=3600,2546
INK=(30,47,60);BLUE=(20,91,125);GRAY=(115,132,145);LIGHT=(210,220,227);BG=(255,255,255)
font=lambda n:ImageFont.truetype(FONT,n)
def text(im,xy,s,size=37,fill=INK,anchor=None):ImageDraw.Draw(im).text(xy,s,font=font(size),fill=fill,anchor=anchor)
def label(im,xy,s,size=36,rotate=False,fill=BLUE):
    f=font(size);b=f.getbbox(s);tile=Image.new('RGB',(b[2]-b[0]+20,b[3]-b[1]+16),'white')
    ImageDraw.Draw(tile).text((10-b[0],8-b[1]),s,font=f,fill=fill)
    if rotate:tile=tile.rotate(90,expand=True)
    im.paste(tile,(round(xy[0]-tile.width/2),round(xy[1]-tile.height/2)))
def dash(d,a,b,color=LIGHT,width=2,on=16,off=11):
    dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
    if L<1:return
    t=0
    while t<L:
        e=min(t+on,L);d.line((a[0]+dx*t/L,a[1]+dy*t/L,a[0]+dx*e/L,a[1]+dy*e/L),fill=color,width=width);t+=on+off
def dh(im,x1,x2,y,e1,e2,s):
    d=ImageDraw.Draw(im);x1,x2=sorted([x1,x2])
    for x,e in [(x1,e1),(x2,e2)]:d.line((x,e,x,y+15 if y>e else y-15),fill=GRAY,width=2)
    d.line((x1,y,x2,y),fill=BLUE,width=3)
    for x,sign in [(x1,1),(x2,-1)]:d.polygon([(x,y),(x+sign*19,y-7),(x+sign*19,y+7)],fill=BLUE)
    label(im,((x1+x2)/2,y),s)
def dv(im,y1,y2,x,e1,e2,s):
    d=ImageDraw.Draw(im);y1,y2=sorted([y1,y2])
    for y,e in [(y1,e1),(y2,e2)]:d.line((e,y,x+15 if x>e else x-15,y),fill=GRAY,width=2)
    d.line((x,y1,x,y2),fill=BLUE,width=3)
    for y,sign in [(y1,1),(y2,-1)]:d.polygon([(x,y),(x-7,y+sign*19),(x+7,y+sign*19)],fill=BLUE)
    label(im,(x,(y1+y2)/2),s,rotate=True)
def arrow(im,a,b,s,pos,size=34):
    d=ImageDraw.Draw(im);d.line((a,b),fill=BLUE,width=3)
    dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
    if L:
        u=(dx/L,dy/L);v=(-u[1],u[0]);d.polygon([a,(a[0]+u[0]*19+v[0]*7,a[1]+u[1]*19+v[1]*7),(a[0]+u[0]*19-v[0]*7,a[1]+u[1]*19-v[1]*7)],fill=BLUE)
    label(im,pos,s,size=size)
def page(title,subtitle,index):
    im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
    text(im,(95,52),title,65);text(im,(100,139),subtitle,32,GRAY)
    d.line((95,215,W-95,215),fill=INK,width=3)
    d.line((95,H-135,W-95,H-135),fill=INK,width=2)
    text(im,(100,H-111),'單位 mm｜示意比例，以標註數值為準｜未標註製造公差｜來源：第一版.blend',29,GRAY)
    text(im,(100,H-64),'2026-10-31　依原模型量測，未修改模型；非流體性能驗證圖。',26,GRAY)
    text(im,(W-115,H-99),f'{index} / 2',37,INK,anchor='ra')
    return im
def view(im,data,box,title,envelope=False):
    d=ImageDraw.Draw(im);x0,y0,x1,y1=box;lo,hi=data['bounds'];s=min((x1-x0)/(hi[0]-lo[0]),(y1-y0)/(hi[1]-lo[1]))
    cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2
    def p(a):return ((x0+x1)/2+(a[0]-cx)*s,(y0+y1)/2-(a[1]-cy)*s)
    for a,b in data['segments']:d.line((p(a),p(b)),fill=INK,width=3)
    a=p((lo[0],hi[1]));b=p((hi[0],lo[1]));bounds=(a[0],a[1],b[0],b[1])
    if envelope:
        for a_,b_ in [((a[0],a[1]),(b[0],a[1])),((b[0],a[1]),(b[0],b[1])),((b[0],b[1]),(a[0],b[1])),((a[0],b[1]),(a[0],a[1]))]:dash(d,a_,b_)
    text(im,(x0,y0-83),title,43)
    return p,bounds
def rows(im,x,y,w,data,rowh=68):
    d=ImageDraw.Draw(im)
    for i,(a,b) in enumerate(data):
        yy=y+i*rowh
        if i%2==0:d.rectangle((x,yy,x+w,yy+rowh),fill=(244,248,251))
        text(im,(x+20,yy+14),a,31);text(im,(x+w-20,yy+14),b,32,BLUE,anchor='ra')

# Page 1: installed-axis external envelope and original-right-part three views.
p1=page('原版大型集風罩｜外形尺寸圖','右側單件三視圖；X／Y／Z 沿用原機器的安裝方向，尺寸不含鼓風機。',1)
pf,bf=view(p1,right['views']['front'],(230,385,1580,1450),'正視圖｜沿 +Y 方向看',True)
dh(p1,bf[0],bf[2],1545,bf[3],bf[3],'592.6　最大寬 X')
dv(p1,bf[1],bf[3],135,bf[0],bf[0],'501.9　最大高 Z')
ps,bs=view(p1,right['views']['side'],(1880,385,2570,1450),'右側視圖｜沿 −X 方向看',True)
dh(p1,bs[0],bs[2],1545,bs[3],bs[3],'328.8　最大深 Y')
pi,bi=view(p1,right['views']['iso'],(2820,430,3470,1120),'等角視圖｜形狀參考')
text(p1,(2820,1220),'90° 轉向後水平出風',32,BLUE)
text(p1,(2820,1280),'入口接鼓風機，向上進風',30,GRAY)
pt,bt=view(p1,right['views']['top'],(245,1795,1550,2295),'俯視圖｜沿 −Z 方向看',True)
dv(p1,bt[1],bt[3],1660,bt[2],bt[2],'328.8')
inlet=pt((0,0));d=ImageDraw.Draw(p1)
dash(d,(inlet[0]-60,inlet[1]),(inlet[0]+60,inlet[1]),BLUE,2,12,7)
dash(d,(inlet[0],inlet[1]-60),(inlet[0],inlet[1]+60),BLUE,2,12,7)
arrow(p1,inlet,(inlet[0]+170,inlet[1]+120),'進風接口中心',(inlet[0]+275,inlet[1]+145),30)
text(p1,(1880,1705),'主要尺寸',44)
rows(p1,1870,1780,1610,[
    ('單側最大外包絡 X × Y × Z','592.6 × 328.8 × 501.9'),
    ('進風淨口／法蘭外框','82 × 88 ／ 118 × 120'),
    ('單側有效出風弧長','592.8（弧長，非直線寬）'),
    ('出風狹縫／出口面板高','2.0 ／ 20.0'),
    ('主要殼壁／法蘭厚度','2.0 ／ 3.0'),
    ('左右合裝最大外寬 X',f"{r['combined_bounds_world_mm']['size'][0]:.1f}"),
    ('左右入口前後位置差','80.0（原模型配置）')],67)
text(p1,(1880,2290),'左右外包絡相同，入口位置與轉接形狀不同；原版須區分左右件。',29,GRAY)

# Page 2: flange pattern, actual radial nozzle section, and assembled width.
p2=page('原版大型集風罩｜接口、風刀與雙側配置','法蘭細節及狹縫剖面；藍色尺寸為模型標註，右側件為接口方向基準。',2)
text(p2,(230,275),'A｜進風法蘭平面',45)
ox,oy,k=930,970,7.0
def fp(u,v):return (ox+u*k,oy-v*k)
d=ImageDraw.Draw(p2)
def rounded_contour(w,h,rad,cx=0,cy=0):
    pp=[]
    for x,y,a in [(w/2-rad,h/2-rad,0),(-w/2+rad,h/2-rad,90),(-w/2+rad,-h/2+rad,180),(w/2-rad,-h/2+rad,270)]:
        for j in range(21):
            t=math.radians(a+90*j/20);pp.append(fp(cx+x+rad*math.cos(t),cy+y+rad*math.sin(t)))
    d.line(pp+[pp[0]],fill=INK,width=4)
rounded_contour(118,120,4,2,0);rounded_contour(82,88,3)
for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]:
    x,y=fp(2+dz,-dy);rad=3.2 if abs(dy)==51 and abs(dz)==50 else 2.2
    d.ellipse((x-rad*k,y-rad*k,x+rad*k,y+rad*k),outline=BLUE if rad==3.2 else INK,width=3)
    d.line((x-9,y,x+9,y),fill=GRAY,width=1);d.line((x,y-9,x,y+9),fill=GRAY,width=1)
dash(d,fp(-75,0),fp(80,0),GRAY,2);dash(d,fp(0,-72),fp(0,72),GRAY,2)
dh(p2,fp(-57,0)[0],fp(61,0)[0],380,fp(0,60)[1],fp(0,60)[1],'118.0　外框')
dh(p2,fp(-48,0)[0],fp(52,0)[0],465,fp(0,51)[1],fp(0,51)[1],'100.0　角孔距')
dv(p2,fp(0,60)[1],fp(0,-60)[1],1510,fp(61,0)[0],fp(61,0)[0],'120.0　外框')
dv(p2,fp(0,51)[1],fp(0,-51)[1],1620,fp(52,0)[0],fp(52,0)[0],'102.0　角孔距')
dh(p2,fp(-41,0)[0],fp(41,0)[0],1060,fp(0,0)[1],fp(0,0)[1],'82.0　淨口')
dv(p2,fp(0,44)[1],fp(0,-44)[1],420,fp(-41,0)[0],fp(-41,0)[0],'88.0　淨口')
rows(p2,225,1510,1440,[('角孔／其餘孔','4 × Ø6.4 ／ 8 × Ø4.4'),
    ('法蘭厚度／圓角','3.0 ／ 外框 R4、淨口 R3'),
    ('法蘭中心相對淨口中心','沿 118 邊方向偏移 2.0')],65)
text(p2,(235,1755),'角孔 100 × 102 為中心距；其餘孔位見圖。',29,GRAY)
text(p2,(235,1810),'右側件基準：淨口中心為 (0, 0)，法蘭中心為 (+2, 0)。',27,GRAY)

text(p2,(1900,275),'B｜出風口中段徑向剖面',45)
box=(2020,410,3450,1180);limits=((-13,107),(-86,25));sc=min((box[2]-box[0])/120,(box[3]-box[1])/111)
def np_(r_,z_):return ((box[0]+box[2])/2+(r_-47)*sc,(box[1]+box[3])/2-(z_+30.5)*sc)
plot=Image.new('RGB',(W,H),'white');pd=ImageDraw.Draw(plot)
for a,b in right['nozzle_section']:pd.line((np_(*a),np_(*b)),fill=INK,width=4)
# Crop to the physical-detail region, excluding lower tapered-body lines.
p2.paste(plot.crop((box[0],box[1],box[2],box[3])),(box[0],box[1]))
d=ImageDraw.Draw(p2);Ln=r['nominal_design']['nozzle']['total_length_mm'];h=r['nominal_design']['pre_nozzle_height_mm']
cline=[np_(Ln+28,-65),np_(Ln+28,-28)]
cline += [np_(Ln+28*math.cos(math.pi/2*j/40),-28+28*math.sin(math.pi/2*j/40)) for j in range(1,41)]
cline += [np_(0,0)]
for a,b in zip(cline,cline[1:]):dash(d,a,b,BLUE,2,10,7)
dh(p2,np_(0,0)[0],np_(Ln,0)[0],355,np_(0,10)[1],np_(Ln,8)[1],'51.43　噴嘴長')
c=np_(Ln,-28);a=np_(Ln+28/math.sqrt(2),-28+28/math.sqrt(2))
d.ellipse((c[0]-5,c[1]-5,c[0]+5,c[1]+5),fill=BLUE)
arrow(p2,a,c,'轉彎中心 R28',(c[0]+40,c[1]+110),31)
x1=np_(Ln+28-h/2,-55)[0];x2=np_(Ln+28+h/2,-55)[0];yy=1250
for xx in [x1,x2]:d.line((xx,np_(0,-55)[1],xx,yy+12),fill=GRAY,width=2)
d.line((x1-55,yy,x2+55,yy),fill=BLUE,width=3)
d.polygon([(x1,yy),(x1-19,yy-7),(x1-19,yy+7)],fill=BLUE)
d.polygon([(x2,yy),(x2+19,yy-7),(x2+19,yy+7)],fill=BLUE)
label(p2,((x1+x2)/2,yy+45),'12.17　彎前通道',size=31)
arrow(p2,np_(1,0),np_(-13,14),'出口縫 2.0',(2150,510),33)
text(p2,(1910,1350),'轉向 90°；末端收縮最大壁角 7°，直唇長 4.0。',31)
text(p2,(1910,1410),'出風縫 2.0、主要壁厚 2.0；出口面板總高 20.0。',31)
text(p2,(1910,1470),'剖面沿出風弧中段取得；R28 為通道中心線半徑。',29,GRAY)

# Both original hoods in the installed front projection.
combined=[]
for part in [right,left]:
    dx=part['port_world_mm'][0]
    for a,b in part['views']['front']['segments']:combined.append([[a[0]+dx,a[1]],[b[0]+dx,b[1]]])
bounds=r['combined_bounds_world_mm'];z0=right['port_world_mm'][2]
comb={'segments':combined,'bounds':[[bounds['min'][0],bounds['min'][2]-z0],[bounds['max'][0],bounds['max'][2]-z0]]}
cp,cb=view(p2,comb,(1930,1795,3430,2270),'C｜左右合裝正視')
dh(p2,cb[0],cb[2],2350,cb[3],cb[3],f"{bounds['size'][0]:.1f}　左右合裝最大寬")
rows(p2,225,1910,1440,[('單側有效出風弧長','592.8'),('單側出風 X 投影跨度','525.0'),
    ('中央預留不出風範圍','50.0'),('左右入口前後差','80.0')],65)
text(p2,(235,2210),'592.8 是曲線弧長，不能當作出口直線寬度。',28,GRAY)
text(p2,(235,2265),'中央 50 指有效出風範圍；面板外緣間隙另受壁厚影響。',27,GRAY)

files=[HERE/'01_原版大型集風罩_外形尺寸.png',HERE/'02_原版大型集風罩_接口與剖面.png']
for im,p in zip([p1,p2],files):im.save(p,dpi=(217.714,217.714))
pdf=HERE/'原版大型集風罩_尺寸圖.pdf'
p1.save(pdf,'PDF',resolution=217.714,save_all=True,append_images=[p2],title='原版大型集風罩尺寸圖',author='Model dimensions from 第一版.blend')
source=Path(r['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==r['source_sha256']
readme='''# 原版大型集風罩尺寸圖

來源為目前磁碟上的 `第一版.blend`，原檔未修改。原場景數值沿用已確認的公分比例，量測時乘 10 換算毫米。

- `01_原版大型集風罩_外形尺寸.png`：右側單件正視、右側視、俯視、等角視與最大外包絡。
- `02_原版大型集風罩_接口與剖面.png`：法蘭孔位、出風口中段徑向剖面、左右合裝最大寬。
- `原版大型集風罩_尺寸圖.pdf`：上述兩頁的 A3 橫式 PDF。

單側最大外形依安裝 X/Y/Z 為 592.6 × 328.8 × 501.9 mm。左右外包絡相同，但原版進風接口前後相差 80 mm，因此並非完全相同的兩個零件。

外包絡與投影線來自實際網格。接口及風道細節以建模參數為基準，另檢查原網格 12 個法蘭孔暢通、左右各 19 處出風縫約為 2 mm。單側有效出口弧長 592.8 mm 不等於直線投影跨度 525 mm。

此為模型尺寸參考圖，未標註完整製造公差，不能直接當作已核准生產的施工圖。圖面示意比例，以標註尺寸為準，沒有執行 CFD 或流量測試。

量測記錄與實際投影線：`尺寸量測與視圖.json`。
'''
(HERE/'尺寸圖說明.md').write_text(readme,encoding='utf-8')
bundle=HERE/'原版大型集風罩_尺寸圖.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[pdf,HERE/'尺寸圖說明.md',HERE/'尺寸量測與視圖.json']:z.write(p,p.name)
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
print('DIMENSION_DRAWINGS_COMPLETE',json.dumps([str(p) for p in files+[pdf,bundle]],ensure_ascii=False),flush=True)
