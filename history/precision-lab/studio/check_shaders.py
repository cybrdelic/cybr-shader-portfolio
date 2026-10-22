"""Compile/link the actual current GLSL independently of scene asset loading."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess,os,time,json
R=Path(__file__).resolve().parent.parent
subprocess.run(['python',str(R/'studio/build_progressive_shader.py')],check=True)
x=subprocess.Popen(['Xvfb',':156','-screen','0','800x600x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
os.environ['DISPLAY']=':156';time.sleep(.2)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=gl','--ignore-gpu-blocklist'])
  p=b.new_page();p.set_content('<canvas id="c"></canvas>');results=[]
  for v,f in [('scene.vert','scene.frag'),('screen.vert','screen.frag'),('screen.vert','finish.frag'),('screen.vert','progressive.frag'),('screen.vert','denoise.frag')]:
   data={'v':(R/'shaders'/v).read_text(),'f':(R/'shaders'/f).read_text()}
   result=p.evaluate('''s=>{let gl=document.querySelector('canvas').getContext('webgl2');let logs=[];function shader(type,src){let sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);logs.push(gl.getShaderInfoLog(sh));return sh;}let prog=gl.createProgram();gl.attachShader(prog,shader(gl.VERTEX_SHADER,s.v));gl.attachShader(prog,shader(gl.FRAGMENT_SHADER,s.f));gl.linkProgram(prog);return {pass:gl.getProgramParameter(prog,gl.LINK_STATUS),logs:[...logs,gl.getProgramInfoLog(prog)]};}''',data)
   result['program']=f;results.append(result);print(json.dumps(result),flush=True)
  (R/'verification/shader-compile.json').write_text(json.dumps(results,indent=2));b.close()
finally:x.terminate()
