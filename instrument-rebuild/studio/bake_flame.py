"""Offline compact buoyant-flow flame asset.
Semi-Lagrangian advection, spectral incompressible projection, three injection
sites and dissipating heat/fuel. Periodic pressure boundaries with sponge layers
are an artistic approximation, not a validated combustion simulation. The
runtime samples RG8 volumes; it never solves the fluid or allocates histories.
"""
from pathlib import Path
import numpy as np, gzip,json
from scipy.ndimage import map_coordinates,gaussian_filter
from scipy.fft import rfftn,irfftn
R=Path(__file__).resolve().parent.parent
shape=(32,64,32);dt=.055;gen=np.random.default_rng(76123)
z,y,x=np.mgrid[:shape[0],:shape[1],:shape[2]].astype('f4');coords=np.stack([z,y,x])
v=np.zeros((3,*shape),'f4');temp=np.zeros(shape,'f4');fuel=temp.copy()
k=np.meshgrid(np.fft.fftfreq(32)*2*np.pi,np.fft.fftfreq(64)*2*np.pi,np.fft.rfftfreq(32)*2*np.pi,indexing='ij');k=np.array(k,'f4');k2=(k*k).sum(0);k2[0,0,0]=1
sponge=np.clip((y-1)/3,0,1)*np.clip((62-y)/8,0,1)*np.clip(np.minimum(x,31-x)/5,0,1)*np.clip(np.minimum(z,31-z)/5,0,1)
frames=[]
for it in range(326):
    t=it*dt
    # Spatially varying small sources and eddies keep the columns from looking
    # like one stretched noise sphere.
    source=np.zeros(shape,'f4')
    for j,(cx,cz,r) in enumerate([(10,12,2.4),(22,16,2.1),(15,24,1.9)]):
        cx+=.8*np.sin(t*2.1+j*3);cz+=.6*np.sin(t*1.5+j*4)
        source+=np.exp(-((x-cx)**2+(z-cz)**2)/(2*r*r))*np.exp(-((y-4)/1.6)**2)*(0.8+.17*np.sin(t*4.1+j*3))
    source=np.minimum(source,1.)
    fuel=np.maximum(fuel,source*.88);temp=np.maximum(temp,source*.95)
    # Buoyant upward flow and small periodic shear at the injector.
    v[1]+=dt*(20*temp-2*fuel)
    v[0]+=dt*4.0*np.sin(y*.30+t*2.4)*temp
    v[2]+=dt*4.0*np.cos(y*.27-t*1.8)*temp
    # Vorticity confinement gives thin folding tongues at this low grid density.
    curl=np.stack([np.gradient(v[2],axis=1)-np.gradient(v[1],axis=2),np.gradient(v[0],axis=2)-np.gradient(v[2],axis=0),np.gradient(v[1],axis=0)-np.gradient(v[0],axis=1)])
    mag=np.sqrt((curl*curl).sum(0));grad=np.stack(np.gradient(mag));grad/=np.maximum(np.sqrt((grad*grad).sum(0)),1e-6)
    force=np.cross(grad,curl,axisa=0,axisb=0,axisc=0);v+=dt*1.65*force
    back=coords-v*dt
    for axis in range(3):back[axis]=np.clip(back[axis],0,shape[axis]-1.001)
    v=np.stack([map_coordinates(c,back,order=1,mode='nearest') for c in v])*.994
    vf=rfftn(v,axes=(1,2,3),workers=2);dot=(vf*k).sum(0);vf-=k*dot/ k2
    v=irfftn(vf,s=shape,axes=(1,2,3),workers=2).astype('f4')*sponge
    temp=map_coordinates(temp,back,order=1,mode='nearest')*.989*sponge
    fuel=map_coordinates(fuel,back,order=1,mode='nearest')*.993*sponge
    burn=fuel*np.clip((temp-.15)*1.4,0,1)*dt*.60
    fuel=np.maximum(fuel-burn,0);temp=np.clip(temp+burn*1.4-dt*.020,0,1.1)
    # Resolve only the luminous region; no opaque billboard or screen-space image.
    density=np.clip(fuel*2.5,0,1)*np.clip((temp-.08)*3.0,0,1)
    if it>=182 and (it-182)%3==0:
        f=np.stack([np.clip(temp,0,1),density],-1)
        atlas=np.zeros((256,256,2),'u1')
        for zz in range(32):atlas[(zz//8)*64:(zz//8+1)*64,(zz%8)*32:(zz%8+1)*32]=np.rint(f[zz]*255).astype('u1')
        frames.append(atlas)
    if it%50==0:print('flow step',it,'heat',float(temp.max()),'velocity',float(v[1].max()),flush=True)
frames=np.array(frames);assert len(frames)==48
# A crossfade over the final six volumes supplies a seamless presentation loop;
# it is recorded as editing, not claimed to be a naturally periodic flow.
for i in range(6):
    f=(i+1)/7;frames[-6+i]=np.rint(frames[-6+i]*(1-f)+frames[i]*f).astype('u1')
payload=frames.tobytes();(R/'materials/flame.rg8.gz').write_bytes(gzip.compress(payload,7,mtime=0))
info={'width':256,'height':256,'frames':48,'grid':[32,64,32],'format':'RG8','bytes':len(payload),'seconds':7.92,'simulationSteps':326,'timeStep':dt,'source':'Offline buoyancy/advection/pressure-projection flow, heat and fuel; simplified combustion. Six-volume crossfade closes the presentation loop. Not a validated fire solver.'}
(R/'materials/flame.json').write_text(json.dumps(info,indent=2));print('Flame complete',info,flush=True)
