from browser_runtime import start_display, launch_browser
"""Real WebGL readbacks and allocation instrumentation. No hardware-emulation FPS claims."""
from pathlib import Path
import os,time,subprocess,json,base64,traceback,hashlib,io
from PIL import Image
from playwright.sync_api import sync_playwright
from browser_loading import load_html
R=Path(__file__).resolve().parent.parent;O=R/'verification';O.mkdir(exist_ok=True)
checks=[];errors=[];requests=[];reports={};measurements={}
def check(name,passed,**details):
 c={'name':name,'pass':bool(passed),**details};checks.append(c);print(json.dumps(c),flush=True)
def image(data,name):
 raw=base64.b64decode(data.split(',',1)[1]);(O/name).write_bytes(raw);im=Image.open(io.BytesIO(raw)).convert('RGB');colors=len(set(im.resize((100,100)).getdata()));return {'size':list(im.size),'colors':colors,'sha256':hashlib.sha256(raw).hexdigest()}
TRACKER=r'''(()=>{
 const P=WebGL2RenderingContext.prototype,T={textures:new Map(),buffers:new Map(),bindings:new Map(),bufferBindings:new Map(),unit:0,programs:0,renderbuffers:0,formats:[],draws:0};window.alloc=T;
 const wrap=(n,fn)=>{const f=P[n];P[n]=function(...a){const r=f.apply(this,a);fn.call(this,a,r);return r;};};
 const target=t=>t>=34069&&t<=34074?34067:t;
 const bytes=f=>({34842:8,32856:4,32849:3,33190:4,34836:16,36208:16,33321:1,33323:2})[f]??0;
 const tex=(g,t)=>T.bindings.get(T.unit+':'+target(t));
 wrap('activeTexture',(a)=>{T.unit=a[0];});wrap('bindTexture',(a)=>{T.bindings.set(T.unit+':'+a[0],a[1]);});
 wrap('texImage2D',function(a){const t=tex(this,a[0]);if(!T.textures.has(t))T.textures.set(t,new Map());T.textures.get(t).set(a[0]+':'+a[1],a[3]*a[4]*bytes(a[2]));T.formats.push(a[2]);});
 wrap('texStorage3D',function(a){const t=tex(this,a[0]);let total=0;for(let i=0;i<a[1];i++)total+=Math.max(1,a[3]>>i)*Math.max(1,a[4]>>i)*(a[0]===32879?Math.max(1,a[5]>>i):a[5])*bytes(a[2]);T.textures.set(t,new Map([['storage',total]]));T.formats.push(a[2]);});
 wrap('bindBuffer',a=>T.bufferBindings.set(a[0],a[1]));wrap('bufferData',a=>T.buffers.set(T.bufferBindings.get(a[0]),typeof a[1]==='number'?a[1]:a[1].byteLength));
 wrap('deleteTexture',a=>T.textures.delete(a[0]));wrap('deleteBuffer',a=>T.buffers.delete(a[0]));wrap('createProgram',()=>T.programs++);wrap('createRenderbuffer',()=>T.renderbuffers++);wrap('drawArrays',()=>T.draws++);wrap('drawElements',()=>T.draws++);
 T.snapshot=()=>({textureBytes:[...T.textures.values()].reduce((a,b)=>a+[...b.values()].reduce((c,d)=>c+d,0),0),bufferBytes:[...T.buffers.values()].reduce((a,b)=>a+b,0),programs:T.programs,renderbuffers:T.renderbuffers,formats:[...new Set(T.formats)],draws:T.draws});
})()'''
x=start_display()
try:
 with sync_playwright() as pw:
  def browser():return launch_browser(pw)
  def start(b,name,width,height,dpr=1,mobile=False,no_float=False,no_timer=False):
   ctx=b.new_context(viewport={'width':width,'height':height},device_scale_factor=dpr,reduced_motion='reduce',has_touch=mobile,is_mobile=mobile,accept_downloads=True);p=ctx.new_page();p.set_default_timeout(120000)
   p.on('pageerror',lambda e:errors.append({'scope':name,'error':str(e)}));p.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http://','https://')) else None)
   p.evaluate(TRACKER)
   if no_float or no_timer:
    p.evaluate('''([nof,notim])=>{const get=WebGL2RenderingContext.prototype.getExtension;WebGL2RenderingContext.prototype.getExtension=function(n){if(nof&&n==='EXT_color_buffer_float'||notim&&n==='EXT_disjoint_timer_query_webgl2')return null;return get.call(this,n);};}''',[no_float,no_timer])
   load_html(p,R/'dist/index.html');p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=180000);r=p.evaluate('CYBR.report');check(name+' actual startup',r['ready'] and not r['error'],gpu=r['gpu'],error=r['error']);
   if not r['ready']:raise RuntimeError(r['error'])
   return ctx,p
  b=browser();ctx,p=start(b,'Desktop',960,600)
  for ch in range(8):
   shot=p.evaluate('ch=>CYBR.test.capture(ch,1.5)',ch);ev=image(shot,f'chapter-{ch}.png');check('Rendered chapter '+str(ch),ev['size']==[960,600] and ev['colors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,**ev)
  r=p.evaluate('CYBR.report');a=p.evaluate('alloc.snapshot()');check('Exactly two programs; no MSAA/renderbuffers',a['programs']==2 and a['renderbuffers']==0,observed=a)
  check('Eight-frame native edge resolve completed',r['antialiasing']['samples']==8 and r['antialiasing']['historyBytes']==960*600*3)
  check('Own fitted area-light data and true generated optical captures',r['areaLighting']['bytes']==16384 and r['opticalCaptures']['provisional'] is False and r['opticalCaptures']['geometrySHA256']==r['geometrySHA256'])
  check('Baked flame volume uploaded with bounded 6 MiB storage',r['flameVolume']['bytes']==6291456 and 33323 in a['formats'],flame=r['flameVolume'])
  check('No BVH textures or progressive shaders allocated',not r['pathTracerCompiled'] and not r['bvhUploaded'] and 34836 not in a['formats'] and 36208 not in a['formats'])
  check('Reported resource bytes match intercepted GL allocations',r['memory']['applicationGpuBytes']==a['textureBytes']+a['bufferBytes'],reported=r['memory']['applicationGpuBytes'],observed=a['textureBytes']+a['bufferBytes'])
  p.evaluate('CYBR.go(0)');p.wait_for_function('CYBR.diagnostics.chapter===0');p.keyboard.press('ArrowRight');p.wait_for_function('CYBR.diagnostics.chapter===1');check('Keyboard navigation',p.evaluate('CYBR.diagnostics.target')==1)
  p.evaluate('CYBR.go(0)');p.wait_for_function('CYBR.diagnostics.chapter===0');p.locator('#portfolio').dispatch_event('wheel',{'deltaY':160,'deltaMode':0});p.wait_for_function('CYBR.diagnostics.chapter===1');check('Wheel navigation',p.evaluate('CYBR.diagnostics.target')==1)
  p.locator('#visible-diagnostics').click();p.locator('#performance-panel').wait_for(state='visible');r=json.loads(p.locator('#performance-report').input_value());check('Diagnostics accessible and accurate',r['resolution']==[960,600] and not r['progressiveStudio']['enabled'])
  p.evaluate("()=>{Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('denied'))},configurable:true});document.execCommand=()=>false;}")
  p.locator('#performance-copy').click();p.wait_for_function('document.getElementById("copy-result").textContent.includes("selected")');sel=p.locator('#performance-report').evaluate('(t)=>[t.selectionStart,t.selectionEnd,t.value.length]');check('Denied clipboard selects complete report',sel[0]==0 and sel[1]==sel[2])
  with p.expect_download() as d:p.locator('#performance-download').click()
  d.value.save_as(str(O/'download.json'));check('JSON download',json.loads((O/'download.json').read_text())['build']=='cybr-instrument-rebuild-2026-10-22')
  p.locator('#performance-close').click();p.evaluate('CYBR.setScale(.75)');p.wait_for_function('CYBR.report.resolution[0]===720');check('Scale reduction requires explicit selection',p.evaluate('CYBR.report.resolutionReason')=='explicit-user-selection');p.evaluate('CYBR.setScale(1)');p.wait_for_function('CYBR.report.resolution[0]===960')
  p.evaluate('window.loss=CYBR.test.gl.getExtension("WEBGL_lose_context");loss.loseContext()');p.wait_for_function('CYBR.report.lost');check('Loss preserves details and exposes reload',p.locator('#retry').is_visible() and p.evaluate('CYBR.report.lastContextLoss.memory.applicationGpuBytes')>0)
  p.locator('#visible-diagnostics').click();check('Diagnostics accessible during context loss',p.locator('#performance-report').is_visible());p.locator('#performance-close').click()
  p.wait_for_timeout(200);p.evaluate('loss.restoreContext()');p.wait_for_function('CYBR.report.ready&&!CYBR.report.lost',timeout=180000);shot=p.evaluate('CYBR.test.capture(0,1.5)');ev=image(shot,'restored.png');r=p.evaluate('CYBR.report');check('Restored context redraws and pauses animation',ev['colors']>200 and r['contextLosses']==1 and not r['playing'] and not r['bvhUploaded'] and p.evaluate('CYBR.test.gl.getError()')==0)
  p.add_style_tag(content='#portfolio{width:6000px!important;height:3000px!important;}');p.wait_for_function('CYBR.report.error.includes("budget")')
  check('Over-budget allocation rejected before resizing canvas',p.evaluate('CYBR.report.resolution')==[960,600] and not p.evaluate('CYBR.report.ready'))
  p.evaluate('CYBR.setScale(.5)');p.wait_for_function('CYBR.report.ready&&!CYBR.report.error');check('Explicit smaller scale recovers budget error',p.evaluate('CYBR.report.resolution')==[3000,1500] and p.evaluate('CYBR.report.resolutionReason')=='explicit-user-selection')
  p.add_style_tag(content='#portfolio{width:960px!important;height:600px!important;}');p.evaluate('CYBR.setScale(1)');p.wait_for_function('CYBR.report.resolution[0]===960')
  reports['desktop']=p.evaluate('CYBR.report');ctx.close();b.close()
  b=browser();ctx,p=start(b,'Native portrait',443,816,3.25,True,no_timer=True)
  p.add_style_tag(content='#portfolio{width:443.0769348144531px!important;height:816.6154174804688px!important;}');p.wait_for_function('CYBR.report.resolution[0]===1440&&CYBR.report.resolution[1]===2654')
  shot=p.evaluate('CYBR.test.capture(0,1.5)');ev=image(shot,'portrait-native.png');r=p.evaluate('CYBR.report');a=p.evaluate('alloc.snapshot()');check('Actual native 1440 by 2654 rendering',ev['size']==[1440,2654] and ev['colors']>200 and r['renderScale']==1,**ev)
  check('No GPU timer dependency',not r['gpuTimerAvailable'] and r['gpuFrameMs'] is None and r['frame']>0)
  check('Native targets plus bounded RGB edge history have expected sizes',r['memory']['parts']['sceneColor']+r['memory']['parts']['sceneDepth']==1440*2654*12 and r['memory']['renderTargetCount']==2 and r['antialiasing']['historyBytes']==1440*2654*3,attachmentBytes=1440*2654*12,edgeHistoryBytes=1440*2654*3)
  check('Native resource ledger matches GL intercepts',r['memory']['applicationGpuBytes']==a['textureBytes']+a['bufferBytes'],observed=a,reported=r['memory'])
  boxes={n:p.locator('#'+n).bounding_box() for n in ['live-mode','visible-diagnostics']};check('Touch controls fit viewport',all(x and x['height']>=44 and x['x']>=0 and x['x']+x['width']<=443.5 for x in boxes.values()),boxes=boxes)
  cdp=ctx.new_cdp_session(p);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':205,'y':490,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':205,'y':290,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});p.wait_for_function('CYBR.diagnostics.target>=1');check('Native touch swipe',p.evaluate('CYBR.diagnostics.target')>=1)
  p.locator('#visible-diagnostics').click();p.locator('#performance-panel').wait_for(state='visible');p.screenshot(path=str(O/'portrait-diagnostics.png'));check('Paused diagnostic does not label refinement as animation FPS','Animation paused' in p.locator('#performance-text').inner_text())
  check('Portrait diagnostics remains visible',p.locator('#performance-copy').is_visible() and p.locator('#performance-report').is_visible());p.locator('#performance-close').click()
  # Sequential completed readbacks are recorded only as software-rendering timings.
  times=[]
  for chapter in [0,2,4]:
   t=time.perf_counter();p.evaluate('ch=>CYBR.test.capture(ch,2)',chapter);times.append({'chapter':chapter,'completedCaptureWallMs':(time.perf_counter()-t)*1000})
  measurements['portraitSoftwareCaptures']=times
  reports['portrait']=p.evaluate('CYBR.report');ctx.close();b.close()
  b=browser();ctx,p=start(b,'No float color',640,400,no_float=True,no_timer=True);shot=p.evaluate('CYBR.test.capture(2,1.5)');ev=image(shot,'no-float.png');r=p.evaluate('CYBR.report');check('RGBM fallback renders without HDR color extension',not r['linearHDR'] and ev['colors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,**ev);reports['noFloat']=r;ctx.close();b.close()
except BaseException as exc:errors.append({'testHarness':str(exc),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
finally:
 x.terminate();check('No uncaught browser/harness errors',not errors,errors=errors);check('No external runtime asset requests',not requests,requests=requests)
 result={'build':'cybr-instrument-rebuild-2026-10-22','htmlSHA256':hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest(),'physicalAndroidTested':False,'sixtyFPSVerified':False,'visualRedesign':True,'visualAcceptance':'Human visual judgment; no numerical photorealism certificate','environment':'Portable Chromium; actual renderer identity is recorded in reports. Real native-size pixel readbacks, emulated touch. Not an Adreno performance measurement. Capture wall times include PNG serialization and readback, not GPU execution time.','checks':checks,'passed':sum(c['pass'] for c in checks),'total':len(checks),'errors':errors,'reports':reports,'measurements':measurements}
 (O/'test-report.json').write_text(json.dumps(result,indent=2));print('RESULT',result['passed'],'/',result['total'],flush=True)

if result["passed"] != result["total"]: raise SystemExit(1)
