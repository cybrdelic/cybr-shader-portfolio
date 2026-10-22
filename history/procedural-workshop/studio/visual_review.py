"""Capture native browser pixels and matched prior-build cameras. No post-processing.
Layout thumbnails are the only resized images; native captures remain unmodified.
"""
from pathlib import Path
import os,subprocess,time,base64,json,hashlib
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification/visual';O.mkdir(parents=True,exist_ok=True)
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,default=None);args=parser.parse_args();BASE=args.baseline
x=subprocess.Popen(['Xvfb',':164','-screen','0','2000x1400x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':164';time.sleep(.25)
errors=[];record={'nativeResolution':[1920,1200],'time':1.5,'newHTMLSHA256':hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest(),'photographicAssets':False,'imagePostprocessing':False,'captures':[]};cameras={}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  for version,path in [('new',R/'dist/index.html')]+([('before',BASE)] if BASE else []):
   p=b.new_page(viewport={'width':1920,'height':1200},device_scale_factor=1,reduced_motion='reduce');p.set_default_timeout(180000);p.on('pageerror',lambda e:errors.append(str(e)))
   load_html(p,path);p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)')
   assert p.evaluate('CYBR.report.ready'),p.evaluate('CYBR.report')
   for chapter in ([0,1,2,3,4,5,6] if version=='new' else [0,2,3,6]):
    if version=='before':p.evaluate('c=>CYBR.test.setCamera(c)',cameras[chapter])
    data=p.evaluate('ch=>CYBR.test.capture(ch,1.5)',chapter);raw=base64.b64decode(data.split(',')[1]);name=f'{version}-{chapter}.png';(O/name).write_bytes(raw)
    if version=='new':cameras[chapter]=p.evaluate('CYBR.test.getCamera()')
    record['captures'].append({'file':name,'chapter':chapter,'camera':cameras[chapter],'sha256':hashlib.sha256(raw).hexdigest(),'GLerror':p.evaluate('CYBR.test.gl.getError()')})
    print(version,chapter,len(raw),flush=True)
   record[version+'Report']=p.evaluate('CYBR.report');p.close()
  b.close()
finally:
 x.terminate();record['errors']=errors;(O/'capture-manifest.json').write_text(json.dumps(record,indent=2))
