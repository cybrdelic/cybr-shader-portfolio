from pathlib import Path
import json,hashlib,gzip,struct,numpy as np
R=Path(__file__).resolve().parent.parent
p=bytearray((R/'geometry/mesh-lit.bin').read_bytes());nv,ni,stride=struct.unpack_from('<III',p,4)
dt=np.dtype([('p','<f4',3),('n','<i2',3),('m','u1',4),('pad','u1',2),('uv','<i2',2)])
v=np.frombuffer(p,dt,nv,16);f=np.frombuffer(p,'<u4',ni,16+nv*stride).reshape(-1,3)
# Smooth estimator noise over connected same-material surfaces, never across
# separate parts or hard normal boundaries (those vertices are not shared).
ao=np.c_[v['m'][:,1].astype(float),v['pad'].astype(float)];normal=v['n'].astype(float)/32767
edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);a,b=edges.T
mask=((normal[a]*normal[b]).sum(axis=1)>.92)&(v['m'][a,0]==v['m'][b,0]);a,b=a[mask],b[mask]
deg=np.bincount(a,minlength=nv)+np.bincount(b,minlength=nv)
for _ in range(3):
 accum=np.stack([np.bincount(a,weights=ao[b,c],minlength=nv)+np.bincount(b,weights=ao[a,c],minlength=nv) for c in range(3)],1)
 avg=accum/np.maximum(deg[:,None],1);ao=np.where(deg[:,None]>0,ao*.35+avg*.65,ao)
v['m'][:,1]=np.round(np.clip(ao[:,0],0,255)).astype('u1');v['pad']=np.round(np.clip(ao[:,1:],0,255)).astype('u1');data=bytes(p);(R/'geometry/mesh.bin').write_bytes(data)
c=gzip.compress(data,compresslevel=9,mtime=0);(R/'geometry/mesh.bin.gz').write_bytes(c)
info=json.loads((R/'geometry/packed.json').read_text());info.update(sha256=hashlib.sha256(data).hexdigest(),compressedBytes=len(c),ambientOcclusion={'samples':40,'range':1.2,'decayLength':.30,'normalAwareSmoothingPasses':3,'type':'offline cosine-weighted visibility and 56/24 sample rectangular area-light visibility, static rest pose'})
(R/'geometry/packed.json').write_text(json.dumps(info,indent=2));print('mesh',info['triangles'],info['vertices'],len(c))
