"""Matched actual browser captures; dimensions/camera/time recorded, no post-shading."""
from pathlib import Path
import os,time,subprocess,json,base64,sys,hashlib
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent
kind=sys.argv[1] if len(sys.argv)>1 else 'new'
source=R/'dist/index.html' if kind=='new' else Path('/mnt/data/CYBR-Portfolio-Asset-Rebuild.html')
out=R/'verification'/('full-resolution' if kind=='new' else 'matched-before');out.mkdir(exist_ok=True)
chapters=list(range(8)) if kind=='new' else [0,2,3,4,5,6]
x=subprocess.Popen(['Xvfb',':165','-screen','0','2600x1700x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':165';time.sleep(.3)
errors=[];meta=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  p=b.new_page(viewport={'width':2560,'height':1600},device_scale_factor=1,reduced_motion='reduce');p.set_default_timeout(180000)
  p.on('pageerror',lambda e:errors.append(str(e)));load_html(p,source)
  p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=180000);assert p.evaluate('CYBR.report.ready'),p.evaluate('CYBR.report')
  for ch in chapters:
   t=time.perf_counter();s=p.evaluate('ch=>CYBR.test.capture(ch,1.5)',ch);raw=base64.b64decode(s.split(',',1)[1]);name=f'chapter-{ch}.png';(out/name).write_bytes(raw)
   err=p.evaluate('CYBR.test.gl.getError()');meta.append(dict(chapter=ch,file=name,glError=err,sha256=hashlib.sha256(raw).hexdigest(),captureSeconds=time.perf_counter()-t));print(kind,ch,err,flush=True)
  report=p.evaluate('CYBR.report');b.close()
finally:x.terminate()
(out/'capture-record.json').write_text(json.dumps(dict(sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),size=[2560,1600],time=1.5,deviceScaleFactor=1,mode='actual browser canvas',postProcessing='None; PNG directly from canvas',hardware='Chromium ANGLE software graphics',captures=meta,errors=errors,report=report),indent=2))
if errors or any(x['glError'] for x in meta):raise SystemExit(1)
