from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'尺寸與流道檢查.json').read_text());checks=json.loads((HERE/'STL_重讀檢查.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert len(r['variants'])==3 and len(checks)==3
for p,h in r['input_file_hashes'].items():assert sha(p)==h
for q in r['variants']:
    assert sha(q['blend'])==q['blend_sha256'] and sha(q['STL'])==q['STL_sha256']
    assert q['bounds_mm']['size']==[220,120,240]
for q in checks:assert sha(HERE/'STL_毫米'/q['file'])==q['sha256']
font=lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',n)
labels={
    '01_直通風刀_完整外觀.png':('直通長型風刀｜216 mm 直線出口','外形 220 × 120 × 240 mm；保留原鼓風機接口，向上直通。圖示為 6 mm 縫寬版'),
    '02_直線出口_頂部近看.png':('直線出口｜頂部局部近看','淨出風長 216 mm，兩側各 2 mm 壁厚；沒有弧線或額外內縮段。圖示為 6 mm 版'),
    '03_內部直通_剖面預覽.png':('內部剖面｜方形口逐漸變為長型狹縫','橘色為預覽切面；內部沒有 90° 彎道、橫向頂蓋或分隔板。圖示為 6 mm 版')}
for name,(title,subtitle) in labels.items():
    p=HERE/name;im=Image.open(p).convert('RGB')
    if im.height==1100:
        canvas=Image.new('RGB',(1600,1262),(248,250,252));canvas.paste(im,(0,122));d=ImageDraw.Draw(canvas)
        d.text((35,19),title,font=font(43),fill=(22,46,65));d.text((37,75),subtitle,font=font(24),fill=(55,75,88))
        d.text((37,1231),'依實際網格渲染｜完整單件列印；預覽剖面不寫入列印件；未驗證風速或消除回流',font=font(19),fill=(80,95,107))
        canvas.save(p)
    assert Image.open(p).size==(1600,1262)
rows='\n'.join(f"| 216 × {q['gap_mm']} mm | {q['outlet_area_mm2']:.0f} mm² | {q['mesh']['volume_mm3']/1000:.1f} cm³ |" for q in r['variants'])
doc='''# 直通長型風刀測試版

2026-11-01。依使用者要求，原鼓風機矩形出口轉成盡量長的直線風刀口；外寬不超過 220 mm、高度不超過 250 mm。

## 尺寸與幾何

- 三種版本的最大外包絡均為 **220 × 120 × 240 mm（寬 × 深 × 高）**。
- **淨出風長 216 mm**；加上兩側各 2 mm 壁厚，外寬正好 220 mm。
- 出風口位於最高處 Z=240 mm，最後 12 mm 是等截面的直通段，出口與前面最寬段等寬，沒有額外內縮。狹縫是直線，不是弧線。
- 氣流沿 +Z 方向向上直通；沒有原來的 90 度彎道，也不會轉成水平出風。
- 保留原進風淨口 82 × 88 mm、R3 入口角、118 × 120 × 3 mm 法蘭、12 個安裝孔及 2 mm 中心偏置。角孔 Ø6.4 mm、其餘孔 Ø4.4 mm。
- 入口直段 12 mm、連續轉接段 216 mm、出口直段 12 mm。截面壁厚名義 2 mm，隨寬度展開、厚度縮小，截面面積沿程不增加。
- 只有一個完整中空列印件，沒有測壓口、旁通口、內部分隔板或分片接縫。

這次依「盡量長」的要求增加出口長度，並非沿用先前暫定的 160 mm。三種版本總體尺寸相同，但深度收縮曲線隨最終縫寬不同；不是只有一個可更換出口零件。

## 選擇測試版本

| 出口淨尺寸 | 出口面積 | 模型材料體積（不含支撐／底邊） |
|---|---:|---:|
'''+rows+'''

**三個檔案是三種選擇，不是三個零件都要印。建議先只印 216 × 6 mm 版。**

前次 160 × 2 mm 測試件的出口面積為 320 mm²；這次三種出口分別為 432、864、1296 mm²。先用較大的 6 mm 狹縫觀察鼓風機吸口是否仍出現反吹，再視穩定性與出風狀態決定是否測 4 mm 或 2 mm。這是測試順序建議，不保證 6 mm 一定能消除回流。

由於長度、轉接段與出口面積都與原 20 cm 弧形罩不同，不能把前後差異全部歸因於取消彎道，也不能把此件視為原大型罩的等效縮小模型。

## 檔案

- `直通風刀_216x6mm.blend`／`STL_毫米/直通風刀_216x6mm_單件_mm.stl`：建議優先試的 6 mm 版。
- `直通風刀_216x4mm.blend`／對應 STL：4 mm 版。
- `直通風刀_216x2mm.blend`／對應 STL：2 mm 版。
- `01_直通風刀_完整外觀.png`、`02_直線出口_頂部近看.png`、`03_內部直通_剖面預覽.png`：由實際 6 mm 版本網格渲染。
- `04_直通風刀_尺寸圖.png`、`直通風刀_尺寸圖.pdf`：寬高、淨出風長及接口尺寸。

Blender 使用毫米場景，STL 請以毫米、100% 尺寸匯入切片軟體。三個 Blender 檔各只有一個完整列印網格；預覽剖開僅為圖片，不會出現在列印件。

## 列印與清理

以法蘭朝下、Z=0 貼列印平台的方向設計。內部沒有封頂的 90 度彎道，所有流道從下到上開放，目的是減少難以移除的內部支撐。

內壁對應路徑相對垂直的取樣最大傾角約 28 度。這是幾何值，仍需在切片軟體逐層確認外伸、線寬、層高與冷卻設定，不代表任何印表機都已驗證免支撐。切片若自動加入內部支撐，先確認是否真的需要與是否能從兩端取出，避免把細縫堵住。

220 mm 是模型本體最大寬度；切片的裙邊、支撐或機器邊界餘量需另計。原本 300 × 300 × 300 mm 的列印範圍可以容納本體。

列印後確認狹縫整條通暢、清除毛邊，法蘭貼合及固定完成後再測試。若仍發生吸口反吹、異常聲音或振動，先停止該組合的測試並記錄版本與現象。

## 檢查範圍

- 三個 Blender 均儲存後重開，確認單一網格且幾何相同於輸出的列印件。
- 每個材料網格只有一個連通實體，沒有非流形邊；STL 獨立重讀沒有退化三角面或不封閉的座標邊。
- 三個版本外包絡均為 220 × 120 × 240 mm；入口到出口中心線直通。
- 每條狹縫沿長度取樣 41 處，確認縫高及向上出口暢通；保留的 12 個法蘭孔全部通暢。
- 轉接截面面積沿程單調不增加，出口位於最大高度及最大寬度處。
- 原始 `第一版.blend` 與目前 `完整模型.blend` 均未修改。

未執行 CFD、實體試印、流量、風速或壓損驗證，也沒有保證風刀效果或回流改善。實測紀錄應先區分吸口狀態、風機聲音、狹縫各段出風與紙條測試距離，避免只用整體手感比較。

檢查紀錄：`尺寸與流道檢查.json`、`STL_重讀檢查.json`。
'''
(HERE/'使用與測試說明.md').write_text(doc,encoding='utf-8')
with zipfile.ZipFile(HERE/'STL_直通長型風刀_三種縫寬.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted((HERE/'STL_毫米').glob('*.stl')):z.write(p,p.name)
    z.write(HERE/'使用與測試說明.md','使用與測試說明.md')
bundle=HERE.parent/'直通長型風刀測試版_完整檔案.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    files=sorted(HERE.glob('*.blend'))+sorted((HERE/'STL_毫米').glob('*.stl'))+sorted(HERE.glob('*.png'))
    files += [HERE/'直通風刀_尺寸圖.pdf',HERE/'使用與測試說明.md',HERE/'尺寸與流道檢查.json',HERE/'STL_重讀檢查.json']
    assert len(list(HERE.glob('*.blend')))==3 and len(list(HERE.glob('*.png')))==4
    for p in files:z.write(p,str(Path(HERE.name)/p.relative_to(HERE)))
for p in [HERE/'STL_直通長型風刀_三種縫寬.zip',bundle]:
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    print('PACKAGED',p,p.stat().st_size,flush=True)
for p,h in r['input_file_hashes'].items():assert sha(p)==h
print('STRAIGHT_TEST_NOZZLE_DELIVERY_COMPLETE',flush=True)
