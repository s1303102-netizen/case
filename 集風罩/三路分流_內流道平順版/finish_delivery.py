from pathlib import Path
import json,hashlib,zipfile
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'流道幾何檢查.json').read_text());stl=json.loads((HERE/'STL_重讀檢查.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert r['saved_blends_verified'] and r['flange_12_bolt_paths_clear'] and len(stl)==3
for p,h in r['input_hashes'].items():assert sha(p)==h,p
for p,h in r['output_blend_sha256'].items():assert sha(HERE/p)==h,p
for q in stl:assert sha(HERE/'STL_毫米'/q['file'])==q['sha256']
font=lambda n:ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',n)
labels={
    '02_平順接頭_完整外觀.png':('共用分流接頭｜內流道平順版','原鼓風機法蘭孔位與三個軟管端的位置保留；全機使用同款 2 個'),
    '03_內部剖開_薄前緣.png':('內部剖面｜矩形入口連續分三路','橘色為預覽切面；分隔板以 R0.4 薄圓弧鼻端起始，再漸厚至 2 mm'),
    '04_鼻端與矩形根部_近看.png':('局部近看｜兩片薄前緣分隔板','鼻端圓弧半徑 0.4 mm，基準厚度 0.8 mm；移除根部多餘圓角墊塊'),
    '05_整機_平順接頭配置.png':('整機配置｜兩側共用新接頭','以目前儲存的整機為基礎，只替換接頭；透明外殼僅為預覽效果')}
for name,(title,subtitle) in labels.items():
    p=HERE/name;im=Image.open(p).convert('RGB')
    if im.height==1100:
        canvas=Image.new('RGB',(1600,1262),(248,250,252));canvas.paste(im,(0,122));d=ImageDraw.Draw(canvas)
        d.text((35,19),title,font=font(43),fill=(22,46,65));d.text((37,75),subtitle,font=font(25),fill=(55,75,88))
        d.text((37,1231),'實際網格渲染｜預覽剖面不會寫入列印件；未進行 CFD 或風速實測',font=font(20),fill=(80,95,107))
        canvas.save(p)
    assert Image.open(p).size==(1600,1262)
doc='''# 三路分流接頭：內流道平順版

## 這次修改

這版處理矩形進風口接到三路時的多餘圓角材料、局部台階與較鈍的分隔板前緣。接頭仍為一個中空、一體列印零件，左右兩側共用同款。

- 保留與鼓風機相符的 82 × 88 mm 淨入口及 R3 外角，不把鼓風機原本的圓角接口硬改成銳角。
- 三路的矩形根部改為外側貼合入口、內側貼合兩片分隔板，取消原本各支路圓角矩形在分流處留下的圓角墊塊。內部直壁在接合處保持連續，再逐漸變成圓形管路。
- 兩片分隔板從 Z=20 mm 起始，以半徑 0.4 mm 的圓弧鼻端迎風，在 Z=20.4 mm 處厚約 0.8 mm，再以 19.6 mm 長的平順曲線加厚，到 Z=40 mm 時為 2 mm，接上三路的矩形根部。
- 鼻端是圓弧形，最前端截線自然趨近零寬；「0.8 mm」指圓弧鼻端後的基準厚度，並非把整片分隔板都做成 0.8 mm，也不是全長零厚度刀片。
- 保留原法蘭 118 × 120 mm、12 個安裝孔、三個軟管端的中心位置與方向、名義內徑 51 mm 軟管規格。管嘴主外徑 50.6 mm、止滑圈最大外徑 51.2 mm、內徑 46.6 mm、套接長 25 mm。

新接頭包絡約 209.36 × 120.00 × 155.02 mm，仍在 300 × 300 × 300 mm 列印範圍內。外部尺寸與上一版有不足 0.1 mm 級的取樣差異；支路漸變外形也配合新內壁重新生成，並非只有外觀倒角。

## Blender 檔案

| 檔案 | 內容 |
|---|---|
| `01_第一版_內流道平順版.blend` | 以目前使用者已儲存的整機檔為基礎，只更換左右接頭網格。 |
| `02_單側組裝_內流道平順版.blend` | 單側鼓風機、更新接頭、原三支軟管與三個小罩。 |
| `03_共用分流接頭_內流道平順版.blend` | 單獨一個完整、未剖開的新版接頭。 |
| `04_小型集風罩_共用款.blend` | 沿用前版相同小罩。 |

原始 `第一版.blend` 與 `三路分流_共用接頭修正版` 內的檔案均未改寫。整機檔在前次交付後曾被儲存過；此次採用目前磁碟上的內容，並逐項核對接頭之外的所有物件、幾何與位置保持不變。

01 延續原場景的公分數值比例與原單位顯示設定；02–04 使用毫米場景。列印直接使用 `STL_毫米` 內的 STL，以毫米、100% 匯入。

## 列印檔與數量

- `分流接頭_左右共用_內流道平順_mm.stl`：新接頭，全機印 2 個。取代前一版接頭 STL。
- `小型集風罩_共用款_直立_mm.stl`：沿用原小罩，全機 6 個。
- `小型集風罩_共用款_斜放45度_mm.stl`：同一個小罩的另一種擺放方向，與直立檔擇一使用。

如果已印好小罩，這次不需要因接頭修改而重印小罩。鼓風機與軟管是外購件。全機仍為接頭 2 個＋小罩 6 個；這次沒有新增測壓孔或分成兩片。

薄前緣是否能成形需在切片預覽確認，鼻端後的 0.8 mm 基準厚度需能被所用噴嘴與線寬解析。注意分隔板起始處的橋接及支撐，避免留下取不出的內部支撐；從進風口清除毛邊及線絲時不要折傷鼻端。模型尚未實印，不能保證免支撐。

## 預覽圖

- `01_內流道剖面_新舊比較.png`：從新舊實際三角面取得同位置的橫剖與縱剖，灰色是舊版、藍色是新版，白色是空氣通道。
- `02_平順接頭_完整外觀.png`：完整接頭外觀。
- `03_內部剖開_薄前緣.png`：剖開後查看三條內壁和兩片分隔板。
- `04_鼻端與矩形根部_近看.png`：薄鼻端與入口局部放大。
- `05_整機_平順接頭配置.png`：整機使用新版接頭的配置。

剖開、橘色切面及透明外殼只用於 PNG，不會寫進交付 Blender 或 STL。列印檔是完整零件。

## 已完成的檢查

- 新接頭為單一連通材料實體，沒有非流形邊。STL 獨立重讀無非流形座標邊或退化三角面，正體積約 165398 mm³。
- 三條完整中心路徑、三個管嘴出口、12 個原安裝孔均通暢。
- 矩形轉接處在接合面前後 1 mm 範圍的 12 處角落路徑通暢；下方主入口直壁量得半寬 41 mm、半深 44 mm。
- 兩片分隔板前段各取 6 個高度量測，厚度由約 0.80 mm 逐漸增至 2.00 mm。
- 根部外壁在不同高度與方向共 78 條射線檢查連續性，取樣壁厚約不小於 2 mm。這是取樣結果，並非全模型最小壁厚證明。
- 四個 Blender 檔均重開檢查；整機兩個接頭、單側組裝接頭與單獨列印件為相同網格，接頭安裝變換保持不變，沒有穿越外殼。
- 其餘原物件逐項核對保持不變，原始與上一版輸入檔案雜湊保持不變。

這些是幾何與列印網格檢查，未進行 CFD、風速、壓損或實際列印測試。修改針對可見台階與前緣鈍厚，尚不能宣稱風阻降低特定比例，也不能保證流量增加。

檢查紀錄：`流道幾何檢查.json`、`STL_重讀檢查.json`。
'''
(HERE/'使用與列印說明.md').write_text(doc,encoding='utf-8')
with zipfile.ZipFile(HERE/'STL_內流道平順版.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted((HERE/'STL_毫米').glob('*.stl')):z.write(p,p.name)
    z.write(HERE/'使用與列印說明.md','使用與列印說明.md')
full=HERE.parent/'三路分流_內流道平順版_完整檔案.zip'
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    selected=sorted(HERE.glob('*.blend'))+sorted((HERE/'STL_毫米').glob('*.stl'))+sorted(HERE.glob('*.png'))
    selected += [HERE/'使用與列印說明.md',HERE/'流道幾何檢查.json',HERE/'STL_重讀檢查.json']
    assert len(list(HERE.glob('*.blend')))==4 and len(list(HERE.glob('*.png')))==5
    for p in selected:z.write(p,str(Path(HERE.name)/p.relative_to(HERE)))
for p in [HERE/'STL_內流道平順版.zip',full]:
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    print('PACKAGED',p,p.stat().st_size,flush=True)
for p,h in r['input_hashes'].items():assert sha(p)==h
print('SMOOTH_FLOW_REVISION_COMPLETE',flush=True)
