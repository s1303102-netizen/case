from pathlib import Path
from collections import Counter
import struct,json,math,hashlib
HERE=Path(__file__).resolve().parent
result=[]
for path in sorted((HERE/'STL_毫米').glob('*.stl')):
    blob=path.read_bytes();n=struct.unpack_from('<I',blob,80)[0];assert len(blob)==84+50*n
    vertices={};coords=[];edges=Counter();collapsed=0;volume=0
    low=[math.inf]*3;high=[-math.inf]*3
    for j in range(n):
        data=struct.unpack_from('<12fH',blob,84+50*j)
        xyz=[tuple(data[k:k+3]) for k in [3,6,9]];ids=[]
        for p in xyz:
            if p not in vertices:vertices[p]=len(vertices);coords.append(p)
            ids.append(vertices[p])
            for a in range(3):low[a]=min(low[a],p[a]);high[a]=max(high[a],p[a])
        a,b,c=xyz
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if len(set(ids))<3 or sum(x*x for x in cross)<1e-18:collapsed+=1
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for k in range(3):edges[tuple(sorted((ids[k],ids[(k+1)%3])))]+=1
    bad=sum(v!=2 for v in edges.values());size=[high[i]-low[i] for i in range(3)]
    row={'file':path.name,'triangles':n,'vertices':len(vertices),'nonmanifold_coordinate_edges':bad,
         'collapsed_triangles':collapsed,'signed_volume_mm3':volume,'bounds_mm':[low,high],
         'size_mm':size,'sha256':hashlib.sha256(blob).hexdigest()}
    print(json.dumps(row,ensure_ascii=False),flush=True)
    assert bad==0 and collapsed==0 and volume>1000 and max(size)<300 and abs(low[2])<.001
    result.append(row)
(HERE/'STL_重讀檢查.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('ALL_BINARY_STL_FILES_CHECKED')
