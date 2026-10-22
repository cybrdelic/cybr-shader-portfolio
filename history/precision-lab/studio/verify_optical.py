"""Execute browser checks for Precision Lab. These are not visual or FPS certifications."""
from pathlib import Path
import base64,gzip,hashlib,io,json,os,struct,subprocess,time,traceback
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_loading import load_html
from capture_live_checked import CAPTURE_JS
R=Path(__file__).resolve().parent.parent;O=R/'verification/final';O.mkdir(parents=True,exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[];requests=[];reports={}
def check(name,passed,**evidence):
 entry={'name':name,'pass':bool(passed),**evidence};checks.append(entry);print(json.dumps(entry),flush=True)
def image(data,name):
 if data.startswith('data:'):data=data.split(',',1)[1]
 raw=base64.b64decode(data);(O/name).write_bytes(raw);im=Image.open(io.BytesIO(raw)).convert('RGB');small=np.asarray(im.resize((96,64)))
 return {'size':list(im.size),'sampleColors':len(np.unique(small.reshape(-1,3),axis=0)),'channelStd':float(small.std()),'sha256':hashlib.sha256(raw).hexdigest()}
# Validate actual binary caches instead of trusting their descriptive metadata.
info=json.loads((R/'geometry/optical-bvh.json').read_text());raw=gzip.decompress((R/'geometry/optical-bvh.bin.gz').read_bytes());header=struct.unpack('<8I',raw[:32]);n,t,v=header[1:4];nodes=np.frombuffer(raw,'<f4',count=n*8,offset=32).reshape(n,8);tri=np.frombuffer(raw,'<u4',count=t*4,offset=32+n*32).reshape(t,4)
check('BVH header, triangle/vertex counts and byte length',n==info['nodes'] and t==info['triangles'] and v==info['vertices'] and len(raw)==32+n*32+t*16)
check('Finite ordered hierarchy bounds and valid vertex indices',np.isfinite(nodes).all() and (nodes[:,:3]<=nodes[:,4:7]).all() and tri[:,:3].max()<v and tri[:,3].max()<4)
check('Hierarchy depth fits shader stack',info['maxDepth']<64,maxDepth=info['maxDepth'],stack=64)
for name in ['color','normal']:
 b=gzip.decompress((R/f'materials/{name}.rgba.gz').read_bytes());check(name+' material array size',len(b)==8*1024*1024*4,bytes=len(b))
del raw,nodes,tri,b
x=subprocess.Popen(['Xvfb',':154','-screen','0','2200x3000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':154';time.sleep(.3)
try:
 with sync_playwright() as pw:
  def browser():return pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  def page_for(b,name,viewport,dpr=1,mobile=False,no_float=False):
   ctx=b.new_context(viewport=viewport,device_scale_factor=dpr,reduced_motion='reduce',has_touch=mobile,is_mobile=mobile,accept_downloads=True)
   p=ctx.new_page();p.set_default_timeout(120000);p.on('pageerror',lambda e:errors.append({'scope':name,'error':str(e)}));p.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http://','https://')) else None)
   if no_float:p.evaluate("(()=>{const get=WebGL2RenderingContext.prototype.getExtension;WebGL2RenderingContext.prototype.getExtension=function(n){return n==='EXT_color_buffer_float'?null:get.call(this,n)}})()")
   load_html(p,R/'dist/index.html');p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=240000)
   rep=p.evaluate('CYBR.report');check(name+' startup',rep['ready'] and not rep['error'],api=rep['api'],gpu=rep['gpu'],error=rep['error']);
   if not no_float:check(name+' defaults to native Studio refinement',rep['progressiveStudio']['enabled'] and rep['renderScale']==1)
   p.evaluate('CYBR.test.setStudio(false);CYBR.pause()');return ctx,p
  b=browser();ctx,p=page_for(b,'Desktop',{'width':960,'height':600})
  for chapter in range(8):
   shot=p.evaluate(CAPTURE_JS,chapter)
   ev=image(shot,f'live-chapter-{chapter}.png');check('Live chapter '+str(chapter),ev['size']==[960,600] and ev['sampleColors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,**ev)
  p.evaluate('CYBR.test.renderAt(0,1.5)');p.keyboard.press('ArrowRight');p.wait_for_function('CYBR.diagnostics.chapter===1');check('Keyboard chapter navigation',p.evaluate('CYBR.diagnostics.target')==1)
  p.evaluate('CYBR.test.renderAt(0,1.5)');p.locator('#portfolio').dispatch_event('wheel',{'deltaY':160,'deltaMode':0});p.wait_for_function('CYBR.diagnostics.chapter===1');check('Wheel changes and settles chapter',p.evaluate('CYBR.diagnostics.target')==1)
  p.evaluate('CYBR.pause();CYBR.test.renderAt(2,1.5)')
  shots=[]
  for i in range(4):
   shot=p.evaluate('()=>{const samples=CYBR.test.refineSamples(1);return {...CYBR.test.captureStudio(),samples};}');ev=image(shot['image'],f'studio-turbine-{shot["samples"]}spp.png');shots.append(ev['sha256'])
  rep=p.evaluate('CYBR.report');check('Progressive samples accumulate at unchanged dimensions',rep['progressiveStudio']['samples']==4 and rep['resolution']==[960,600] and len(set(shots))==4,samples=rep['progressiveStudio']['samples'],distinctCaptures=len(set(shots)))
  p.evaluate('CYBR.test.setDenoise(false)');rawshot=p.evaluate('CYBR.test.captureStudio()');rawinfo=image(rawshot['image'],'studio-raw-4spp.png');p.evaluate('CYBR.test.setDenoise(true)');clean=p.evaluate('CYBR.test.captureStudio()');cleaninfo=image(clean['image'],'studio-reconstructed-4spp.png');check('Native guided reconstruction is optional and changes the actual image',rawinfo['sha256']!=cleaninfo['sha256'] and rawinfo['size']==cleaninfo['size']==[960,600] and p.evaluate('CYBR.test.gl.getError()')==0)
  reset_count=p.evaluate('()=>{CYBR.go(1);return CYBR.report.progressiveStudio.samples;}');check('View change immediately resets accumulation',reset_count==0)
  shot=p.evaluate('()=>{CYBR.test.refineSamples(1);return CYBR.test.captureStudio();}');ev=image(shot['image'],'studio-optics-first-sample.png');check('New view starts independent Studio history',shot['samples']==1 and ev['sampleColors']>200,**ev)
  p.locator('#visible-diagnostics').click();p.locator('#performance-panel').wait_for(state='visible');r=json.loads(p.locator('#performance-report').input_value())
  check('Selectable diagnostics includes correct mode and dimensions',r['progressiveStudio']['enabled'] and r['resolution']==[960,600] and r['targetFPS'] is None)
  p.evaluate("()=>{Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('test denial'))},configurable:true});document.execCommand=()=>false}")
  p.locator('#performance-copy').click();p.wait_for_function('document.getElementById("copy-result").textContent.includes("selected")');sel=p.evaluate('(()=>{const t=document.getElementById("performance-report");return [t.selectionStart,t.selectionEnd,t.value.length]})()');check('Clipboard-denied fallback selects the full report',sel[0]==0 and sel[1]==sel[2])
  with p.expect_download() as download:p.locator('#performance-download').click()
  download.value.save_as(str(O/'downloaded-report.json'));check('Diagnostics JSON download',json.loads((O/'downloaded-report.json').read_text())['build']=='cybr-precision-lab-2026-10-22')
  p.locator('#performance-close').click();p.locator('#live-mode').click();p.evaluate('CYBR.pause()');check('Live mode restores renderer choice without downscaling',not p.evaluate('CYBR.report.progressiveStudio.enabled') and p.evaluate('CYBR.report.resolution')==[960,600])
  p.evaluate('CYBR.setScale(.75)');p.wait_for_function('CYBR.report.resolution[0]===720');check('Lower scale is explicit only',p.evaluate('CYBR.report.resolutionReason')=='explicit-user-selection')
  p.evaluate('CYBR.setScale(1)');p.wait_for_function('CYBR.report.resolution[0]===960');check('Native resolution returns exactly',p.evaluate('CYBR.report.resolution')==[960,600])
  p.evaluate('window.loss=CYBR.test.gl.getExtension("WEBGL_lose_context");loss.loseContext()');p.wait_for_function('CYBR.report.lost');p.wait_for_timeout(150);p.evaluate('loss.restoreContext()');p.wait_for_function('CYBR.report.ready&&!CYBR.report.lost',timeout=240000)
  shot=p.evaluate('()=>{CYBR.pause();CYBR.test.renderAt(0,1.5);CYBR.test.refineSamples(1);return CYBR.test.captureStudio();}');ev=image(shot['image'],'studio-after-context-restore.png');check('Context restoration rebuilds optics and Studio resources',ev['sampleColors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,**ev)
  reports['desktop']=p.evaluate('CYBR.report');ctx.close();b.close()
  b=browser();ctx,p=page_for(b,'Portrait dimensions',{'width':443,'height':816},3.25,True)
  p.add_style_tag(content='#portfolio{width:443.0769348144531px!important;height:816.6154174804688px!important;}');p.wait_for_function('CYBR.report.resolution[0]===1440&&CYBR.report.resolution[1]===2654')
  shot=p.evaluate('()=>{CYBR.pause();CYBR.test.renderAt(0,1.5);return document.getElementById("portfolio").toDataURL("image/png")}');ev=image(shot,'portrait-native-live.png');check('Actual native portrait canvas',ev['size']==[1440,2654] and ev['sampleColors']>200,**ev)
  rects={name:p.locator('#'+name).bounding_box() for name in ['live-mode','studio-mode','visible-diagnostics']};check('Mobile controls are visible and touch-sized',all(v and v['height']>=44 and v['x']>=0 and v['x']+v['width']<=443.5 for v in rects.values()),rects=rects)
  cdp=ctx.new_cdp_session(p);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':205,'y':490,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':205,'y':290,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});p.wait_for_function('CYBR.diagnostics.target>=1');check('Touch swipe navigates',p.evaluate('CYBR.diagnostics.target')>=1)
  shot=p.evaluate('()=>{CYBR.pause();CYBR.test.renderAt(0,1.5);CYBR.test.refineSamples(1);return CYBR.test.captureStudio();}');ev=image(shot['image'],'portrait-native-studio-first-sample.png');check('Studio also renders the full native portrait buffer',ev['size']==[1440,2654] and ev['sampleColors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,samples=shot['samples'],**ev)
  p.locator('#visible-diagnostics').click();p.locator('#performance-panel').wait_for(state='visible');check('Portrait diagnostics remains accessible',p.locator('#performance-report').is_visible());p.screenshot(path=str(O/'portrait-diagnostics-ui.png'))
  reports['portrait']=p.evaluate('CYBR.report');ctx.close();b.close()
  b=browser();ctx,p=page_for(b,'Float-color-disabled fallback',{'width':640,'height':400},no_float=True)
  p.evaluate('CYBR.test.setStudio(true)');check('Unsupported Studio leaves Live usable',not p.evaluate('CYBR.report.progressiveStudio.enabled') and not p.evaluate('CYBR.report.linearHDR') and p.evaluate('CYBR.report.ready'))
  reports['noFloat']=p.evaluate('CYBR.report');ctx.close();b.close()
except BaseException as exc:
 errors.append({'testHarness':str(exc),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
finally:
 x.terminate()
 check('No uncaught JavaScript or test-harness errors',not errors,errors=errors)
 check('No external runtime asset requests',not requests,requests=requests)
 result={'build':'cybr-precision-lab-2026-10-22','htmlSHA256':hashlib.sha256(HTML.encode()).hexdigest(),'physicalAndroidTested':False,'sixtyFPSVerified':False,'visualTargetCertified':False,'testEnvironment':'Chromium with ANGLE/Mesa llvmpipe. Portrait dimensions and input are emulated, not a physical Adreno test. Render readbacks are real; no image generation or retouching.','browserVersion':subprocess.run(['/usr/bin/chromium','--version'],capture_output=True,text=True).stdout.strip(),'checks':checks,'reports':reports,'passed':sum(c['pass'] for c in checks),'total':len(checks),'errors':errors}
 (O/'test-report.json').write_text(json.dumps(result,indent=2));print('RESULT',result['passed'],'/',result['total'],flush=True)
