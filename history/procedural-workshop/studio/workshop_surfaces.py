"""Procedural Workshop: dimensioned, deterministic surface processes.
No source photography, scans, scraped maps, or generative image model.
RGB values are linear reflectance; alpha is perceptual roughness. Normal maps
encode geometric slopes of authored height fields. Dimensions below are artistic
physical-scale approximations (one scene unit ~100 mm), not measured materials.
"""
from pathlib import Path
import gzip,json
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parent.parent;N=1024
C=np.empty((8,N,N,4),np.uint8);T=np.empty_like(C)
y,x=np.mgrid[:N,:N].astype(np.float64)/N

def field(cells,seed):
    a=np.random.default_rng(seed).normal(size=(cells,cells))
    out=map_coordinates(a,[y*cells,x*cells],order=3,mode='grid-wrap')
    return (out-out.mean())/(out.std()+1e-8)

def store(i,color,rough,height,ao=1):
    color=np.broadcast_to(color,(N,N,3));rough=np.broadcast_to(rough,(N,N))
    C[i,...,:3]=np.rint(np.clip(color,0,1)*255).astype('u1');C[i,...,3]=np.rint(np.clip(rough,.05,.98)*255).astype('u1')
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*N*.5
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*N*.5
    normal=np.stack([-dx,-dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    T[i,...,:3]=np.rint((normal*.5+.5)*255).astype('u1');T[i,...,3]=np.rint(np.clip(np.broadcast_to(ao,(N,N)),0,1)*255).astype('u1')

# Fine abrasive tracks: correlated along tool travel, with long wave handled areas.
rng=np.random.default_rng(17219)
tracks=gaussian_filter(rng.normal(size=(N,N)),(.7,52),mode='wrap');tracks/=tracks.std()
handling=field(5,731)
store(0,np.array([.68,.69,.70])*(1+tracks[...,None]*.003),.32+.018*tracks+.015*handling,tracks*.000004)
# Industrial powder/enamel finish: subtle orange peel, no noisy glossy plastic.
peel=field(85,701);fine=field(256,702)
store(1,np.array([.78,.78,.78])*(1+.002*peel[...,None]),.30+.009*peel,peel*.000006+fine*.000001)
# Walnut: growth early/latewood and directional open pores, not a sine texture.
bend=field(5,803)*.025+field(11,804)*.006
phase=(x+bend+0.012*np.sin(y*6.283))*31
ring=.5+.5*np.sin(phase*6.283)
late=np.clip((ring-.64)/.36,0,1)**2
fib=gaussian_filter(rng.normal(size=(N,N)),(38,.65),mode='wrap');fib/=fib.std()
pores=np.clip(fib-1.2,0,2)*.32
body=field(7,806)
wood=np.array([.125,.054,.019])*(1+body[...,None]*.12-late[...,None]*.20-pores[...,None]*.35)
store(2,wood,.38+late*.045+pores*.12,late*.000025-pores*.00010+field(180,807)*.000003,1-pores*.16)
# Schist: mica/grain clusters, quartz lenses, and iron stains tied to fractures.
a,b,c,d=[field(n,s) for n,s in [(5,812),(21,813),(93,814),(330,815)]]
lam=y*.83+x*.56+a*.014+b*.004
seam=np.exp(-(np.sin(lam*23.4)/.065)**2)
quartz=np.clip((field(13,817)+.45*field(48,818)-1.05)*.7,0,1)
coarse=np.clip(field(38,819)*.25+.5,0,1)
rock=np.array([.103,.113,.122])*(1+.12*a[...,None]+.10*b[...,None]+.085*c[...,None]+.045*d[...,None])
rock=rock*(1-quartz[...,None]*.55)+quartz[...,None]*[.36,.35,.32]
rust=seam*np.clip(field(11,820)+.5,0,1)*.55
rock=rock*(1-rust[...,None]*.55)+rust[...,None]*[.056,.025,.009]
rock*=1-seam[...,None]*.28
h=a*.00012+b*.00014+c*.00006+d*.000025-seam*.00030+quartz*.00012
store(3,rock,.77+.045*c-.20*quartz,h,1-seam*.13)
# Old bark: elongated cellular plates with irregular axial cleavage.
seed=np.random.default_rng(831);sites=seed.uniform(0,1,(390,2));sites[:,0]*=1.8
points=np.stack([x*1.8,y*.55],-1).reshape(-1,2)
all_sites=np.concatenate([sites+[i*1.8,j] for i in [-1,0,1] for j in [-1,0,1]])
dist,idx=cKDTree(all_sites).query(points,k=2);gap=(dist[:,1]-dist[:,0]).reshape(N,N)
furrow=np.exp(-(gap/.0030)**2)
wrinkles=field(95,832);ridge=field(20,833)
bark=np.array([.125,.108,.082])*(1+.13*ridge[...,None]+.07*wrinkles[...,None])
bark*=1-furrow[...,None]*.60
lichen=np.clip((field(33,834)-1.25)*.5,0,.5)
bark=bark*(1-lichen[...,None])+lichen[...,None]*[.17,.18,.13]
store(4,bark,.89+.06*furrow,-furrow*.00085+ridge*.00016+wrinkles*.000035,1-furrow*.24)
# Marble panel: sparse branching calcite ribbons warped by low-frequency flow.
u=x*.69+y*.47+field(5,845)*.09+field(17,846)*.012
vein=np.exp(-(np.sin(u*11.7)/.075)**2)
hair=np.exp(-(np.sin((u+.015*field(33,847))*47)/.025)**2)*.17
marble=np.array([.68,.665,.63])*(1+field(12,848)[...,None]*.015)
marble*=1-(vein*.66+hair)[...,None]
store(5,marble,.245+vein*.05,field(130,849)*.000003+vein*.000006)
# Broken basalt: rough cooled crust, pores at multiple scales and low albedo.
pores=np.clip(field(160,854)-.6,0,2)
coarse=field(19,855);micro=field(350,856)
basalt=np.array([.022,.021,.020])*(1+coarse[...,None]*.17-pores[...,None]*.21)
store(6,basalt,.88+pores*.04,coarse*.00020-pores*.00023+micro*.000018,1-pores*.11)
# Nine related but non-identical broadleaf variants: vascular network, wax,
# restrained age discoloration, cupped silhouettes live in geometry.py.
U=x*3%1;V=y*3%1;variant=(x*3).astype(int)+3*(y*3).astype(int)
mid=V-.5;rib=np.exp(-(mid/.010)**2)
veins=np.exp(-(np.sin((U*8.3-abs(mid)*4.1+.09*np.sin(U*5+variant))*np.pi)/.105)**2)*np.exp(-abs(mid)*2.1)
blotch=field(42,863)*.07+field(130,864)*.025
leaf=np.stack([.026+.0018*variant,.078+.0055*variant,.012+.0014*variant],-1)*(1+blotch[...,None])
leaf+=rib[...,None]*[.024,.031,.008]+veins[...,None]*[.008,.012,.003]
aged=np.maximum((abs(mid)-.43)/.07,0)*((variant==2)|(variant==7))*.45
leaf=leaf*(1-aged[...,None])+aged[...,None]*[.086,.060,.019]
store(7,leaf,.43+blotch*.12+aged*.12,rib*.00008+veins*.000025+field(180,865)*.000002)
for name,arr in [('color',C),('normal',T)]:
    (R/f'materials/{name}.rgba.gz').write_bytes(gzip.compress(arr.tobytes(),7,mtime=0))
info=json.loads((R/'materials/maps.json').read_text());info['names']=['abrasive-machining','micro-enamel','growth-ring-walnut','cleavage-mica-quartz','cellular-bark','veined-marble','porous-basalt','veined-leaf-variants'];info['source']='Deterministic process-based surface fields; linear albedo, roughness, height-derived normals. No scans or photographs.'
(R/'materials/maps.json').write_text(json.dumps(info,indent=2))
print('Generated all eight procedural surface families.',flush=True)
