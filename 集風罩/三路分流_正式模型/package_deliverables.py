from pathlib import Path
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'模型與列印檢查.json').read_text());stl=json.loads((HERE/'STL_重讀檢查.json').read_text())
assert r['saved_files_reopened_and_verified'] and len(stl)==4
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
for q in stl:assert hashlib.sha256((HERE/'STL_毫米'/q['file']).read_bytes()).hexdigest()==q['sha256']
rows=[]
for key,title in [('右側','右側分流接頭'),('左側','左側分流接頭'),('集風罩','共用小型集風罩')]:
    size=r['parts'][key]['bounds']['size'];qty='1' if key!='集風罩' else '6'
    rows.append('| '+title+' | '+' × '.join(f'{v:.1f}' for v in size)+' | '+qty+' |')
hose_rows=[]
for q in r['hose_cut_lengths']:
    hose_rows.append(f"| {q['side']} | {q['branch']} | {q['cut_length_mm']:.1f} | {q['minimum_centerline_bend_radius_mm']:.1f} |")
text='''# 三路分流集風罩：四個 Blender 檔與列印 STL

原始「第一版.blend」保持原狀；新的完整場景另存為 01 檔。使用原場景的公分數值比例。雨傘沿用先前僅PNG預覽的決定，未加入這次的3D模型。

## 四個 Blender 檔

| 檔案 | 內容 |
|---|---|
| `01_第一版_三路分流集風罩.blend` | 完整機器；原左右大集風罩換成兩套三路分流、外購管與小罩；原外殼、凹槽、鼓風機、相機及燈光不變。 |
| `02_單側鼓風機_導管_集風罩.blend` | 原鼓風機所在的右半邊（X負側）；一台鼓風機、一個接頭、三支管、三個小罩。 |
| `03_分流接頭_左右款.blend` | 左右兩款接頭，各為單一連通網格，一次列印成形。兩個物件分開陳列，不是合印為一件。 |
| `04_小型集風罩_共用款.blend` | 一款共用小罩；單側用3個，全機用6個。 |

01保留原場景單位設定；02–04以毫米顯示。列印請使用 `STL_毫米` 資料夾內的STL，以毫米、100%尺寸匯入切片軟體。

## 要印的零件

| 零件 | 包絡尺寸 mm | 全機數量 |
|---|---|---:|
'''+ '\n'.join(rows)+'''

只做單側時：選對方向的分流接頭1個＋共用小罩3個。做整台時：右接頭1個＋左接頭1個＋共用小罩6個，共8件。鼓風機與導風管是外購物件，不在列印STL內。

`小型集風罩_共用款_直立_mm.stl` 與 `小型集風罩_共用款_斜放45度_mm.stl` 是同一個零件的兩種擺放，選一種列印即可。45度版包絡約220.4×166.6×237.3mm，也在30cm範圍內。

所有列印件均為單件中空件，不需分成兩片。材料網格封閉、流道兩端開放；不含測壓孔、旁通或接合耳。主要罩壁約2.4mm，套管嘴壁厚2mm。法蘭沿用118×120mm外框、82×88mm開口及12個安裝孔。

## 軟管與套接端

- 按內徑51mm軟管設計；管嘴主外徑50.6mm、止滑小凸圈最大外徑51.2mm、直套接長度25mm。圖中軟管外徑55mm僅為外購管示意。
- 管嘴內徑46.6mm，用於保留2mm列印壁厚，並非全程51mm等截面。根部與罩內流道採漸變銜接。這個短縮徑的實際壓損尚未量測。
- 組裝時每端套入約23mm，再用合適管夾固定；單側6個管夾，全機12個。不同廠牌的管徑公差與柔軟度不同，先用管嘴的一小段試套，再決定完整列印與鎖緊方式。
- 兩台鼓風機前後位置不同，左側接頭因此有向後的偏移，不能直接把右側接頭當左側用。

下表為模型中的軟管中心線長度，已包含兩端套入範圍；實際裁管需留試裝調整餘量。最小彎曲半徑是幾何數值，仍需與實品型錄的半徑定義及最小值比對。

| 側別 | 支路 | 模型管長 mm | 最小中心線彎曲半徑 mm |
|---|---:|---:|---:|
'''+ '\n'.join(hose_rows)+'''

## 切片與列印

STL已接地為Z=0，尺寸都小於300×300×300mm。這是可匯入切片的幾何檔，不代表已實印測試。小罩含90度彎道與薄狹縫，請先查看逐層預覽，決定直立或45度擺放、底板附著及支撐。

支撐應能取出，尤其要確認2mm出風縫與彎道不會被不可移除的內部支撐封住。45度擺放僅提供另一種切片方向，不保證免支撐。列印後檢查並清除線絲、碎屑與支撐，確認流道與出風縫打開。

## 幾何檢查與性能範圍

- 四個儲存的Blender檔均重開核對，除了在01新檔替換原兩個大罩，其餘原物件逐項雜湊相同；原始檔雜湊不變。
- 每個列印件均為一個連通材料實體，沒有非流形邊；STL獨立重讀後，沒有零面積三角面或不封閉的座標邊。
- 左右接頭三條完整中心路徑均無阻擋；小罩完整中心路徑無阻擋，出風縫59處取樣約2mm。
- 六個小罩共用同一網格，以剛體旋轉定位；每段有效弧長約193.6mm，段間暫留6mm。中央仍保留50mm不出風範圍；模組接縫處氣流均勻度尚未驗證。
- 分流接頭及六支導管未穿過原外殼，小罩面板只在原開口上緣接觸。
- 沒有做CFD、風速或壓損實測；原R28mm彎道及約51.43mm收縮噴嘴是沿用的候選設計，不是已證明的最佳值。

完整紀錄：`模型與列印檢查.json`、`STL_重讀檢查.json`。預覽PNG由實際交付的模型渲染。
'''
(HERE/'使用與列印說明.md').write_text(text,encoding='utf-8')
with zipfile.ZipFile(HERE/'STL_列印檔.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted((HERE/'STL_毫米').glob('*.stl')):z.write(p,p.name)
    z.write(HERE/'使用與列印說明.md','使用與列印說明.md')
full=HERE.parent/'三路分流_四個Blender與列印檔.zip'
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    selected=[Path(p) for p in r['blend_files']]+list((HERE/'STL_毫米').glob('*.stl'))+list(HERE.glob('*.png'))
    selected += [HERE/'使用與列印說明.md',HERE/'模型與列印檢查.json',HERE/'STL_重讀檢查.json']
    for p in selected:z.write(p,str(Path('三路分流_正式模型')/p.relative_to(HERE)))
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
print('PACKAGED',full,full.stat().st_size,'bytes')
