"""Render two high-detail scene-local optics caches from generated geometry.
RGBM stores linear radiance in RGBA8, avoiding an expanded floating-point cache.
These are offline renders, not photographs or externally sourced assets.
"""
from pathlib import Path
import os,subprocess,time,json,base64,gzip,hashlib
import numpy as np
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;N=512
ns={'__file__':str(R/'studio/optical_environment.py')}
exec((R/'studio/optical_environment.py').read_text().split("if __name__=='__main__':")[0],ns)
x=subprocess.Popen(['Xvfb',':163','-screen','0','1000x1000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':163';time.sleep(.3)
faces=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  p=b.new_page(viewport={'width':N,'height':N},reduced_motion='reduce');p.set_default_timeout(180000);load_html(p,R/'dist/index.html')
  p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=180000);assert p.evaluate('CYBR.report.ready'),p.evaluate('CYBR.report')
  p.evaluate('CYBR.pause()')
  for oid in [1,7]:
   for f in range(6):
    data=p.evaluate('v=>CYBR.test.captureProbe(...v)',[oid,f,True]);a=np.frombuffer(base64.b64decode(data),'<f4').reshape(N,N,4)
    rgb=np.where(a[:,:,3:]>.5,a[:,:,:3],ns['env'](ns['directions'](N,f)).reshape(N,N,3));assert np.isfinite(rgb).all()
    faces.append(rgb);print('Optical capture',oid,f,float(rgb.max()),flush=True)
  assert p.evaluate('CYBR.test.gl.getError()')==0;b.close()
finally:x.terminate()
c=np.array(faces);chunks=[]
for level in range(10):
 if level:c=.25*(c[:,0::2,0::2]+c[:,1::2,0::2]+c[:,0::2,1::2]+c[:,1::2,1::2])
 rgb=np.clip(c,0,16)/16;m=np.maximum(1/255,np.ceil(rgb.max(-1,keepdims=True)*255)/255);a=np.concatenate([rgb/m,m],-1)
 chunks.append(np.rint(np.clip(a,0,1)*255).astype('u1').tobytes())
raw=b''.join(chunks);(R/'studio/optical-probes.bin.gz').write_bytes(gzip.compress(raw,mtime=0))
info=dict(size=N,layers=12,levels=10,bytes=len(raw),format='RGBA8 RGBM',encodingRange=16,objects=[1,7],provisional=False,geometrySHA256=json.loads((R/'geometry/packed.json').read_text())['sha256'],source='Actual opaque-geometry browser captures at the optical centers, including the optical mounts; analytic glass itself is absent from the opaque pass; box-filtered mips. Scene-local fallback for off-screen refraction/reflection, not a photograph or scan.')
(R/'studio/optical-probes.json').write_text(json.dumps(info,indent=2));print('OPTICS DONE',len(raw),flush=True)
