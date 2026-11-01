"""Check actual exported binary STL topology, envelopes and build-plate Z."""
from pathlib import Path
from collections import Counter
import struct,json,math,hashlib
HERE=Path(__file__).resolve().parent
checks=[]
for f in sorted(HERE.glob('*.stl')):
    data=f.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    assert len(data)==84+n*50
    edges=Counter();degenerate=0;minimum=[math.inf]*3;maximum=[-math.inf]*3
    for i in range(n):
        coords=struct.unpack_from('<12fH',data,84+50*i)
        a,b,c=[tuple(coords[j:j+3]) for j in [3,6,9]]
        for v in (a,b,c):
            for k in range(3):minimum[k]=min(minimum[k],v[k]);maximum[k]=max(maximum[k],v[k])
        if len({a,b,c})<3:degenerate+=1
        for u,v in [(a,b),(b,c),(c,a)]:edges[tuple(sorted((u,v)))]+=1
    checks.append({'file':f.name,'triangles':n,'nonmanifold_coordinate_edges':sum(v!=2 for v in edges.values()),
                   'collapsed_triangles':degenerate,'size_mm':[round(b-a,4) for a,b in zip(minimum,maximum)],
                   'lowest_Z_mm':minimum[2],'sha256':hashlib.sha256(data).hexdigest()})
assert len(checks)==11
assert all(r['nonmanifold_coordinate_edges']==0 and r['collapsed_triangles']==0 and max(r['size_mm'])<300 and abs(r['lowest_Z_mm'])<.001 for r in checks)
(HERE/'STL檔案重讀檢查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_11_STL_FILES_PASS',flush=True)
