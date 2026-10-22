from browser_runtime import start_display, launch_browser
"""Offline capture and GGX integration of scene-local reflection probes.
The normal browser renderer only samples this cached lighting data. It does not
capture cubemaps or perform a full scene trace per frame. No external assets.
"""
from pathlib import Path
import os,subprocess,time,json,base64,gzip,math
import numpy as np
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent
S=256
# Reuse the exact same procedural room used by the visible PBR renderer.
ns={'__file__':str(R/'studio/optical_environment.py')}
exec((R/'studio/optical_environment.py').read_text().split("if __name__=='__main__':")[0],ns)
env,directions,unit,radical=[ns[k] for k in ['env','directions','unit','radical']]

def capture():
 x=start_display()
 cubes=[]
 try:
  with sync_playwright() as pw:
   browser=launch_browser(pw)
   page=browser.new_page(viewport={'width':S,'height':S},device_scale_factor=1,reduced_motion='reduce')
   load_html(page,R/'dist/index.html')
   page.wait_for_function('window.CYBR && (CYBR.report.frame>0 || CYBR.report.error)',timeout=120000)
   page.evaluate('CYBR.pause()')
   rep=page.evaluate('CYBR.report');assert rep['ready'] and rep['linearHDR'],rep
   for oid in range(1,8):
    faces=[]
    for face in range(6):
     payload=page.evaluate('x=>CYBR.test.captureProbe(...x)',[oid,face])
     arr=np.frombuffer(base64.b64decode(payload),'<f4').reshape(S,S,4).copy()
     room=env(directions(S,face)).reshape(S,S,3)
     arr[:,:,:3]=np.where(arr[:,:,3:]>.5,arr[:,:,:3],room)
     assert np.isfinite(arr).all() and arr[:,:,:3].max()>0
     faces.append(arr);print('captured',oid,face,'range',arr[:,:,:3].min(),arr[:,:,:3].max(),flush=True)
    cubes.append(faces)
   assert page.evaluate('CYBR.test.gl.getError()')==0
   browser.close()
 finally:x.terminate()
 cubes=np.asarray(cubes,dtype=np.float32);np.save(R/'studio/probe-captures.npy',cubes)
 return cubes

def sample_cube(cube,d):
 a=np.abs(d);axis=np.argmax(a,axis=-1);positive=np.take_along_axis(d,axis[...,None],-1)[...,0]>0
 face=axis*2+(~positive).astype(int);den=np.max(a,axis=-1)
 x,y,z=d[...,0],d[...,1],d[...,2]
 u=np.choose(face,[-z,z,x,x,x,-x])/den
 v=np.choose(face,[-y,-y,z,-z,-y,-y])/den
 px=np.clip((u*.5+.5)*S-.5,0,S-1);py=np.clip((v*.5+.5)*S-.5,0,S-1)
 ix=np.floor(px).astype(int);iy=np.floor(py).astype(int);fx=(px-ix)[...,None];fy=(py-iy)[...,None]
 jx=np.minimum(ix+1,S-1);jy=np.minimum(iy+1,S-1)
 return (cube[face,iy,ix]*(1-fx)+cube[face,iy,jx]*fx)*(1-fy)+(cube[face,jy,ix]*(1-fx)+cube[face,jy,jx]*fx)*fy

def filter_face(cube,n,rough,samples=160):
 xi=(np.arange(samples)+.5)/samples;alpha=rough*rough
 ct=np.sqrt((1-radical(samples))/(1+(alpha*alpha-1)*radical(samples)));st=np.sqrt(1-ct*ct);phi=2*np.pi*xi
 h=np.stack([st*np.cos(phi),st*np.sin(phi),ct],-1).astype(np.float32)
 out=[]
 for start in range(0,len(n),256):
  nn=n[start:start+256];up=np.where((np.abs(nn[:,2])<.999)[:,None],[0,0,1],[1,0,0]);t=unit(np.cross(up,nn));b=np.cross(nn,t)
  hh=t[:,None,:]*h[None,:,0,None]+b[:,None,:]*h[None,:,1,None]+nn[:,None,:]*h[None,:,2,None]
  l=2*np.sum(nn[:,None,:]*hh,axis=-1,keepdims=True)*hh-nn[:,None,:];w=np.maximum(np.sum(nn[:,None,:]*l,axis=-1),0)
  val=sample_cube(cube,l.reshape(-1,3)).reshape(len(nn),samples,4)
  out.append(np.sum(val*w[...,None],axis=1)/np.maximum(w.sum(axis=1,keepdims=True),1e-8))
 return np.concatenate(out)

if __name__=='__main__':
 import sys
 cubes=np.load(R/'studio/probe-captures.npy') if '--reuse' in sys.argv else capture()
 chunks=[];levels=int(math.log2(S))+1
 # Texture array layout is mip-major, then probe and cube face.
 for lev in range(levels):
  size=max(1,S>>lev);rough=lev/(levels-1)
  for oid in range(7):
   for face in range(6):
    n=directions(size,face);c=cubes[oid,face].reshape(-1,4) if lev==0 else filter_face(cubes[oid],n,rough)
    c=c.astype('<f2');chunks.append(c.tobytes())
  print('filtered probes',lev,size,flush=True)
 payload=b''.join(chunks);(R/'studio/probes.bin.gz').write_bytes(gzip.compress(payload,mtime=0))
 info={'geometrySHA256':json.loads((R/'geometry/packed.json').read_text())['sha256'],'size':S,'levels':levels,'layers':42,'probes':7,'type':'RGBA16F','bytes':len(payload),'source':'Actual geometry renders, each excluding its own exhibit. Static local image-based lighting; 160 GGX samples per filtered texel. Alpha preserves filtered geometry occupancy, separating local-object reflection from explicit direct area lights.'}
 (R/'studio/probes.json').write_text(json.dumps(info,indent=2))
 print('DONE',len(payload),flush=True)
