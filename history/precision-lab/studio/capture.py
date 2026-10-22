from pathlib import Path
import os,subprocess,time,json,sys,base64
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification';O.mkdir(exist_ok=True)
chapters=list(map(float,sys.argv[1:])) or [0,1,2,3,4,5,6,7]
x=subprocess.Popen(['Xvfb',':152','-screen','0','2000x3000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':152';time.sleep(.2)
errors=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  ctx=browser.new_context(viewport={'width':1536,'height':960},device_scale_factor=1,reduced_motion='reduce',accept_downloads=True)
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda msg:print('CONSOLE',msg.type,msg.text[:500],flush=True) if msg.type in ['error','warning'] else None)
  load_html(page,R/'dist/index.html')
  page.wait_for_function('window.CYBR && (CYBR.report.frame>0 || CYBR.report.error)',timeout=180000)
  rep=page.evaluate('CYBR.report');print(json.dumps(rep,indent=2),flush=True);assert rep['ready'],rep.get('error')
  for c in chapters:
   start=time.time();url=page.evaluate('(ch)=>{CYBR.pause();CYBR.test.renderAt(ch,1.5);return document.getElementById("portfolio").toDataURL("image/png");}',c)
   path=O/f'chapter-{c:g}.png';path.write_bytes(base64.b64decode(url.split(',',1)[1]));print('CAPTURE',str(path),round(time.time()-start,2),flush=True)
  (O/'preview-report.json').write_text(json.dumps({'report':page.evaluate('CYBR.report'),'errors':errors,'glError':page.evaluate('CYBR.test.gl.getError()')},indent=2))
  browser.close()
finally:x.terminate()
