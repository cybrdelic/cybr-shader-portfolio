"""Deterministic surface maps for the rebuilt assets.
Not photographed/scanned. Changes at grain / plate / vein scale are authored
here once rather than evaluated as layers of noise at every screen pixel.
RGBA: linear RGB + roughness. Normal RGB + occlusion A.
"""
from pathlib import Path
import numpy as np,json,gzip
from scipy.ndimage import gaussian_filter,zoom
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parent.parent;N=1024
gen=np.random.default_rng(220026)
C=np.frombuffer(gzip.decompress((R/'materials/color.rgba.gz').read_bytes()),np.uint8).reshape(8,N,N,4).copy()
T=np.frombuffer(gzip.decompress((R/'materials/normal.rgba.gz').read_bytes()),np.uint8).reshape(8,N,N,4).copy()
y,x=np.mgrid[:N,:N].astype(float)/N

def noise(cells,seed):
    rng=np.random.default_rng(seed);a=rng.normal(size=(cells,cells));a=zoom(a,N/cells,order=3,mode='wrap')[:N,:N]
    a=(a-a.mean())/(a.std()+1e-8);return a

def store(layer,color,rough,height,strength=1.,ao=None):
    C[layer,:,:,:3]=np.rint(np.clip(color,0,1)*255).astype('u1')
    C[layer,:,:,3]=np.rint(np.clip(rough,0,1)*255).astype('u1')
    dy,dx=np.gradient(height);n=np.stack([-dx*strength,-dy*strength,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    T[layer,:,:,:3]=np.rint((n*.5+.5)*255).astype('u1')
    T[layer,:,:,3]=np.rint(np.clip(np.ones((N,N)) if ao is None else ao,0,1)*255).astype('u1')

# Brushed/turned metal: no aggressive pitting in the normal channel.
stripes=gaussian_filter(gen.normal(0,1,(N,N)),[.45,48],mode='wrap');stripes/=stripes.std()
handled=noise(6,14);height=stripes*.24+gen.normal(0,.02,(N,N))
store(0,np.ones((N,N,3))*[.68,.69,.70]*(1+.008*stripes[...,None]),.32+.025*stripes+.014*handled,height,.25)
# Porcelain coating microtexture stays below specular highlight width.
coating=noise(180,58);store(1,np.ones((N,N,3))*.78,.30+.014*coating,coating*.05,.5)
# Tangential walnut: coherent bands bend around a knot, pore streaks follow grain.
# These are authored growth coordinates, not sampled photographic texture.
w0=noise(5,110);w1=noise(16,111);w2=noise(80,112)
knx=x-.38;kny=(y-.61)*.28
knot=np.exp(-((knx/.115)**2+(kny/.18)**2))
grain=(x+.026*w0+.006*w1+.060*knot*np.sin(np.arctan2(kny,knx)))
late=np.exp(-((np.sin(grain*122.0))/.30)**2)
fibres=gaussian_filter(gen.normal(size=(N,N)),[25,.5],mode='wrap');fibres/=fibres.std()
pore=np.clip((fibres-1.65)*.65,0,1)
wc=np.array([.145,.066,.024])*(1-.34*late[...,None])
wc*=1+.11*w0[...,None]+.018*w2[...,None]
wc=wc*(1-pore[...,None]*.38)
store(2,wc,.38+.045*late+.035*pore,.20*late+.06*fibres-pore*.21,1.25,1-pore*.12)
# Marble: broad unpigmented ground with sparse forked mineral-bearing seams.
ma,mb,mc=noise(5,510),noise(16,511),noise(48,512)
coordinate=x*.8+y*.43+.055*ma+.012*mb
vein=np.exp(-(np.sin(coordinate*7.4)/.055)**2)
branch=np.exp(-(np.sin((coordinate+y*.15+.015*mc)*11.8)/.035)**2)
branch*=np.clip(mb+.6,0,1)*.55
vc=np.clip(vein+branch,0,1)
marble=np.array([.57,.55,.51])*(1+.017*ma[...,None])
marble=marble*(1-vc[...,None]*.79)+vc[...,None]*[.026,.026,.025]
store(5,marble,.26+vc*.024,mc*.012,.15)
# Slate/granite mineral field. The morphology is not a stack of arbitrary sine bands.
a,b,c,d=[noise(n,seed) for n,seed in [(5,22),(17,52),(65,62),(240,73)]]
mineral=.5+.16*a+.10*b+.06*c+.03*d
cloud=np.clip((noise(8,861)+.5)*.5,0,1)
color=np.array([.145,.145,.129])+mineral[...,None]*np.array([.105,.099,.079])
# Small cloudy quartz veins; thin dark cleavages with ochre staining.
veinpos=x*.92+y*.36+.045*a+.018*b
vein=np.exp(-(np.sin(veinpos*17.5)/.075)**2)
secondary=np.exp(-(np.sin((x*.31-y*.94+.038*a)*29.7)/.035)**2)
fracture=np.clip(vein+secondary*.50,0,1)
quartz=np.exp(-(np.sin((x-y*.15+.031*a)*13.7)/.14)**2)
color=color*(1-fracture[...,None]*.53)+quartz[...,None]*[.08,.077,.065]
rust=np.clip(noise(13,774)-.65,0,1)*cloud
color=color*(1-rust[...,None]*.32)+rust[...,None]*[.032,.013,.004]
lichen=np.clip((noise(11,782)+noise(42,73)*.35-1.0)*2.1,0,1)
color=color*(1-lichen[...,None]*.75)+lichen[...,None]*[.10,.12,.055]
height=.6*a+.31*b+.14*c+.12*d-fracture*.45+quartz*.24+lichen*.15
store(3,color,.79+.035*c-.10*lichen,height,4.,1-fracture*.24)
# Bark plates: irregular tall cells, deep longitudinal ruptures, torn short ends.
warp=.28*noise(5,43)+.12*noise(18,23)
phase=x*34+warp
long=np.exp(-(np.sin(phase*np.pi)/.24)**2)
short=np.exp(-(np.sin((y*11+.3*noise(13,79))*np.pi)/.17)**2)
short*=np.clip(noise(28,87)+.45,0,1)
ridge=np.clip((np.cos(phase*np.pi*2)*.5+.5),0,1)
height=1.1*ridge+.14*noise(90,4)+.045*noise(320,27)-long*.75-short*.43
color=np.array([.105,.078,.050])*(.85+.16*noise(12,141)[...,None])
color=color+ridge[...,None]*[.052,.041,.028]
color=color*(1-long[...,None]*.66)*(1-short[...,None]*.35)
lightedge=np.clip(gaussian_filter(long,2)-long,0,1)
color+=lightedge[...,None]*[.20,.16,.11]
store(4,color,.86+long*.1,height,3.8,1-long*.4-short*.16)
# Basalt crust: coarse angular plates and porous broken top, not uniformly shiny.
cell=gen.uniform(0,N,(310,2));distance,indices=cKDTree(cell).query(np.stack([x*N,y*N],-1).reshape(-1,2),k=2)
distance=distance.reshape(N,N,2);indices=indices[:,0].reshape(N,N)
crack=np.exp(-((distance[...,1]-distance[...,0])/2.2)**2)
height=.2*noise(12,600)+.14*noise(100,601)+.07*noise(350,602)-crack*.55
color=np.array([.018,.017,.015])*(1+.22*noise(14,42)[...,None])
color=color*(1-crack[...,None]*.6)
store(6,color,.90-.08*noise(30,80),height,3.5,1-crack*.3)
# Nine leaf variants. Veins follow a midrib and branching side veins rather than
# independent random speckle. No alpha-blended foliage clouds are needed.
U=np.mod(x*3,1);V=np.mod(y*3,1);ix=np.minimum((x*3).astype(int),2);iy=np.minimum((y*3).astype(int),2);variant=ix+3*iy
mid=V-.5
rib=np.exp(-(mid/.009)**2)
branch=(U*8.5-abs(mid)*4.5+.15*np.sin(abs(mid)*7+variant))
veins=np.exp(-(np.sin(branch*np.pi)/.12)**2)*np.exp(-abs(mid)*1.5)
tertiary=np.exp(-(np.sin((V*26+U*8+variant*.37)*np.pi)/.15)**2)*.16
blotch=.13*np.sin(U*15+variant)*np.sin(V*13-variant)+.075*noise(85,638)
base=np.stack([.025+.0028*variant,.078+.008*variant,.010+.0016*variant],-1)
color=base*(.90+blotch[...,None])
color+=rib[...,None]*[.025,.040,.007]+veins[...,None]*[.010,.014,.003]
color+=tertiary[...,None]*[.007,.009,.002]
edge=np.clip((abs(mid)-.39)/.11,0,1)
# Sparse older tips with dry ochre edges, not identical green cutouts.
old=(variant==2)|(variant==7);wear=edge*old*.5
color=color*(1-wear[...,None])+wear[...,None]*[.074,.052,.018]
height=rib*.42+veins*.14+tertiary*.05+noise(190,82)*.025
store(7,color,.48+.05*edge+blotch*.1,height,1.2)
for name,arr in [('color',C),('normal',T)]:(R/f'materials/{name}.rgba.gz').write_bytes(gzip.compress(arr.tobytes(),compresslevel=7,mtime=0))
info=json.loads((R/'materials/maps.json').read_text());info['names']=['directional-metal','enamel-microfinish','growth-coordinate-walnut','mineral-fracture-stone','fissured-bark','sparse-seam-marble','porous-basalt','nine-veined-leaves'];info['source']='Authored deterministic grain, fracture, bark-plate and leaf-venation maps. Not photographed or scanned.';(R/'materials/maps.json').write_text(json.dumps(info,indent=2))
print('Rebuilt surface maps; texture-array dimensions and layer count unchanged.',flush=True)
