"""Publish the user-authorized .blend change after verified backup and hashes."""
from pathlib import Path
import json,hashlib,shutil,os

HERE=Path(__file__).resolve().parent
ROOT=Path('/Users/alissachang/Desktop/大專')
TARGET=ROOT/'完整模型.blend'
DEST=ROOT/'夾傘機構/正式整合_前方中空9mm_20261030'
REPORT=HERE/'正式實作_核對紀錄.json'
report=json.loads(REPORT.read_text())
stage=Path(report['staged_file'])
backup=Path(report['backup_file'])
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert report['staged_reopened_and_verified'] is True
assert sha(TARGET)==report['source_sha256_before'],'Source was saved externally; do not replace.'
assert sha(backup)==report['source_sha256_before']
assert sha(stage)==report['staged_sha256']
assert not DEST.exists(),'Delivery folder already exists; do not overwrite.'
DEST.mkdir()
files=[stage,backup,REPORT,HERE/'正式實作說明.md',HERE/'implement_hollow_and_clamps.py',
       HERE/'render_implemented_model.py',HERE/'渲染說明.json',HERE/'publish_verified.py',
       HERE/'01_正式整合_整體外觀.png',HERE/'02_正式整合_雙組共軸近照.png',
       HERE/'03_正式整合_全中空與9mm底殼剖視.png']
for file in files:
    assert file.is_file(),file
    output=DEST/file.name
    shutil.copy2(file,output)
    assert sha(output)==sha(file),file.name
assert sha(DEST/backup.name)==report['source_sha256_before']
assert sha(TARGET)==report['source_sha256_before'],'Source changed during copying; original retained.'
pending=ROOT/'.完整模型_雙組中空9mm_核對後待換.blend'
assert not pending.exists(),'Pending file already exists; do not overwrite it.'
shutil.copy2(stage,pending)
assert sha(pending)==report['staged_sha256']
assert sha(TARGET)==report['source_sha256_before'],'Source changed before commit; original retained.'
os.replace(pending,TARGET)
assert sha(TARGET)==report['staged_sha256']
report['original_file_not_yet_overwritten']=False
report['published_to_original']=True
report['published_file']=str(TARGET)
report['published_sha256']=sha(TARGET)
report['backup_file']=str(DEST/backup.name)
report['staged_file']=str(DEST/stage.name)
report['published_backup_verified']=True
(DEST/REPORT.name).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'updated_model':str(TARGET),'delivered_model_copy':str(DEST/stage.name),
    'verified_original_backup':str(DEST/backup.name),'delivery_folder':str(DEST),
    'target_sha256':sha(TARGET),'backup_verified':True,'published':True},ensure_ascii=False))
