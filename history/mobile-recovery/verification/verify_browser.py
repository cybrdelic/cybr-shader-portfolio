"""Real browser checks. Does not certify physical-device stability, FPS or realism."""
from pathlib import Path
import base64,gzip,hashlib,io,json,os,subprocess,time,traceback
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];O=R/'verification';checks=[];errors=[];requests=[];reports={}

def save_progress():
 d={'build':'cybr-mobile-recovery-2026-10-22-r1','checks':checks,'reports':reports,'errors':errors,'requests':requests,'physicalAndroidTested':False,'sixtyFPSVerified':False,'photorealismClaimed':False,'environment':'Actual Chromium WebGL2 through ANGLE/Mesa llvmpipe; touch and pixel density are emulated. Local file/http navigations are blocked by this container, so the exact standalone HTML is incrementally parsed with document.write. No model or pixels are substituted.','passed':sum(c['pass'] for c in checks),'total':len(checks),'htmlSHA256':hashlib.sha256((R/'dist/index.html').read_bytes()).hexdigest()}
 (O/'test-report.json').write_text(json.dumps(d,indent=2));return d

def check(name,condition,**evidence):
 checks.append({'name':name,'pass':bool(condition),**evidence});print(json.dumps(checks[-1]),flush=True);save_progress()

def load(page,path):
 page.set_content('<!doctype html><html><head></head><body></body></html>');page.evaluate('document.open()')
 with Path(path).open() as f:
  while s:=f.read(512*1024):page.evaluate('(s)=>document.write(s)',s)
 page.evaluate('document.close()')

def image(data,name):
 raw=base64.b64decode(data.split(',')[1]);(O/name).write_bytes(raw)
 im=Image.open(io.BytesIO(raw)).convert('RGB');a=np.array(im.resize((96,64)))
 return {'size':list(im.size),'sampleColors':len(np.unique(a.reshape(-1,3),axis=0)),'channelStd':float(a.std()),'sha256':hashlib.sha256(raw).hexdigest()}

info=json.loads((R/'geometry/packed.json').read_text());preserved=json.loads((O/'preserved-source-hashes.json').read_text())
check('Mesh cache byte-for-byte unchanged',hashlib.sha256(gzip.decompress((R/'geometry/mesh.bin.gz').read_bytes())).hexdigest()==info['sha256'],sha256=info['sha256'],triangles=info['triangles'])
for f in ['materials/color.rgba.gz','materials/normal.rgba.gz','studio/irradiance.bin.gz']:
 check('Unmodified '+f,hashlib.sha256((R/f).read_bytes()).hexdigest()==preserved[f])
shaders='\n'.join(p.read_text() for p in (R/'shaders').iterdir())
check('No compiled scene-ray hierarchy or progressive program',not any(x in shaders for x in ['u_bvh_nodes','traceIncidentRadiance','u_history','u_guide_history']),compiledPrograms=2)
x=subprocess.Popen(['Xvfb',':159','-screen','0','2800x3000x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.environ['DISPLAY']=':159';time.sleep(.4)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  def page_for(label,width,height,dpr=1,touch=False,no_float=False,no_timer=False):
   ctx=b.new_context(viewport={'width':width,'height':height},device_scale_factor=dpr,has_touch=touch,is_mobile=touch,reduced_motion='reduce',accept_downloads=True)
   p=ctx.new_page();p.set_default_timeout(120000)
   p.on('pageerror',lambda e:errors.append({'scope':label,'error':str(e)}))
   p.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http://','https://')) else None)
   if no_float or no_timer:
    p.evaluate('''({noFloat,noTimer})=>{const original=WebGL2RenderingContext.prototype.getExtension;WebGL2RenderingContext.prototype.getExtension=function(name){if((noFloat&&name==='EXT_color_buffer_float')||(noTimer&&name==='EXT_disjoint_timer_query_webgl2'))return null;return original.call(this,name);};}''',{'noFloat':no_float,'noTimer':no_timer})
   load(p,R/'dist/index.html');p.wait_for_function('window.CYBR&&(CYBR.report.frame>0||CYBR.report.error)',timeout=240000)
   rep=p.evaluate('CYBR.report');check(label+' actual WebGL2 startup',rep['ready'] and not rep['error'],renderer=rep['gpu'],error=rep['error'])
   if not rep['ready']:raise RuntimeError(label+' could not render: '+rep['error'])
   return ctx,p
  ctx,p=page_for('Desktop',960,600)
  rep=p.evaluate('CYBR.report');check('Safe native defaults; Studio absent and animation opt-in',rep['renderScale']==1 and not rep['playing'] and not rep['progressiveStudio']['available'] and not rep['secondaryRays']['hierarchyAllocated'],memory=rep['memory'],passes=rep['passes'])
  for ch in range(8):
   ev=image(p.evaluate('(ch)=>CYBR.test.capture(ch,0)',ch),f'chapter-{ch}.png');glerr=p.evaluate('CYBR.test.gl.getError()')
   check('Actual raster chapter '+str(ch),ev['size']==[960,600] and ev['sampleColors']>200 and glerr==0,**ev,glError=glerr)
  p.evaluate('CYBR.go(0)');p.wait_for_function('CYBR.diagnostics.chapter===0');p.locator('#portfolio').focus();p.keyboard.press('ArrowRight');p.wait_for_function('CYBR.diagnostics.chapter===1');check('Keyboard navigation',p.evaluate('CYBR.diagnostics.target')==1)
  p.evaluate('CYBR.go(0)');p.wait_for_function('CYBR.diagnostics.chapter===0');p.locator('#portfolio').dispatch_event('wheel',{'deltaY':160,'deltaMode':0});p.wait_for_function('CYBR.diagnostics.chapter===1');check('Wheel navigation and snap',p.evaluate('CYBR.diagnostics.target')==1)
  p.wait_for_function('CYBR.report.pendingCompletionFences===0&&CYBR.report.pendingTimingQueries===0');count=p.evaluate('CYBR.report.submittedFrames');p.wait_for_timeout(550);check('No continuous GPU rendering while idle',p.evaluate('CYBR.report.submittedFrames')==count,submittedFrames=count)
  p.locator('#visible-diagnostics').click();r=json.loads(p.locator('#performance-report').input_value());check('Visible diagnostic report identifies exact active workload',r['diagnosticsVisible'] and r['progressiveStudio']['available']==False and r['memory']['knownPayloadBytes']>0)
  p.evaluate("()=>{Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('test denial'))},configurable:true});document.execCommand=()=>false;}")
  p.locator('#performance-copy').click();p.wait_for_function('document.getElementById("copy-result").textContent.includes("selected")');sel=p.evaluate('(()=>{const t=document.getElementById("performance-report");return [t.selectionStart,t.selectionEnd,t.value.length]})()');check('Denied clipboard selects the complete report',sel[0]==0 and sel[1]==sel[2])
  with p.expect_download() as dl:p.locator('#performance-download').click()
  dl.value.save_as(str(O/'downloaded-report.json'));check('JSON diagnostic download',json.loads((O/'downloaded-report.json').read_text())['build']=='cybr-mobile-recovery-2026-10-22-r1')
  p.locator('#performance-close').click()
  base=p.evaluate('CYBR.report.memory');p.evaluate('window.loss=CYBR.test.gl.getExtension("WEBGL_lose_context");loss.loseContext()');p.wait_for_function('CYBR.report.lost');lost=p.evaluate('CYBR.report')
  check('Context loss preserves useful failure snapshot and exposes restart',not lost['ready'] and lost['lastFailure']['knownPayloadBytes']==base['knownPayloadBytes'] and p.locator('#retry').is_visible(),lastFailure=lost['lastFailure'])
  p.locator('#visible-diagnostics').click();r=json.loads(p.locator('#performance-report').input_value());check('Diagnostics stays usable during context loss',r['lost'] and r['contextLosses']==1 and r['memory']['knownPayloadBytes']==0)
  p.locator('#performance-close').click();p.wait_for_timeout(150);p.evaluate('loss.restoreContext()');p.wait_for_function('CYBR.report.ready&&CYBR.report.frame>0',timeout=240000)
  ev=image(p.evaluate('CYBR.test.capture(0,0)'),'restored-assembly.png');after=p.evaluate('CYBR.report');check('Browser restoration rebuilds native resources without allocation growth',after['memory']['knownPayloadBytes']==base['knownPayloadBytes'] and after['memory']['objectCount']==base['objectCount'] and ev['sampleColors']>200 and not after['playing'],memoryBefore=base['knownPayloadBytes'],memoryAfter=after['memory']['knownPayloadBytes'])
  p.evaluate('CYBR.test.gl.getExtension("WEBGL_lose_context").loseContext()');p.wait_for_function('CYBR.report.lost');p.locator('#retry').click();p.wait_for_function('CYBR.report.ready&&CYBR.report.frame>0',timeout=240000)
  ev=image(p.evaluate('CYBR.test.capture(1,0)'),'manual-restart-light.png');after=p.evaluate('CYBR.report');check('Manual fresh-canvas restart after context loss',after['manualRestarts']==1 and not after['lost'] and ev['sampleColors']>200 and after['memory']['knownPayloadBytes']==base['knownPayloadBytes'])
  check('No GL error after loss, restore and restart',p.evaluate('CYBR.test.gl.getError()')==0);reports['desktop']=after;save_progress();ctx.close()
  ctx,p=page_for('Native portrait',443,816,3.25,True,no_timer=True)
  p.add_style_tag(content='#portfolio{width:443.0769348144531px!important;height:816.6154174804688px!important;}');p.wait_for_function('CYBR.report.resolution[0]===1440&&CYBR.report.resolution[1]===2654')
  rep=p.evaluate('CYBR.report');expected=json.loads((O/'allocation-audit.json').read_text())['newPayloadBytes'];ev=image(p.evaluate('CYBR.test.capture(0,0)'),'portrait-native.png')
  check('Exact user buffer size with unchanged native pixel density',ev['size']==[1440,2654] and rep['renderScale']==1 and not rep['adaptiveResolution'],**ev)
  check('Native allocation ledger matches byte-level audit',rep['memory']['knownPayloadBytes']==expected,expectedBytes=expected,actualBytes=rep['memory']['knownPayloadBytes'],MiB=rep['memory']['knownPayloadMiB'])
  rects={n:p.locator('#'+n).bounding_box() for n in ['play-button','visible-diagnostics']};check('Touch controls visible and at least 44px tall',all(r and r['height']>=44 and r['x']>=0 and r['x']+r['width']<=443.5 for r in rects.values()),rects=rects)
  cdp=ctx.new_cdp_session(p);cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':206,'y':480,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':206,'y':275,'id':1}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});p.wait_for_function('CYBR.diagnostics.target>=1');check('Native touch swipe navigates',p.evaluate('CYBR.diagnostics.target')>=1,resolution=p.evaluate('CYBR.report.resolution'))
  p.wait_for_function('CYBR.report.pendingCompletionFences===0');p.evaluate('CYBR.setScale(.75)');p.wait_for_function('CYBR.report.resolution[0]===1080');scaled=p.evaluate('CYBR.report');check('Lower resolution only through explicit choice',scaled['resolutionReason']=='explicit-user-selection' and scaled['resolution']==[1080,1991])
  p.evaluate('CYBR.setScale(1)');p.wait_for_function('CYBR.report.resolution[0]===1440');rep=p.evaluate('CYBR.report');check('Return to native releases old render targets',rep['memory']['knownPayloadBytes']==expected and rep['resolution']==[1440,2654],objectCount=rep['memory']['objectCount'])
  # Exercise orientation/resize without accumulating old targets. Same full-detail asset payload.
  for w,h in [(816.6154174804688,443.0769348144531),(400,700),(443.0769348144531,816.6154174804688)]:
   p.evaluate('([w,h])=>{const c=document.getElementById("portfolio");c.style.setProperty("width",w+"px","important");c.style.setProperty("height",h+"px","important");}',[w,h]);ww=int(w*3.25+.5);hh=int(h*3.25+.5)
   p.wait_for_function('([w,h])=>CYBR.report.resolution[0]===w&&CYBR.report.resolution[1]===h',arg=[ww,hh]);p.wait_for_function('CYBR.report.pendingCompletionFences===0')
  rep=p.evaluate('CYBR.report');check('Repeated native reallocations retain one framebuffer only',rep['memory']['knownPayloadBytes']==expected and rep['renderTarget']['offscreenTargets']==1 and rep['memory']['objectCount']==after['memory']['objectCount'],memory=rep['memory'])
  # Explicit animation makes submission/completion rates meaningful. Not a mobile benchmark.
  p.evaluate('CYBR.play()');p.wait_for_function('CYBR.report.submittedFrames>=15',timeout=180000);p.evaluate('CYBR.pause()');p.wait_for_function('CYBR.report.pendingCompletionFences===0');rep=p.evaluate('CYBR.report');check('No-timer backend still submits and completes real frames',not rep['gpuTimerAvailable'] and rep['completedFrames']>=10 and rep['gpuFrameMs'] is None,submitted=rep['submittedFrames'],completed=rep['completedFrames'],observedSoftwareFPS=rep['completedFPS'])
  p.locator('#visible-diagnostics').click();check('Portrait diagnostics opens without shader hit-testing',p.locator('#performance-report').is_visible());p.screenshot(path=str(O/'portrait-diagnostics.png'));p.locator('#performance-close').click();
  p.evaluate('CYBR.test.gl.getExtension("WEBGL_lose_context").loseContext()');p.wait_for_function('CYBR.report.lost');p.locator('#retry').click();p.wait_for_function('CYBR.report.ready&&CYBR.report.frame>0',timeout=240000);
  native_recovery=p.evaluate('CYBR.report');check('Fresh-canvas recovery at exact native portrait resolution',native_recovery['resolution']==[1440,2654] and native_recovery['memory']['knownPayloadBytes']==expected and p.evaluate('CYBR.test.gl.getError()')==0);
  reports['nativePortrait']=native_recovery;save_progress();ctx.close()
  ctx,p=page_for('No float color support',640,400,no_float=True,no_timer=True);rep=p.evaluate('CYBR.report');ev=image(p.evaluate('CYBR.test.capture(2,0)'),'rgbm-fallback.png');check('RGBM fallback remains native and usable',rep['renderTarget']['format']=='RGBA8 RGBM' and rep['resolution']==[640,400] and ev['sampleColors']>200 and p.evaluate('CYBR.test.gl.getError()')==0,**ev);reports['fallback']=rep;ctx.close();b.close()
except BaseException as exc:
 errors.append({'testHarness':str(exc),'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
finally:
 x.terminate();check('No uncaught JavaScript or test harness errors',not errors,errors=errors);check('No external runtime requests',not requests,requests=requests)
 d=save_progress();print('RESULT',d['passed'],'/',d['total'],flush=True)
