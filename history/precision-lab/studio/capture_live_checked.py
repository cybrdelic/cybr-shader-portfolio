"""Capture a live frame after waiting for prior GPU work, without a stale drawing buffer."""
from pathlib import Path
import base64,hashlib,io,json,os,subprocess,time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification/final'
CAPTURE_JS='''async (chapter)=>{
  CYBR.test.setStudio(false);CYBR.pause();
  const gl=CYBR.test.gl, fence=gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);gl.flush();
  await new Promise((resolve,reject)=>{let started=performance.now();function poll(){const r=gl.clientWaitSync(fence,0,0);if(r===gl.WAIT_FAILED)return reject(new Error('Capture fence failed'));if(r===gl.TIMEOUT_EXPIRED){if(performance.now()-started>120000)return reject(new Error('Capture fence timeout'));return setTimeout(poll,16);}resolve();}poll();});
  gl.deleteSync(fence);CYBR.test.renderAt(chapter,1.5);
  return document.getElementById('portfolio').toDataURL('image/png');
}'''
if __name__=='__main__':
 x=subprocess.Popen(['Xvfb',':155','-screen','0','1200x800x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':155';time.sleep(.2)
 try:
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
   ctx=b.new_context(viewport={'width':960,'height':600},device_scale_factor=1,reduced_motion='reduce');p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   load_html(p,R/'dist/index.html');p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=240000)
   url=p.evaluate(CAPTURE_JS,0);raw=base64.b64decode(url.split(',',1)[1]);path=O/'live-chapter-0-checked.png';path.write_bytes(raw);im=Image.open(io.BytesIO(raw)).convert('RGB');ar=np.asarray(im.resize((96,64)));colors=len(np.unique(ar.reshape(-1,3),axis=0))
   report={'name':'Live chapter 0 after completion-aware readback','pass':im.size==(960,600) and colors>200 and not errors,'size':list(im.size),'sampleColors':colors,'channelStd':float(ar.std()),'sha256':hashlib.sha256(raw).hexdigest(),'htmlSHA256':hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest(),'errors':errors,'note':'The earlier capture read a discarded default framebuffer because rendering was throttled by two outstanding fences. This capture waits for prior commands, then draws and reads in the same JavaScript evaluation. Production HTML is unchanged.'}
   (O/'live-readback-retest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);b.close()
 finally:x.terminate()
