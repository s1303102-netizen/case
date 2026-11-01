"""Re-render the same full assembly at 3840 x 3480, without a floor.
Uses the existing procedural Blender scene, not a bitmap upscale or AI edit.
Never saves the input .blend file.
"""
from pathlib import Path
import json
import hashlib
import struct

BASE = Path('/Users/alissachang/Desktop/大專/夾傘機構/雙組夾持加入雨傘_模擬圖_20261030/render_umbrella_with_dual_clamp.py')
base_code = BASE.read_text()
setup = base_code[:base_code.index("\nrender('01_加入雨傘_整體擺放模擬.png'")]
exec(compile(setup, str(BASE), 'exec'))
floor.hide_render = True
scene.render.film_transparent = False
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = .02
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
filename = '加入雨傘_整體模擬_3840x3480_無地板.png'
render(filename, (2.1,2.85,1.90), (0,.06,.63), 2.40, 3840,3480,-.45)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
with (HERE / filename).open('rb') as stream:
    png_header = stream.read(24)
assert png_header[:8] == b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II',png_header[16:24]) == (3840,3480)
report = {'source':str(SOURCE),'source_sha256':source_hash,'source_modified':False,
    'output':str(HERE / filename),'resolution':[3840,3480],
    'render_engine':'Cycles','samples_max':64,'adaptive_noise_threshold':.02,
    'floor_visible':False,'background':'Opaque world background; no floor plane',
    'camera_and_model_placement':'Unchanged from previous full-assembly preview',
    'method':'Native 3D render, not bitmap upscaling'}
(HERE / '高解析無地板_渲染紀錄.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('HIGHRES_NO_FLOOR_COMPLETE',json.dumps(report,ensure_ascii=False),flush=True)
