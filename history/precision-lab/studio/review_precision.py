"""Capture actual refined browser views, including an unfiltered reference."""
from pathlib import Path
import os,subprocess,time,json,base64,hashlib
from playwright.sync_api import sync_playwright
from browser_loading import load_html
from capture_live_checked import CAPTURE_JS
R=Path(__file__).resolve().parent.parent;O=R/'verification/review';O.mkdir(parents=True,exist_ok=True)
x=subprocess.Popen(['Xvfb',':157','-screen','0','1800x1200x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':157';time.sleep(.2)
errors=[];results=[]
html_hash=hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest()
if (O/'review.json').exists():
 previous=json.loads((O/'review.json').read_text())
 if previous.get('htmlSHA256')==html_hash:
  results=previous.get('views',[])
completed={v['chapter'] for v in results}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  page=browser.new_page(viewport={'width':1280,'height':800},device_scale_factor=1,reduced_motion='reduce');page.set_default_timeout(240000);page.on('pageerror',lambda e:errors.append(str(e)))
  load_html(page,R/'dist/index.html');page.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=240000);assert page.evaluate('CYBR.report.ready'),page.evaluate('CYBR.report.error')
  print('READY',flush=True)
  for chapter,samples in [(0,128),(2,64)]:
   if chapter in completed:continue
   if chapter!=0:page.set_viewport_size({'width':1280,'height':800})
   url=page.evaluate(CAPTURE_JS,chapter);(O/f'live-{chapter}.png').write_bytes(base64.b64decode(url.split(',',1)[1]));print('LIVE',chapter,flush=True)
   page.evaluate('()=>{CYBR.test.setStudio(true);CYBR.pause();for(let i=1;i<10000;i++)cancelAnimationFrame(i);}')
   for begin in range(0,samples,8):
    count=page.evaluate('n=>{for(let i=1;i<10000;i++)cancelAnimationFrame(i);return CYBR.test.refineSamples(n);}',min(8,samples-begin))
    if count in [16,32,64,96,128]:
     capture=page.evaluate('CYBR.test.captureStudio()');(O/f'studio-{chapter}-{count}.png').write_bytes(base64.b64decode(capture['image'].split(',',1)[1]));print('STUDIO',chapter,count,flush=True)
   page.evaluate('CYBR.test.setDenoise(false)');capture=page.evaluate('CYBR.test.captureStudio()');(O/f'raw-{chapter}-{capture["samples"]}.png').write_bytes(base64.b64decode(capture['image'].split(',',1)[1]));page.evaluate('CYBR.test.setDenoise(true)')
   rep=page.evaluate('CYBR.report');results.append({'chapter':chapter,'report':rep,'glError':page.evaluate('CYBR.test.gl.getError()')});(O/'review.json').write_text(json.dumps({'htmlSHA256':hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest(),'views':results,'errors':errors},indent=2))
  browser.close()
finally:x.terminate()
