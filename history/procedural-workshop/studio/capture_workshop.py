from pathlib import Path
import sys,base64,subprocess,os,time,json
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent
O=R/'verification/workshop';O.mkdir(parents=True,exist_ok=True)
x=subprocess.Popen(['Xvfb',':162','-screen','0','1600x1100x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':162';time.sleep(.25)
errors=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  p=b.new_page(viewport={'width':1280,'height':800},device_scale_factor=1,reduced_motion='reduce')
  p.set_default_timeout(120000);p.on('pageerror',lambda e:errors.append(str(e)))
  load_html(p,Path(sys.argv[1]) if len(sys.argv)>1 else R/'dist/index.html')
  p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=180000)
  report=p.evaluate('CYBR.report');print(json.dumps({k:report[k] for k in ['ready','error','gpu','resolution','triangles']}),flush=True)
  for ch in [0,1,2,3,4,5,6,7]:
   data=p.evaluate('ch=>CYBR.test.capture(ch,1.5)',ch)
   (O/f'chapter-{ch}.png').write_bytes(base64.b64decode(data.split(',')[1]));print('capture',ch,flush=True)
  report=p.evaluate('CYBR.report');report['browserErrors']=errors
  (O/'capture-report.json').write_text(json.dumps(report,indent=2));b.close()
finally:x.terminate()
