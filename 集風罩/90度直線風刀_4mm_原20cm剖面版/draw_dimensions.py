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
im=Image.new('RGB',(2600,1900),'white');d=ImageDraw.Draw(im)
text(im,(80,45),'原 20 cm 剖面修正版｜216 × 4 mm 直線風刀',60)
text(im,(85,132),'先變薄 → R28 轉 90° → 上下對稱緩收；沿用原 20 cm 的剖面構造，出口改為直線。',32,GRAY)
text(im,(300,235),'整體側視剖面',39)
s=4.6;xc=580;yb=1385
def p(y,z):return (xc+y*s,yb-z*s)
sec=r['sections'];end_y=r['outlet_center_mm'][1];cz=r['outlet_center_mm'][2]
body_end=end_y-r['integrated_knife_face_depth_mm']
frame_h=r['integrated_knife_face_total_height_mm']/2
def sidepaths(subset,offset):
    pos=[];neg=[]
    for a in subset:
        c=a['center_mm'];n=a['depth_normal'];half=a['depth_mm']/2+offset
        pos.append((c[1]+half*n[1],c[2]+half*n[2]))
        neg.append((c[1]-half*n[1],c[2]-half*n[2]))
    return pos,neg
def draw_profile(mapper,subset,flange=False):
    for offset,color,width in [(2,INK,4),(0,BLUE,3)]:
        for path in sidepaths(subset,offset):d.line([mapper(*a) for a in path],fill=color,width=width)
    # Integrated front face, preserving exact +/-2-mm inner edges.
    for sign in [-1,1]:
        shape=[(body_end,cz+sign*4),(body_end,cz+sign*frame_h),
               (end_y,cz+sign*frame_h),(end_y,cz+sign*2),(body_end,cz+sign*2)]
        d.line([mapper(*a) for a in shape],fill=INK,width=4)
    if flange:
        for sign in [-1,1]:
            d.line([mapper(sign*46,3),mapper(sign*60,3),mapper(sign*60,0),mapper(sign*44,0)],fill=INK,width=4)
draw_profile(p,sec,True)
dh(im,p(-60,0)[0],p(end_y,0)[0],1490,p(-60,0)[1],p(end_y,cz)[1],f'總深 {r["bounds_mm"]["size"][1]:.1f} mm')
dv(im,p(0,cz+frame_h)[1],yb,200,p(end_y,cz+frame_h)[0],p(-60,0)[0],f'總高 {r["bounds_mm"]["size"][2]:.0f} mm')
arrow(im,p(0,55),p(0,20),'向上進風',p(0,78),28)
arrow(im,p(end_y+20,cz),p(end_y,cz),'水平出風',p(end_y+10,cz-16),28)
text(im,(1290,235),'末段放大剖面｜薄通道轉彎＋對稱緩收',36)
text(im,(1290,295),'同上一版 20 cm 的 R28／約 12.2 mm 薄流道比例',27,GRAY)
zs=10;zx=1400;zyb=1190;zref=170
def q(y,z):return (zx+y*zs,zyb-(z-zref)*zs)
endpart=[a for a in sec if a['stage'] in {'thin_pre_bend_straight','90_degree_bend',
        'symmetric_7deg_contraction','straight_outlet_lip'} and a['center_mm'][2]>=175]
draw_profile(q,endpart)
dh(im,q(28,cz)[0],q(body_end-4,cz)[0],500,q(28,cz+6.1)[1],q(body_end-4,cz+2)[1],
   f'對稱收縮 {r["contraction_length_mm"]:.1f} mm')
dv(im,q(0,cz+2)[1],q(0,cz-2)[1],2320,q(end_y,cz)[0],q(end_y,cz)[0],'出風縫 4 mm')
dh(im,q(-r['bend_section_mm'][1]/2,180)[0],q(r['bend_section_mm'][1]/2,180)[0],1245,
   q(0,180)[1],q(0,180)[1],'彎前厚約 12.2 mm')
theta=math.pi/4
tip=q(28*(1-math.cos(theta)),185+28*math.sin(theta))
arrow(im,tip,(tip[0]+90,tip[1]+110),'中心半徑 R28',q(19,181),27)
middle_y=28+r['contraction_length_mm']/2
middle_z=cz-(r['bend_section_mm'][1]+4)/4
arrow(im,q(middle_y,middle_z),q(53,cz-19),'上下兩壁最大各 7°',q(53,cz-28),27)
arrow(im,q(end_y+15,cz),q(end_y,cz),'水平出風',q(end_y+6,cz-15),27)
text(im,(1270,1350),'出口前直段 4 mm ＋ 一體刀口面 2 mm；刀口不侵入 4 mm 淨縫。',28,GRAY)
text(im,(130,1600),f'外形：220 × {r["bounds_mm"]["size"][1]:.1f} × {r["bounds_mm"]["size"][2]:.0f} mm（寬 × 深 × 高）｜淨出口：216 × 4 mm',39,BLUE)
text(im,(130,1680),'原接口：82 × 88 mm；原法蘭：118 × 120 × 3 mm；保留原 12 孔。主壁厚 2 mm、完整單件。',29)
text(im,(130,1750),'單位 mm｜R28 與通道厚度是本案沿用尺寸；對稱噴嘴參考 EP1909627B1，不是 Dyson 原廠尺寸圖。',27,GRAY)
text(im,(130,1810),'僅完成幾何與網格檢查，沒有執行 CFD、風速／均勻度量測或實體試印。',27,GRAY)
im.save(HERE/'04_原20cm剖面_尺寸與末端放大.png',dpi=(220,220))
im.save(HERE/'原20cm剖面_尺寸圖.pdf','PDF',resolution=220)
print('20CM_PROFILE_DIMENSIONS_SAVED',flush=True)
