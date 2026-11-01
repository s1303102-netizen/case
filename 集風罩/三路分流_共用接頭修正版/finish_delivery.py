"""Label rendered assembly views, write revised instructions, and package checked files."""
from pathlib import Path
import json,hashlib,zipfile
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'修改與幾何檢查.json').read_text())
stl=json.loads((HERE/'STL_重讀檢查.json').read_text())
assert r['saved_files_reopened_and_verified'] and len(stl)==3
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in r['input_sha256_preserved'].items():assert sha(p)==h,p
for p,h in r['blend_sha256'].items():assert sha(HERE/p)==h,p
for q in stl:assert sha(HERE/'STL_毫米'/q['file'])==q['sha256']
font='/System/Library/Fonts/STHeiti Medium.ttc'
big=ImageFont.truetype(font,43);small=ImageFont.truetype(font,25)
labels={
    '01_雙側配置_透明外殼.png':('左右共用接頭｜完整配置','另一側鼓風機水平轉 180°，出口後移 80 mm；外殼透明僅供觀察內部'),
    '02_俯視_鼓風機對稱定位.png':('俯視配置｜兩側出風口中心對稱','上方小罩與軟管暫隱藏；兩側出風口中心皆為 Y = −100 mm'),
    '03_單側完整組裝.png':('單側完整組裝','1 台鼓風機 ＋ 1 個共用分流接頭 ＋ 3 支外購軟管 ＋ 3 個共用小型集風罩'),
    '04_同款分流接頭_兩件示意.png':('同款分流接頭｜全機印 2 個','同一份 STL 重複列印，依兩側鼓風機法蘭方向旋轉安裝；無須鏡像列印'),
    '05_共用小型集風罩.png':('共用小型集風罩｜全機印 6 個','沿用原款 90° 彎道與 2 mm 狹縫；本次未改變小罩形狀')}
for filename,(title,subtitle) in labels.items():
    p=HERE/filename;im=Image.open(p).convert('RGB')
    # Idempotent: do not append a second header if this script is rerun.
    if im.height==1100:
        out=Image.new('RGB',(im.width,im.height+162),(248,250,252));out.paste(im,(0,122))
        d=ImageDraw.Draw(out);d.text((35,19),title,font=big,fill=(22,46,65))
        d.text((37,75),subtitle,font=small,fill=(55,75,88))
        if filename.startswith('02_'):
            yy=122+550-(-100+30)*1600/1700
            xx=[800+v*1600/1700 for v in [-335.6132507,335.6132507]]
            for x in range(round(xx[0]),round(xx[1]),24):
                d.line((x,yy,min(x+13,xx[1]),yy),fill=(20,100,125),width=3)
            for i,x in enumerate(xx):
                d.ellipse((x-11,yy-11,x+11,yy+11),outline=(255,255,255),width=6)
                d.ellipse((x-10,yy-10,x+10,yy+10),outline=(15,110,140),width=3)
                title_='原鼓風機側' if i==0 else '轉向 180° 後重新定位'
                tx=x-145 if i==0 else x-165
                d.rounded_rectangle((tx-12,yy+75,tx+320,yy+160),radius=8,fill=(245,249,252))
                d.text((tx,yy+86),title_,font=small,fill=(22,65,86))
                d.text((tx,yy+122),'出風口中心 Y = −100 mm',font=ImageFont.truetype(font,22),fill=(40,80,100))
        d.text((37,out.height-31),'依實際交付模型渲染｜幾何配置預覽，非流體模擬結果',font=ImageFont.truetype(font,20),fill=(80,95,107))
        out.save(p)
    assert Image.open(p).size==(1600,1262)
rows=[]
for q in r['hose_records']:
    rows.append(f"| {q['side']} | {q['branch']} | {q['hood_index']} | {q['cut_length_mm']:.1f} | {q['minimum_centerline_bend_radius_mm']:.1f} |")
doc='''# 三路分流：左右共用接頭修正版（2026-10-29）

## 修改內容

在上一版完整組裝的基礎上，將左側（X 正側、原來接頭較歪的一側）鼓風機水平轉 180 度，重新定位，使其向上的出風口中心由 Y=-20 mm 移至 Y=-100 mm。出口往後移 80 mm，Z=208 mm 不變；左右出口 X 約為 ±335.613 mm。

這裡的 80 mm 是出風口中心的位移。鼓風機旋轉後，機身原點的位移不同，不應直接把物件原點往後移 80 mm 當成同一操作。

左右改用上一版較直的右側接頭網格，依各自法蘭方向旋轉安裝，取消左側偏移款。新左側三支軟管重新配置；六個小型集風罩的位置與形狀、右側整套組裝、原外殼及架傘凹槽均保留。

原始 `第一版.blend` 及 `三路分流_正式模型` 內的上一版檔案均未修改。修正版集中放在本資料夾。

## 四個 Blender 檔

| 檔案 | 內容 |
|---|---|
| `01_第一版_共用分流接頭.blend` | 完整機器，含重新定位的鼓風機、兩個相同接頭與重排軟管。 |
| `02_單側鼓風機_導管_集風罩.blend` | 原右側完整組裝；這一側未改，與上一版相同。 |
| `03_共用分流接頭.blend` | 只有一個共用接頭；全機使用兩件，毋須鏡像網格。 |
| `04_小型集風罩_共用款.blend` | 一個小型集風罩；沿用原款，全機使用六件。 |

01 延續原場景的公分數值比例及原單位設定。02–04 使用毫米場景。列印請直接使用本資料夾 `STL_毫米` 內的 STL，以毫米、100% 尺寸匯入切片軟體。

## STL 與列印數量

| STL | 包絡尺寸 mm | 全機數量 |
|---|---|---:|
| `分流接頭_左右共用_mm.stl` | 209.34 × 120.00 × 155.02 | 2 |
| `小型集風罩_共用款_直立_mm.stl` | 220.39 × 113.64 × 225.00 | 6（與下列擺法擇一） |
| `小型集風罩_共用款_斜放45度_mm.stl` | 220.39 × 166.59 × 237.35 | 同一個小罩的另一種擺法 |

全機共列印 8 件：同款接頭 2 個、小型集風罩 6 個。單側則是接頭 1 個、小罩 3 個。所有零件都在 300 × 300 × 300 mm 範圍內，皆為一次列印的單件中空零件，無測壓口。

這次接頭是將原右側款統一為共用款，STL 實體幾何不變；小罩 STL 也保持原來形狀。請以本修正版的共用接頭檔取代原先左右各印一款的做法，不要再印舊左側偏移接頭。圖中的鼓風機與軟管為外購件，不需列印。

列印方向、橋接與支撐仍需以切片逐層預覽確認。小罩的 2 mm 出風狹縫和彎道內，不能留下取不出的支撐；45 度檔僅提供另一種擺放，不保證免支撐。

## 軟管與接頭

採名義內徑 51 mm 的軟管；圖中外徑 55 mm 僅為示意。管嘴主外徑 50.6 mm、止滑圈最大外徑 51.2 mm、直套接長 25 mm，每端套入約 23 mm。管嘴內徑 46.6 mm，以保留 2 mm 列印壁厚。小罩主要壁厚約 2.4 mm。

不同軟管的實際內徑、公差與彎曲限制不同；建議先用管嘴的一小段試套，再列印整件。全機共有 12 處軟管套接，可使用合適管夾固定。

軟管編號依各側分流接頭支路標示；小罩編號由靠中央到外側依序為 1、2、3。轉向後左側的支路對應為 1→3、2→2、3→1，避免管路交叉。

下列為模型中的中心線管長，已含兩端套入長度；裁管需另留試裝調整餘量。最小彎曲半徑是幾何值，仍需與購買軟管的規格比對。

| 側別 | 接頭支路 | 對應小罩 | 模型管長 mm | 最小中心線彎曲半徑 mm |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'''

## PNG 配置圖

- `01_雙側配置_透明外殼.png`：完整組裝，外殼僅在預覽中暫時透明。
- `02_俯視_鼓風機對稱定位.png`：從上方看兩台鼓風機與接頭；上方小罩、軟管僅在此圖暫時隱藏，以標示出風口中心位置。
- `03_單側完整組裝.png`：單側鼓風機、接頭、三支軟管與小罩。
- `04_同款分流接頭_兩件示意.png`：同一個接頭重複兩件。
- `05_共用小型集風罩.png`：共用小罩。

預覽圖皆由實際交付網格渲染；透明外殼、相機與燈光的預覽處理不會寫回模型。PNG 為幾何配置預覽，不是 CFD 流場或風速模擬。

## 檢查結果與限制

- 四個 Blender 檔均重開檢查；兩側接頭網格與單獨共用接頭完全相同，六個小罩與單獨小罩完全相同。
- 左側鼓風機只有剛體旋轉與平移，沒有修改機身網格。出口仍朝上，左右出口中心位置對稱。
- 原外殼、凹槽、右側組裝、六個小罩的位置與其餘舊物件均核對保留；原始與上一版檔案雜湊不變。
- 鼓風機、接頭與六支軟管均無外殼表面穿越。新左側管路與鼓風機、非對應小罩、彼此及對側組裝沒有非預期接觸；套接位置的重疊為預留套入量。
- 兩種列印零件均為單一連通、封閉的材料網格；STL 獨立重讀檢查無非流形座標邊或退化三角面。沿用上一版相同網格的流道中心路徑與約 2 mm 狹縫檢查。
- 未進行 CFD、實際列印、壓損或風速測試；接頭共用不代表兩側流量已證明相等。

詳細紀錄：`修改與幾何檢查.json`、`STL_重讀檢查.json`。
'''
(HERE/'使用與列印說明.md').write_text(doc,encoding='utf-8')
with zipfile.ZipFile(HERE/'STL_共用款列印檔.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted((HERE/'STL_毫米').glob('*.stl')):z.write(p,p.name)
    z.write(HERE/'使用與列印說明.md','使用與列印說明.md')
full=HERE.parent/'三路分流_共用接頭修正版_完整檔案.zip'
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    selected=[Path(p) for p in r['blend_files']]+list((HERE/'STL_毫米').glob('*.stl'))+[HERE/p for p in labels]
    selected += [HERE/'使用與列印說明.md',HERE/'修改與幾何檢查.json',HERE/'STL_重讀檢查.json']
    for p in selected:z.write(p,str(Path(HERE.name)/p.relative_to(HERE)))
for p in [HERE/'STL_共用款列印檔.zip',full]:
    with zipfile.ZipFile(p) as z:assert z.testzip() is None
    print('PACKAGED',p,p.stat().st_size,flush=True)
for p,h in r['input_sha256_preserved'].items():assert sha(p)==h
print('COMPLETE_SOURCE_AND_PREVIOUS_VERSION_PRESERVED',flush=True)
