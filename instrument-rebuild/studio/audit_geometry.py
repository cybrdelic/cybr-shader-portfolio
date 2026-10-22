"""Audit source-derived geometry and bake provenance before distributing HTML."""
from pathlib import Path
import struct,json,hashlib,gzip,numpy as np
R=Path(__file__).resolve().parent.parent
raw_path=R/'geometry/mesh.bin'
raw=raw_path.read_bytes() if raw_path.exists() else gzip.decompress((R/'geometry/mesh.bin.gz').read_bytes());magic,nv,ni,stride=struct.unpack('<4sIII',raw[:16])
dt=np.dtype([('p','<f4',(3,)),('n','<i2',(3,)),('m','u1',(4,)),('pad','u1',(2,)),('uv','<i2',(2,))])
v=np.frombuffer(raw,dt,nv,16);f=np.frombuffer(raw,'<u4',ni,16+nv*stride).reshape(-1,3)
meta=json.loads((R/'geometry/packed.json').read_text());checks=[]
def ck(n,p,**extra):checks.append(dict(name=n,pass_=bool(p),**extra))
ck('Geometry payload header and index range',magic==b'CYB2' and stride==28 and int(f.max())<nv)
ck('No nonfinite vertex coordinates',np.isfinite(v['p']).all())
norm=np.linalg.norm(v['n'].astype(float)/32767,axis=1);ck('Quantized normals remain normalized',norm.min()>.9998 and norm.max()<1.0002,minimum=float(norm.min()),maximum=float(norm.max()))
sha=hashlib.sha256(raw).hexdigest();ck('Geometry hash matches metadata',sha==meta['sha256'])
for path in ['studio/irradiance.json','studio/probes.json','studio/optical-probes.json']:
 m=json.loads((R/path).read_text());key='geometrySHA256';ck(path+' uses final geometry',m.get(key)==sha,recorded=m.get(key),actual=sha)
tri=v[f];top=(tri['m'][:,:,0]==22).all(1)&(tri['p'][:,:,1]>.94).all(1)
x=np.cross(tri['p'][top,1]-tri['p'][top,0],tri['p'][top,2]-tri['p'][top,0]);ck('Every exposed crust top faces outward',int((x[:,1]<0).sum())==0,topTriangles=int(top.sum()),inwardTriangles=int((x[:,1]<0).sum()))
g=next(g for g in meta['groups'] if g['name']=='geometry-rotor-airfoils');ff=f.ravel()[g['indexStart']:g['indexStart']+g['indexCount']].reshape(-1,3);vv=v['p'][ff].astype(float);vv-=vv.mean((0,1));vol=np.einsum('ij,ij->i',vv[:,0],np.cross(vv[:,1],vv[:,2])).sum()/6
ck('Closed airfoil group has outward signed volume',vol>0,signedVolume=float(vol))
report={'build':'cybr-instrument-rebuild-2026-10-22','geometrySHA256':sha,'vertices':nv,'triangles':ni//3,'checks':checks,'passed':sum(c['pass_'] for c in checks),'total':len(checks),'scope':'Geometry integrity and bake provenance, not a manufacturing or photorealism certification.'}
(R/'verification/geometry-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not all(c['pass_'] for c in checks):raise SystemExit(1)
