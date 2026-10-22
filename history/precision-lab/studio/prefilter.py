"""Generate a procedural linear-radiance studio cubemap and GGX mip pyramid.
No photographic asset or generated image is involved. Radiance is integrated
once, offline, instead of re-evaluating artificial rectangular highlights per pixel.
"""
from pathlib import Path
import numpy as np, json, gzip, math
R=Path(__file__).resolve().parent.parent
S=256

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)

def ambient(d):
    y=np.clip(d[...,1]*.5+.5,0,1)
    return (.095+.19*y[...,None]**1.3)*np.array([.92,.98,1.06])

def env(d):
    out=ambient(d)
    # Large diffusion frame, cool fill and narrow back-rim, at photographic ratios.
    panels=[([-3.8,6.5,5.4],[.37,.255],[7.5,7.1,6.6]),
            ([5.2,3.5,-2.7],[.25,.40],[1.65,1.95,2.4]),
            ([-2.,4.,-5.],[.065,.55],[2.0,2.1,2.2])]
    for facing,size,col in panels:
        n=unit(np.array(facing,np.float32));h=unit(np.cross([0,1,0],n));v=np.cross(n,h)
        front=d@n;u=(d@h)/np.maximum(front,.001);w=(d@v)/np.maximum(front,.001)
        e=np.maximum(np.abs(u)-size[0],np.abs(w)-size[1]);a=np.clip((.025-e)/.05,0,1);a=a*a*(3-2*a)*(front>0)
        # A photographed diffusion panel is not a perfectly uniform white rectangle.
        panel=.88+.12*np.exp(-1.6*((u/size[0])**2+(w/size[1])**2))
        out+=a[...,None]*panel[...,None]*np.array(col)
    n=unit(np.array([.05,.07,1.]));card=np.clip((d@n-.75)/.20,0,1)
    out*=1-.50*card[...,None]*(1-np.clip(d[...,1:2],0,1))
    return out

def directions(n,face):
    u,v=np.meshgrid((np.arange(n)+.5)/n*2-1,(np.arange(n)+.5)/n*2-1)
    one=np.ones_like(u)
    arr=[(one,-v,-u),(-one,-v,u),(u,one,v),(u,-one,-v),(u,-v,one),(-u,-v,-one)][face]
    return unit(np.stack(arr,-1).reshape(-1,3)).astype(np.float32)

def radical(n):
    a=np.arange(n,dtype=np.uint32);a=(a<<16)|(a>>16)
    a=((a&0x55555555)<<1)|((a&0xaaaaaaaa)>>1)
    a=((a&0x33333333)<<2)|((a&0xcccccccc)>>2)
    a=((a&0x0f0f0f0f)<<4)|((a&0xf0f0f0f0)>>4)
    a=((a&0x00ff00ff)<<8)|((a&0xff00ff00)>>8)
    return a.astype(np.float64)*2.3283064365386963e-10

def prefilter(n,rough,samples=192):
    xi=(np.arange(samples)+.5)/samples;alpha=rough*rough
    ct=np.sqrt((1-radical(samples))/(1+(alpha*alpha-1)*radical(samples)))
    st=np.sqrt(1-ct*ct);phi=2*np.pi*xi
    h=np.stack([st*np.cos(phi),st*np.sin(phi),ct],-1).astype(np.float32)
    out=[]
    for start in range(0,len(n),1024):
        nn=n[start:start+1024];up=np.where((np.abs(nn[:,2])<.999)[:,None],[0,0,1],[1,0,0]);t=unit(np.cross(up,nn));b=np.cross(nn,t)
        hh=t[:,None,:]*h[None,:,0,None]+b[:,None,:]*h[None,:,1,None]+nn[:,None,:]*h[None,:,2,None]
        l=2*np.sum(nn[:,None,:]*hh,axis=-1,keepdims=True)*hh-nn[:,None,:]
        w=np.maximum(np.sum(nn[:,None,:]*l,axis=-1),0)
        val=env(l.reshape(-1,3)).reshape(len(nn),samples,3)
        out.append(np.sum(val*w[...,None],axis=1)/np.maximum(w.sum(axis=1,keepdims=True),1e-8))
    return np.concatenate(out)

chunks=[];levels=int(math.log2(S))+1;meta=[]
for level in range(levels):
    size=max(1,S>>level);rough=level/(levels-1)
    for face in range(6):
        d=directions(size,face);c=env(d) if level==0 else prefilter(d,rough)
        c=np.c_[c,np.ones(len(c))].astype('<f2');chunks.append(c.tobytes())
    meta.append({'size':size,'roughness':rough});print('environment',level,size,flush=True)
# Order-2 SH irradiance, integrated over a Fibonacci sphere.
N=65536;i=np.arange(N);yy=1-2*(i+.5)/N;phi=i*(math.pi*(3-math.sqrt(5)));rr=np.sqrt(1-yy*yy)
d=np.stack([rr*np.cos(phi),yy,rr*np.sin(phi)],-1);x,y,z=d.T
Y=np.stack([np.full(N,.2820947918),.4886025119*y,.4886025119*z,.4886025119*x,1.092548431*x*y,1.092548431*y*z,.3153915653*(3*z*z-1),1.092548431*x*z,.5462742153*(x*x-y*y)],-1)
sh=(Y.T@ambient(d))*(4*np.pi/N);sh*=np.array([np.pi,2*np.pi/3,2*np.pi/3,2*np.pi/3,np.pi/4,np.pi/4,np.pi/4,np.pi/4,np.pi/4])[:,None]
payload=b''.join(chunks);(R/'studio/environment.bin.gz').write_bytes(gzip.compress(payload,mtime=0))
(R/'studio/environment.json').write_text(json.dumps({'size':S,'levels':levels,'type':'RGBA16F','bytes':len(payload),'levelsInfo':meta,'irradianceSH':sh.tolist(),'source':'Matched rectangular studio lights and dark photographic sweep; 192 GGX importance samples per texel. SH stores ambient only, direct rectangular lights use baked visibility.'},indent=2))
