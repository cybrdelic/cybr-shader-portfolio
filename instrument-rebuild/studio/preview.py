"""Capture the actual WebGL canvas for visual review; no image substitutions."""
from pathlib import Path
import os,subprocess,time,json,base64,sys
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification';O.mkdir(exist_ok=True)
x=subprocess.Popen(['Xvfb',':161','-screen','0','1920x1440x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':161';time.sleep(.4)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  p=b.new_page(viewport={'width':1280,'height':800},device_scale_factor=1,reduced_motion='reduce')
  p.on('pageerror',lambda e:print('PAGE ERROR',e,flush=True));p.on('console',lambda e:print('CONSOLE',e.type,e.text[:350],flush=True) if e.type=='error' else None)
  p.set_default_timeout(180000);load_html(p,R/'dist/index.html')
  p.wait_for_function('window.CYBR && (CYBR.report.frame>0 || CYBR.report.error)',timeout=180000)
  r=p.evaluate('CYBR.report');print('READY',r['ready'],r['error'],flush=True)
  (O/'preview-report.json').write_text(json.dumps(r,indent=2))
  if not r['ready']:raise RuntimeError(r['error'])
  for i in (list(map(int,sys.argv[1:])) or list(range(8))):
   t=time.perf_counter();data=p.evaluate('i=>CYBR.test.capture(i,1.5)',i)
   (O/f'view-{i}.png').write_bytes(base64.b64decode(data.split(',',1)[1]));print('CAPTURE',i,time.perf_counter()-t,'error',p.evaluate('CYBR.test.gl.getError()'),flush=True)
  b.close()
finally:x.terminate()
