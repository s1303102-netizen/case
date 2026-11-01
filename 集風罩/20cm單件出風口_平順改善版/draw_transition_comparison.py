"""A code-native geometry comparison sheet; does not represent airflow."""
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
r=json.loads((HERE/'轉接段_前後幾何比較.json').read_text())
c=Canvas();c.rect(0,0,W,14,NAVY,None)
c.text(70,52,'20 cm 單件出風口｜轉接段平順改善',43,NAVY)
c.text(70,118,'外形仍約 182.3 × 143.9 × 188.0 mm；原鼓風機接口、90° 彎道、2 mm 出風縫保留。',24,MUTED)
c.line([(70,166),(2530,166)],BORDER,2)
c.text(90,230,'A　展寬曲線比較',31,NAVY)
c.text(90,280,'橫軸：截面弧向寬度；縱軸：高度',24,MUTED)
c.text(920,230,'B　中央前後壁比較',31,NAVY)
c.text(920,280,'橫軸：前後厚度；縱軸：高度',24,MUTED)
scale=4.5;base=1450
for xcenter in [490,1250]:
    c.line([(xcenter,base+15),(xcenter,base-150*scale-20)],GREY,1.2,8)
    for z in [0,50,100,150]:
        y=base-z*scale;c.line([(xcenter-300,y),(xcenter+300,y)],BORDER,1)
        c.text(xcenter-315,y-12,str(z),22,MUTED,'right')
for version,color,dash in [('before',GREY,9),('after',BLUE,None)]:
    rows=r['section_samples'][version]
    stations=[{'z_mm':0,'width_mm':82,'depth_mm':88}]+rows+[{'z_mm':150,'width_mm':rows[-1]['width_mm'],'depth_mm':rows[-1]['depth_mm']}]
    for sign in [-1,1]:
        c.line([(490+sign*q['width_mm']/2*scale,base-q['z_mm']*scale) for q in stations],color,4 if version=='after' else 3,dash)
        c.line([(1250+sign*q['depth_mm']/2*scale,base-q['z_mm']*scale) for q in stations],color,4 if version=='after' else 3,dash)
c.line([(95,365),(175,365)],GREY,3,9);c.text(195,350,'原 20 cm 版',25,MUTED)
c.line([(480,365),(560,365)],BLUE,4);c.text(580,350,'平順改善版',25,BLUE)
c.text(90,1510,'上方接相同的 90° 彎道與原剖面噴嘴；本圖只比較轉接段與直段。',24,TEXT)
c.text(90,1560,'線條為截面尺寸示意，並非流線，也不表示已預測壓損或風速。',23,MUTED)
c.text(90,1625,'截面積沿程單調縮小：7216 → 約 2154 mm²。',26,TEAL)
c.text(90,1675,'展寬及變薄速度首尾平滑歸零；避免在短距離內集中變形。',24,TEXT)
c.rect(1700,210,830,1480,'#F8FBFD',BORDER,2)
c.text(1740,252,'在同樣高度內重新分配風道',31,NAVY)
y=330
for title,old,new in [('入口直段','20 mm','12 mm'),('轉接段','75 mm','118 mm'),('彎前直段','55 mm','20 mm')]:
    c.text(1740,y,title,26,MUTED);c.text(1740,y+45,old+' → '+new,31,BLUE);y+=145
c.line([(1740,790),(2490,790)],BORDER,2)
c.text(1740,830,'幾何角度比較（相對向上方向）',28,NAVY)
c.text(1740,890,'側緣寬度投影：約 50.2° → 29.2°',26,BLUE)
c.text(1740,945,'中央前後壁：約 46.3° → 27.2°',26,BLUE)
c.text(1740,1000,'邊緣路徑三維角：約 57.6° → 38.5°',24,TEXT)
c.text(1740,1065,'角度來自形狀計算，不是量測風速。',23,MUTED)
c.line([(1740,1120),(2490,1120)],BORDER,2)
c.text(1740,1160,'維持單件、無附加測量構造',28,NAVY)
c.text(1740,1220,'進風口：82 × 88；原法蘭與孔位',25,TEXT)
c.text(1740,1270,'出風弧長 160；2 mm 縫；R 中 28',25,TEXT)
c.text(1740,1320,'主要壁厚仍為 2 mm',25,TEXT)
c.text(1740,1390,'幾何材料體積約再減少 2.1%。',25,TEAL)
c.text(1740,1440,'不含列印支撐與切片設定。',23,MUTED)
c.text(1740,1510,'尚未實測壓損、流量與風速。',24,MUTED)
c.text(1740,1570,'列印時使用 mm、100% 比例。',24,TEXT)
c.text(1740,1620,'切片預覽確認內部支撐可移除。',23,MUTED)
c.line([(70,1750),(2530,1750)],BORDER,2)
c.text(70,1780,'原版檔案保留｜新檔只有單一實體網格｜已檢查進出風口、2 mm 縫與 20 cm 包絡｜未執行 CFD',23,MUTED)
im=c.save('轉接段_前後比較圖');im.save(HERE/'轉接段_前後比較圖.pdf','PDF',resolution=300)
print('COMPARISON_SHEET_SAVED')
