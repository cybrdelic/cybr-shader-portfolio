"""Denoise one-bounce irradiance without crossing mesh normal/material seams."""
from pathlib import Path
import numpy as np,struct,gzip,json,hashlib
R=Path(__file__).resolve().parent.parent
raw=(R/'geometry/mesh.bin').read_bytes();nv,ni,stride=struct.unpack_from('<III',raw,4)
dt=np.dtype([('p','<f4',3),('n','<i2',3),('m','u1',4),('pad','u1',2),('uv','<i2',2)])
v=np.frombuffer(raw,dt,nv,16);f=np.frombuffer(raw,'<u4',ni,16+nv*stride).reshape(-1,3)
x=np.fromfile(R/'studio/irradiance.f32','<f4').reshape(nv,3).astype(float)
assert np.isfinite(x).all() and x.min()>=0
edges=np.r_[f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]];a,b=edges.T;n=v['n']/32767.
valid=((n[a]*n[b]).sum(1)>.92)&(v['m'][a,0]==v['m'][b,0]);a,b=a[valid],b[valid]
deg=np.bincount(a,minlength=nv)+np.bincount(b,minlength=nv)
for _ in range(4):
    sums=np.stack([np.bincount(a,weights=x[b,c],minlength=nv)+np.bincount(b,weights=x[a,c],minlength=nv) for c in range(3)],1)
    x=np.where(deg[:,None]>0,.4*x+.6*sums/np.maximum(deg[:,None],1),x)
raw=x.astype('<f2').tobytes();c=gzip.compress(raw,mtime=0)
(R/'studio/irradiance.bin.gz').write_bytes(c)
info={'vertices':int(nv),'channels':3,'type':'FLOAT16','bytes':len(raw),'compressedBytes':len(c),'min':float(x.min()),'max':float(x.max()),'mean':x.mean(0).tolist(),'geometrySHA256':hashlib.sha256((R/'geometry/mesh.bin').read_bytes()).hexdigest(),'description':'80 cosine-weighted rays per vertex, one explicit colored surface bounce; terminal surface radiance uses precomputed direct-light visibility and ambient approximation. Static rest-pose cache. Four normal-aware smoothing iterations. Not an unbiased full path-tracing solution.'}
(R/'studio/irradiance.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
