from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from zipfile import ZipFile, ZIP_DEFLATED
import json, hashlib
HERE = Path(__file__).resolve().parent
r = json.loads((HERE/'尺寸與流道檢查.json').read_text())
stlcheck = json.loads((HERE/'STL_重讀檢查.json').read_text())
assert r['source_files_unchanged'] and r['saved_blend_reopened']
assert r['mesh']['nonmanifold_edges']==0 and r['mesh']['material_components']==1
assert len(stlcheck)==1 and stlcheck[0]['collapsed_triangles']==0
assert stlcheck[0]['nonmanifold_coordinate_edges']==0
for path, expected in r['source_hashes'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected, path

notes = f'''# 90 度直線風刀｜216 × 4 mm 單件測試版

2026-11-01。保留原鼓風機接口，把氣流由向上轉成水平；出口本身仍為直線，不做成圓弧。

## 尺寸與流道

- 最大外形 **220 × 190 × 243 mm（寬 × 深 × 高）**，符合寬不超過 220 mm、高不超過 250 mm。
- 淨出風口 **216 × 4 mm**，面積 **864 mm²**；出口方向 +Y，進風方向 +Z，兩者夾角 90°。
- 出口中心：X=0、Y=130、Z=239 mm。Z=0 是原接口法蘭底面。
- 原鼓風機進風淨口 **82 × 88 mm、R3**；法蘭 **118 × 120 × 3 mm**；孔位、孔徑與 2 mm 偏置都沿用直通測試件。角孔四個 Ø6.4 mm，其餘八個 Ø4.4 mm。
- 主截面名義壁厚 **2 mm**，完整中空單件。沒有測壓口、旁通、分流板、內部均壓網或需要組合的上下半殼。

氣流路徑依序是：

1. 12 mm 原矩形直段。
2. 145 mm 垂直轉接段：寬 82 → 216 mm、深 88 → 28 mm；依沿程不增加的截面面積安排深度，再以平滑進度曲線連接。
3. **中心半徑 R70 mm** 的 90° 彎道，維持 **216 × 28 mm** 截面；彎道內側空氣邊界半徑 **56 mm**。沒有用 4 mm 薄縫直接繞過彎角。
4. 50 mm 最後收縮段：上壁與彎道頂部平接，下壁平滑抬升，將深度 28 → 4 mm。末端轉接曲線切線回到水平。
5. 10 mm 等截面的 216 × 4 mm 直線出口。出口位於最前緣，保留整個 216 mm 有效長度；上壁沒有額外凹進去。

## 這版與直通 4 mm 版的比較限制

兩版有相同鼓風機接口、216 mm 淨長及 4 mm 縫寬，但轉接長度、厚度分布與流道長度不同；不能把前後所有差異都歸因於新增的 90° 彎道。

本版先展寬、再轉彎、最後收縮，是供實測的幾何候選；**尚未驗證整條風刀的均勻度，也不保證消除中間強／兩側弱、低風量或吸口反吹。** 沒有執行 CFD、流量／風速／壓損測量或實體試印。網格封閉與幾何暢通不是性能驗證。

## 檔案與使用

- `90度直線風刀_216x4mm.blend`：毫米場景，只有一個完整列印實體，沒有未套用的修改器。
- `90度直線風刀_216x4mm_單件_mm.stl`：同一個實體，切片匯入選毫米、100%，不要把數值當成公分或公尺。
- `01_90度風刀_完整外觀.png`、`02_直線4mm出口_近看.png`、`03_90度內流道_剖面.png`：由實際網格渲染；剖開只用於圖片，交付列印件是完整外殼。
- `04_90度風刀_尺寸圖.png`、`90度直線風刀_尺寸圖.pdf`：側面剖面、出口端視圖與毫米尺寸。
- `尺寸與流道檢查.json`、`STL_重讀檢查.json`：尺寸、封閉性及幾何通道的檢查紀錄。

原有直通版、`第一版.blend`、`完整模型.blend` 都沒有修改。

## 列印方向與彎道支撐

這次交付仍是單件，不需分成兩半。增加 90° 彎道後，法蘭朝下直接印可能會在彎道上壁生成難取出的內部支撐，不能沿用直通件的姿態就認定免支撐。

可先在切片軟體試繞 X 軸 **+45°**，讓入口與出口的軸線各接近列印垂直方向的 45°，再把本體移到平台；這只是評估姿態的起點，**不是已經驗證免支撐的設定**。旋轉後須重新確認整體包絡、底邊與外部支撐，不能直接套用原始姿態的 220 × 190 × 243 mm 包絡。

列印前逐層檢查：彎管內部若仍需支撐，確認能從原 82 × 88 mm 入口取出；不要把取不出的密實支撐封進彎道。若所用設備、材料與姿態無法做到可清理，先調整姿態或支撐方案。主體材料體積約 **{r['mesh']['volume_mm3']/1000:.1f} cm³**，不含支撐、底邊及切片差異。

## 已完成的幾何檢查

- Blender 儲存後重開，與 STL 對應同一網格；封閉材料實體只有一個，非流形邊 0。
- STL 另外重新解析：退化三角面 0、非封閉座標邊 0、正材料體積。
- 全寬取樣 {r['slot_sample_count']} 處，檢查 4 mm 縫高及水平出口暢通；原 12 個固定孔暢通。
- 檢查 {r['clear_widthwise_geometric_paths']} 條沿寬度分布的幾何路徑沒有碰到材料；這些是幾何取樣線，**不是 CFD 計算的流線**。
- 原始檔案雜湊值一致，未更動。
'''
(HERE/'使用與列印說明.md').write_text(notes)

fontpath='/System/Library/Fonts/STHeiti Medium.ttc'
labels=[('01_90度風刀_完整外觀.png','90° 直線風刀｜216 × 4 mm','外形 220 × 190 × 243 mm｜原鼓風機接口｜完整單件'),
        ('02_直線4mm出口_近看.png','出口近看｜216 mm 直線 × 4 mm 狹縫','出口水平吹出；出口本身沒有做成圓弧'),
        ('03_90度內流道_剖面.png','內流道剖面｜先展寬，再轉彎，最後收縮','彎道 R70 mm、截面 216 × 28 mm｜僅圖片剖開，列印檔完整')]
for filename,title,subtitle in labels:
    path=HERE/filename
    with Image.open(path) as src:
        if src.height!=1100:
            continue
        src=src.convert('RGB')
        im=Image.new('RGB',(src.width,src.height+150),'white')
        im.paste(src,(0,150))
    d=ImageDraw.Draw(im)
    d.text((48,25),title,font=ImageFont.truetype(fontpath,46),fill=(27,51,67))
    d.text((48,94),subtitle,font=ImageFont.truetype(fontpath,27),fill=(76,94,107))
    im.save(path)

files=[p for p in HERE.iterdir() if p.suffix in {'.blend','.stl','.png','.pdf','.md','.json'}]
assert len([p for p in files if p.suffix=='.blend'])==1
assert len([p for p in files if p.suffix=='.stl'])==1
assert len([p for p in files if p.suffix=='.png'])==4
package=HERE.parent/'90度直線風刀_216x4mm_完整檔案.zip'
with ZipFile(package,'w',ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p,arcname=HERE.name+'/'+p.name)
with ZipFile(package) as z:
    assert z.testzip() is None
for p in HERE.glob('*.png'):
    with Image.open(p) as im:im.verify()
print('90_DEG_DELIVERY_COMPLETE',package,package.stat().st_size,flush=True)
