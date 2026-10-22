"""Deterministic multiscale PBR maps, generated from surface processes.
Each layer is RGBA albedo/roughness plus RGBA tangent normal/AO. This is not a
photographic scan. Textures are evaluated once offline, not every pixel/frame.
"""
from pathlib import Path
import numpy as np, json, gzip
from scipy.ndimage import gaussian_filter, map_coordinates, fourier_gaussian
from scipy.fft import rfft2, irfft2, fft2, ifft2
R=Path(__file__).resolve().parent.parent; S=1024
rng=np.random.default_rng(22012026)
y,x=np.mgrid[0:S,0:S].astype(np.float32)/S

def noise(scale, stretch=(1,1)):
    z=rng.standard_normal((S,S)).astype(np.float32)
    sigma=(max(.35,S/scale*stretch[1]),max(.35,S/scale*stretch[0]))
    z=ifft2(fourier_gaussian(fft2(z),sigma)).real
    return z/max(z.std(),1e-7)
def fbm(scales=(3,7,18,49,135,360), amp=.5):
    z=np.zeros((S,S),np.float32);w=1
    for s in scales:z+=noise(s)*w;w*=amp
    return z

def normals(h, strength):
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.5*strength
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.5*strength
    n=np.stack([-dx,dy,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n*.5+.5

def rgb(c):return np.stack([c,c,c],-1) if c.ndim==2 else c
maps=[];names=[]
def emit(name,base,rough,h,strength,ao=None):
    base=rgb(base) if isinstance(base,np.ndarray) else np.broadcast_to(base,(S,S,3)).copy()
    rgba=np.dstack([np.clip(base,0,1),np.clip(np.broadcast_to(rough,(S,S)),.02,1)])
    nm=np.dstack([normals(h,strength),np.ones((S,S)) if ao is None else np.clip(ao,0,1)])
    maps.append((np.round(rgba*255).astype('u1'),np.round(nm*255).astype('u1')));names.append(name);print('surface ready',name,flush=True)

# Turned/satin metal: directional rolled marks, light irregularity, sparse scuffs.
broad=fbm((2,5,12,35));fine=noise(400,stretch=(.3,7.));grain=noise(720)
scratches=np.zeros((S,S),np.float32)
for j in range(110):
    cx,cy=rng.uniform(0,1,2);length=rng.uniform(.02,.24);width=rng.uniform(.00025,.0013)
    d=np.abs(((x-cx+.5)%1)-.5);v=((y-cy+.5)%1)-.5
    scratches+=np.exp(-np.square(d/width))*np.exp(-np.power(v/length,6))*.06
h=fine*.09+grain*.013-scratches
emit('satin-metal', np.clip(.68+broad*.014,0,1),np.clip(.26+fine*.024+broad*.014+scratches*.5,.16,.43),h,1.6)
# Powder-coated housing, micron-scale orange peel rather than gross pebbles.
orange=noise(145)*.024+noise(500)*.008
smudge=np.clip(noise(6)+.3,0,1)*np.clip(noise(15),0,1)
emit('porcelain-enamel', np.clip(.78+noise(9)*.007+noise(330)*.002,0,1),.34+smudge*.025,orange,.65)
# Walnut: curved growth rings with pores, fibers and branch knots in a coherent field.
warp=noise(4,stretch=(1,3))*.014+noise(18,stretch=(1,7))*.005
q=x+warp+.035*np.sin(y*6.283)
for kx,ky,amount in [(.28,.34,.032),(.74,.78,.018)]:
    dx=((x-kx+.5)%1)-.5;dy=((y-ky+.5)%1)-.5
    q+=amount*np.arctan2(dx,dy*1.6+1e-4)*np.exp(-(dx*dx+dy*dy)*19)
rings=.5+.5*np.sin(q*2*np.pi*67+noise(14,stretch=(1,9))*.45)
late=np.power(rings,12)
fiber=noise(530,stretch=(.7,32))
pores=np.maximum(noise(320,stretch=(.45,10))-1.50,0)**1.5
body=noise(8,stretch=(1,4))*.09
base=np.stack([.215+body*.5,.083+body*.22,.028+body*.10],-1)
base*=np.clip(.98-late*.28+fiber*.045-pores*.14,.18,1.3)[...,None]
emit('cut-walnut',base,.31+late*.07+pores*.1,late*.06-fiber*.012-pores*.06,2.3,np.clip(1-pores*.07,.75,1))
# Dark stratified rock: variable minerals, granular matrix and narrow discontinuities.
warped=y+noise(8)*.009+noise(24)*.002+x*.10
bands=.5+.5*np.sin(warped*2*np.pi*21)
mineral=fbm((3,9,31,96,220,650),.65)
quartz=np.clip(noise(140)-1.5,0,1)*.045
cleavage=np.power(.5+.5*np.cos(warped*2*np.pi*58+noise(12)*.6),16)
base=np.stack([.155+mineral*.023,.166+mineral*.025,.172+mineral*.027],-1)
base*= (.80+bands*.24-cleavage*.36)[...,None];base+=quartz[...,None]
h=mineral*.16+bands*.11-cleavage*.32+noise(900)*.014
emit('layered-stone',base,np.clip(.77+noise(30)*.05-quartz*.35,.42,.96),h,2.3,np.clip(1-cleavage*.25,.6,1))
# Bark: thick longitudinal ridges, plate fissures, lichen islands.
q=x+noise(10,stretch=(1,3))*.012
ridge=np.abs(np.sin(q*2*np.pi*17+noise(25,stretch=(1,7))*.5))
furrow=np.power(1-ridge,7)
plate=np.power(.5+.5*np.sin(y*2*np.pi*34+noise(12)*1.3),20)
lichen=np.clip(noise(10)-1.15,0,1)*np.clip(noise(70)+.3,0,1)
coherent=noise(28)
base=np.stack([.112+coherent*.017,.096+coherent*.014,.073+coherent*.010],-1)
base*=np.clip(1-furrow*.65-plate*.14,.2,1)[...,None];base=base*(1-lichen[...,None]*.6)+np.array([.19,.21,.13])*lichen[...,None]*.6
h=ridge*.16-furrow*.23-plate*.06+noise(280)*.014
emit('old-bark',base,.91,h,2.6,1-furrow*.38)
# Calacatta-like stone: warped geological veins, translucent mineral inclusion.
q=x*.72+y*.34+noise(4)*.055+noise(14)*.011
vein=np.power(np.maximum(0,1-np.abs(np.sin(q*2*np.pi*4))),19)
hair=np.power(np.maximum(0,1-np.abs(np.sin(q*2*np.pi*23+noise(35)*.5))),36)
cloud=noise(7)*.025
base=np.stack([.72+cloud,.715+cloud,.67+cloud],-1)
base=base*(1-vein[...,None]*.55-hair[...,None]*.15)
emit('mineral-marble',base,.23+vein*.04,noise(550)*.004,.8)
# Refractory lava crust: fine pumice pores over a ridged cooled basalt sheet.
pore=np.maximum(noise(90)-.9,0);h=fbm((7,24,77,200,600),.6)*.13-pore*.18
c=np.clip(.024+noise(9)*.004+noise(190)*.004,.008,.06)
emit('cooled-basalt',np.stack([c,c*.95,c*.91],-1),.86,h,4.1,1-np.clip(pore*.16,0,.4))
# Water-free floor: finely textured dark photographic sweep.
h=noise(600)*.012;c=.024+noise(8)*.0008+noise(250)*.00025
emit('studio-sweep',np.stack([c*1.00,c*.98,c*.95],-1),.80,h,.7)

# Stored two 2D arrays, deterministic gzip, no runtime image decoding or network.
for k,idx in [('color',0),('normal',1)]:
    payload=b''.join(a[idx].tobytes() for a in maps)
    (R/'materials'/f'{k}.rgba.gz').write_bytes(gzip.compress(payload,6,mtime=0))
info={'size':S,'layers':len(maps),'names':names,'format':'RGBA8','colorSpace':'linear albedo; roughness in alpha','normalEncoding':'tangent XYZ mapped 0..1; AO in alpha','source':'Deterministic procedural surface processes; not photographed or scanned.'}
(R/'materials/maps.json').write_text(json.dumps(info,indent=2));print(json.dumps(info),flush=True)
