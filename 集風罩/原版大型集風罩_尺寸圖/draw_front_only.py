from pathlib import Path
import ast,json,math
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/STHeiti Medium.ttc'
INK=(30,47,60);BLUE=(20,91,125);GRAY=(115,132,145);LIGHT=(210,220,227)
font=lambda n:ImageFont.truetype(FONT,n)
tree=ast.parse((HERE/'draw_dimensions.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'text','label','dash','dh','dv','view'}],type_ignores=[]),'drawing_helpers','exec'))
r=json.loads((HERE/'尺寸量測與視圖.json').read_text())
data=r['parts']['右側']['views']['front']
im=Image.new('RGB',(2000,1840),'white')
text(im,(90,65),'正視圖｜沿 +Y 方向看',64)
text(im,(95,153),'原版大型集風罩（右側單件）',33,GRAY)
_,bounds=view(im,data,(350,280,1830,1530),'',True)
x0,y0,x1,y1=bounds
width=data['bounds'][1][0]-data['bounds'][0][0]
height=data['bounds'][1][1]-data['bounds'][0][1]
dh(im,x0,x1,1650,y1,y1,f'最大寬度 {width:.1f} mm')
dv(im,y0,y1,165,x0,x0,f'最大高度 {height:.1f} mm')
text(im,(95,1760),'單位：mm（毫米）',34,GRAY)
path=HERE/'原版大型集風罩_正視尺寸_mm.png'
im.save(path,dpi=(240,240))
Image.open(path).verify()
print(path)
