"""Deterministic radiance of a photographic room, integrated for roughness.
The studio is an actual analytic environment, not an imported/generated image.
Panels share positions and ratios with the direct-light shader.
"""
from pathlib import Path
import numpy as np, math, gzip, json
R=Path(__file__).resolve().parent.parent
S=512

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)
def ambient(d):
 y=np.clip(d[...,1]*.5+.5,0,1)
 return (.012+.022*y[...,None]**1.3)*np.array([1.02,1.0,.98])
def env(d):
 d=np.asarray(d,np.float32);out=ambient(d)
 # Horizontal seams on low-level studio walls give optical reflections scale.
 yy=d[...,1];phi=np.arctan2(d[...,2],d[...,0]);horizon=np.exp(-np.square((yy+.03)/.29))
 wall=(.011+.010*(.5+.5*np.cos(phi*7.))) * horizon
 out+=wall[...,None]*np.array([1.05,1.,.95])
 panels=[([-3.8,6.5,5.4],[.34,.24],[9.0,8.65,8.05]),
         ([5.2,3.5,-2.7],[.26,.43],[2.2,2.5,2.9]),
         ([-3.5,3.8,-5.8],[.075,.45],[.55,.58,.64]),
         ([5.5,2.3,1.8],[.030,.32],[.38,.41,.45])]
 for facing,size,col in panels:
  n=unit(np.array(facing,np.float32));h=unit(np.cross([0,1,0],n));v=np.cross(n,h)
  front=d@n;u=(d@h)/np.maximum(front,.00001);w=(d@v)/np.maximum(front,.00001)
  e=np.maximum(abs(u)-size[0],abs(w)-size[1]);edge=np.clip((.008-e)/.016,0,1);edge=edge*edge*(3-2*edge)*(front>0)
  panel=.84+.16*np.exp(-1.7*((u/size[0])**2+(w/size[1])**2))
  # Diffusion-cloth frame outside the emitter; black flags yield sharp bands.
  frame=np.clip((.019-e)/.014,0,1)*(1-edge)*(front>0)
  out*=1-frame[...,None]*.45
  out+=edge[...,None]*panel[...,None]*np.array(col)
 # A negative-fill card facing the lens gives cylindrical metal distinct edges.
 n=unit(np.array([-.1,.03,1.]));card=np.clip((d@n-.77)/.15,0,1)
 out*=1-.50*card[...,None]*(1-np.clip(d[...,1:2],0,1))
 return out.astype(np.float32)
def directions(n,face):
 u,v=np.meshgrid((np.arange(n)+.5)/n*2-1,(np.arange(n)+.5)/n*2-1);one=np.ones_like(u)
 a=[(one,-v,-u),(-one,-v,u),(u,one,v),(u,-one,-v),(u,-v,one),(-u,-v,-one)][face]
 return unit(np.stack(a,-1).reshape(-1,3)).astype(np.float32)
def radical(n):
 a=np.arange(n,dtype=np.uint32);a=(a<<16)|(a>>16)
 a=((a&0x55555555)<<1)|((a&0xaaaaaaaa)>>1);a=((a&0x33333333)<<2)|((a&0xcccccccc)>>2)
 a=((a&0x0f0f0f0f)<<4)|((a&0xf0f0f0f0)>>4);a=((a&0x00ff00ff)<<8)|((a&0xff00ff00)>>8)
 return a.astype(np.float64)*2.3283064365386963e-10

def sample_cube(cube,d):
 a=np.abs(d);axis=np.argmax(a,axis=-1);positive=np.take_along_axis(d,axis[...,None],-1)[...,0]>0
 face=axis*2+(~positive).astype(int);den=np.maximum(np.max(a,axis=-1),1e-9);x,y,z=d.T
 u=np.choose(face,[-z,z,x,x,x,-x])/den;v=np.choose(face,[-y,-y,z,-z,-y,-y])/den
 px=np.clip((u*.5+.5)*S-.5,0,S-1);py=np.clip((v*.5+.5)*S-.5,0,S-1);ix=px.astype(int);iy=py.astype(int)
 fx=(px-ix)[:,None];fy=(py-iy)[:,None];jx=np.minimum(ix+1,S-1);jy=np.minimum(iy+1,S-1)
 return (cube[face,iy,ix]*(1-fx)+cube[face,iy,jx]*fx)*(1-fy)+(cube[face,jy,ix]*(1-fx)+cube[face,jy,jx]*fx)*fy

def prefilter(cube,n,rough,samples):
 xi=(np.arange(samples)+.5)/samples;alpha=rough*rough
 ct=np.sqrt((1-radical(samples))/(1+(alpha*alpha-1)*radical(samples)));st=np.sqrt(1-ct*ct);phi=2*np.pi*xi
 h=np.stack([st*np.cos(phi),st*np.sin(phi),ct],-1).astype(np.float32);out=[]
 for start in range(0,len(n),256):
  nn=n[start:start+256];up=np.where((np.abs(nn[:,2])<.999)[:,None],[0,0,1],[1,0,0]);t=unit(np.cross(up,nn));b=np.cross(nn,t)
  hh=t[:,None,:]*h[None,:,0,None]+b[:,None,:]*h[None,:,1,None]+nn[:,None,:]*h[None,:,2,None]
  l=2*np.sum(nn[:,None,:]*hh,axis=-1,keepdims=True)*hh-nn[:,None,:];w=np.maximum(np.sum(nn[:,None,:]*l,axis=-1),0)
  val=sample_cube(cube,l.reshape(-1,3)).reshape(len(nn),samples,3)
  out.append(np.sum(val*w[...,None],axis=1)/np.maximum(w.sum(axis=1,keepdims=True),1e-8))
 return np.concatenate(out)
if __name__=='__main__':
 cube=np.array([env(directions(S,f)).reshape(S,S,3) for f in range(6)])
 chunks=[];levels=int(math.log2(S))+1
 for level in range(levels):
  size=max(1,S>>level);rough=level/(levels-1)
  for face in range(6):
   d=directions(size,face);c=cube[face].reshape(-1,3) if level==0 else prefilter(cube,d,rough,96 if level<3 else 256)
   chunks.append(np.c_[c,np.ones(len(c))].astype('<f2').tobytes())
  print('environment level',level,size,flush=True)
 N=32768;i=np.arange(N);yy=1-2*(i+.5)/N;phi=i*(math.pi*(3-math.sqrt(5)));rr=np.sqrt(1-yy*yy)
 d=np.stack([rr*np.cos(phi),yy,rr*np.sin(phi)],-1);x,y,z=d.T
 Y=np.stack([np.full(N,.2820947918),.4886025119*y,.4886025119*z,.4886025119*x,1.092548431*x*y,1.092548431*y*z,.3153915653*(3*z*z-1),1.092548431*x*z,.5462742153*(x*x-y*y)],-1)
 sh=(Y.T@ambient(d))*(4*np.pi/N);sh*=np.array([np.pi,2*np.pi/3,2*np.pi/3,2*np.pi/3,np.pi/4,np.pi/4,np.pi/4,np.pi/4,np.pi/4])[:,None]
 payload=b''.join(chunks);(R/'studio/environment.bin.gz').write_bytes(gzip.compress(payload,6,mtime=0))
 (R/'studio/environment.json').write_text(json.dumps({'size':S,'levels':levels,'type':'RGBA16F','bytes':len(payload),'irradianceSH':sh.tolist(),'source':'Analytic studio radiance with key, fill, strip/rim panels and negative-fill flags; GGX-filtered 512px cubemap faces. Not a photograph or AI-generated image.'},indent=2))
