from pathlib import Path
import os,subprocess,time,json,sys,base64
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification';O.mkdir(exist_ok=True)
w=int(sys.argv[1]) if len(sys.argv)>1 else 640;h=int(sys.argv[2]) if len(sys.argv)>2 else 400;samples=int(sys.argv[3]) if len(sys.argv)>3 else 32;chapter=float(sys.argv[4]) if len(sys.argv)>4 else 0
x=subprocess.Popen(['Xvfb',':153','-screen','0','2000x3000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':153';time.sleep(.2)
errors=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  ctx=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1,reduced_motion='reduce',accept_downloads=True)
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:print('CONSOLE',m.type,m.text[:500],flush=True) if m.type in ['error','warning'] else None)
  load_html(page,R/'dist/index.html')
  page.wait_for_function('window.CYBR && (CYBR.report.frame>0 || CYBR.report.error)',timeout=240000)
  rep=page.evaluate('CYBR.report');print(json.dumps(rep,indent=2),flush=True);assert rep['ready'],rep.get('error')
  page.evaluate('(ch)=>{CYBR.pause();CYBR.test.renderAt(ch,1.5);}',chapter)
  for i in range(samples):
   start=time.time();total=page.evaluate('()=>CYBR.test.refineSamples(1)');print('sample',total,'time',time.time()-start,flush=True)
   # rAF is cancelled to make each sample an explicit, reproducible operation.
   page.evaluate('()=>{for(let i=1;i<2000;i++)cancelAnimationFrame(i);}')
   if (i+1) in [1,4,8,16,32,64,128,256,512] or i==samples-1:
    shot=page.evaluate('CYBR.test.captureStudio()');url=shot['image'];out=O/f'final-studio-ch{chapter:g}-{w}x{h}-{shot["samples"]}spp.png';out.write_bytes(base64.b64decode(url.split(',',1)[1]));print('CAPTURE',out,flush=True)
  (O/f'studio-{chapter:g}-{w}x{h}-report.json').write_text(json.dumps({'report':page.evaluate('CYBR.report'),'errors':errors,'glError':page.evaluate('CYBR.test.gl.getError()')},indent=2))
  browser.close()
finally:x.terminate()
