// Event-level checks of the actual self-contained host script.
// This harness exercises navigation, export, context loss, picking and idle behavior.
// Shader rendering is verified separately with native EGL/GLES3.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'host.html'), 'utf8');
const source = '// CYBR — native test\nvoid main(){fragColor=vec4(1);}\n';
const hostScript = html.match(/<script>([\s\S]*?)<\/script>/)[1].replace('__FRAGMENT_SOURCE__', source);
let checks = 0;
function test(name, body) { body(); checks++; console.log('PASS ' + name); }
function boot({ width=1280, height=800, query='', reduced=false, supported=true, linked=true } = {}) {
  let now=0, sequence=0, pickId=0;
  const raf=new Map(), timers=new Map(), uniforms=new Map(), draws=[], links=[], blobs=[];
  class Element {
    constructor(id='') { this.id=id; this.tagName='BUTTON'; this.hidden=false; this.textContent=''; this.dataset={}; this.events=new Map(); this.attrs={}; this.style={}; this.classList={add(){}}; }
    addEventListener(event, callback) { if(!this.events.has(event))this.events.set(event,[]);this.events.get(event).push(callback); }
    dispatch(event, values={}) { const e={target:this,preventDefault(){this.defaultPrevented=true;},...values}; for(const fn of this.events.get(event)||[])fn(e);return e; }
    setAttribute(k,v){this.attrs[k]=v;} removeAttribute(k){delete this.attrs[k];}
    appendChild(){ } remove(){ }
    click(){links.push({href:this.href,download:this.download});this.dispatch('click');}
    focus(){ }
  }
  const elements=new Map();
  const ids=[...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
  for(const id of ids)elements.set(id,new Element(id));
  const chapterButtons=Array.from({length:8},(_,i)=>{const e=new Element();e.dataset.chapter=String(i);return e;});
  const canvas=elements.get('portfolio');
  canvas.tagName='CANVAS';canvas.clientWidth=width;canvas.clientHeight=height;
  canvas.getBoundingClientRect=()=>({left:0,top:0,right:width,bottom:height,width,height});
  let capture=null;
  canvas.setPointerCapture=id=>{capture=id;};canvas.hasPointerCapture=id=>capture===id;
  canvas.releasePointerCapture=()=>{capture=null;};
  canvas.toBlob=callback=>callback(new TestBlob(['png'],{type:'image/png'}));
  const gl={
    VERTEX_SHADER:1,FRAGMENT_SHADER:2,LINK_STATUS:3,DEPTH_TEST:4,BLEND:5,CULL_FACE:6,DITHER:7,TRIANGLES:8,RGBA:9,UNSIGNED_BYTE:10,
    createShader:()=>({}),shaderSource(){},compileShader(){},createProgram:()=>({}),attachShader(){},linkProgram(){},
    getExtension:()=>null,getProgramParameter:()=>linked,getShaderInfoLog:()=>linked?'':'intentional compile test',getProgramInfoLog:()=>'',
    deleteShader(){},deleteProgram(){},detachShader(){},useProgram(){},createVertexArray:()=>({}),deleteVertexArray(){},bindVertexArray(){},disable(){},viewport(){},
    getUniformLocation:(program,name)=>name,
    uniform1f:(name,x)=>uniforms.set(name,x),uniform1i:(name,x)=>uniforms.set(name,x),
    uniform2f:(name,x,y)=>uniforms.set(name,[x,y]),uniform4f:(name,...value)=>uniforms.set(name,value),
    drawArrays:()=>draws.push({pick:uniforms.get('u_pick'),chapter:uniforms.get('u_chapter')}),
    readPixels:(x,y,w,h,format,type,array)=>{array[0]=pickId;array[3]=255;}
  };
  canvas.getContext=()=>supported?gl:null;
  const document=new Element('document');document.tagName='DOCUMENT';document.hidden=false;
  document.body=new Element('body');document.getElementById=id=>elements.get(id);document.querySelectorAll=()=>chapterButtons;
  document.createElement=tag=>{const e=new Element();e.tagName=tag.toUpperCase();return e;};
  document.documentElement=new Element('html');document.documentElement.requestFullscreen=async()=>{};
  const media=new Element();media.matches=reduced;
  const window=new Element('window');window.devicePixelRatio=1;window.matchMedia=q=>q.includes('reduced')?media:{matches:width<760};
  const location={search:query,pathname:'/index.html',hash:''};
  const history={replaceState:(a,b,value)=>{location.hash=value.includes('#')?'#'+value.split('#')[1]:'';}};
  class TestBlob { constructor(parts,opts) {this.parts=parts;this.type=opts.type;this.text=parts.join('');} }
  const context={document,window,location,history,URLSearchParams,TextEncoder,Blob:TestBlob,Uint8Array,Math,Number,Object,Promise,Error,Array,String,Boolean,
    URL:{createObjectURL:blob=>{blobs.push(blob);return 'blob:local/'+blobs.length;},revokeObjectURL(){}},
    btoa:binary=>Buffer.from(binary,'binary').toString('base64'),
    performance:{now:()=>now},
    requestAnimationFrame:fn=>{const id=++sequence;raf.set(id,fn);return id;},cancelAnimationFrame:id=>raf.delete(id),
    setTimeout:(fn,delay)=>{const id=++sequence;timers.set(id,{fn,at:now+delay});return id;},clearTimeout:id=>timers.delete(id),
    ResizeObserver:class{observe(){}},console
  };
  vm.runInNewContext(hostScript,context,{timeout:1000});
  function frame(dt=1000/60) {now+=dt;const list=[...raf.values()];raf.clear();for(const fn of list)fn(now);}
  function frames(n,dt) {for(let i=0;i<n;i++)frame(dt);}
  function runTimers(dt) {now+=dt;for(const[id,t]of[...timers])if(t.at<=now){timers.delete(id);t.fn();}}
  function key(key,tagName='CANVAS') {return document.dispatch('keydown',{key,altKey:false,ctrlKey:false,metaKey:false,target:{tagName}});}
  function point(x,y) {return {clientX:x*height/900,clientY:height-y*height/900,isPrimary:true,button:0,pointerId:1,pointerType:'mouse'};}
  function tap(x,y) {const p=point(x,y);canvas.dispatch('pointerdown',p);canvas.dispatch('pointerup',p);}
  const api={context,window,canvas,elements,document,chapterButtons,draws,links,blobs,uniforms,frames,frame,runTimers,key,point,tap,raf,media,
    get state(){return window.CYBR.diagnostics;},setPick(value){pickId=value;},logicalWidth:width*900/height};
  return api;
}

test('eight semantic chapter controls and only one build marker',()=>{
  assert.equal([...html.matchAll(/data-chapter="\d"/g)].length,8);
  assert.equal([...html.matchAll(/__FRAGMENT_SOURCE__/g)].length,1);
  const h=boot();assert.equal(h.state.ready,true);assert.equal(h.links.length,0);assert.equal(h.blobs.length,0);
});
test('keyboard chapter boundaries select all eight chapters',()=>{
  const h=boot();h.key('8');assert.equal(h.state.target,7);h.frames(100);assert.equal(h.state.chapter,7);
  h.key('ArrowRight');assert.equal(h.state.target,7);h.key('Home');assert.equal(h.state.target,0);
  h.key('ArrowLeft');assert.equal(h.state.target,0);h.key('End');assert.equal(h.state.target,7);
});
test('a small deliberate wheel gesture snaps to the next chapter',()=>{
  const h=boot();h.canvas.dispatch('wheel',{deltaY:70,deltaX:0,deltaMode:0});
  assert.ok(h.state.target>0&&h.state.target<1);h.runTimers(300);assert.equal(h.state.target,1);
});
test('every canvas navigation cell maps to its matching chapter',()=>{
  const h=boot();const cell=(h.logicalWidth-56)/8;
  for(let i=0;i<8;i++){h.tap(28+(i+.5)*cell,42);assert.equal(h.state.target,i);}
});
test('touch travel updates continuously before release, then snaps',()=>{
  const h=boot({width:405,height:900});
  const down={clientX:200,clientY:450,pointerType:'touch',isPrimary:true,button:0,pointerId:1};
  h.canvas.dispatch('pointerdown',down);h.canvas.dispatch('pointermove',{...down,clientY:300});
  assert.ok(h.state.target>0&&h.state.target<1);
  h.canvas.dispatch('pointerup',{...down,clientY:300});assert.equal(h.state.target,1);
});
test('touch cancellation returns to a chapter stop',()=>{
  const h=boot({width:405,height:900});const down={clientX:200,clientY:450,pointerType:'touch',isPrimary:true,button:0,pointerId:1};
  h.canvas.dispatch('pointerdown',down);h.canvas.dispatch('pointermove',{...down,clientY:340});h.canvas.dispatch('pointercancel');
  assert.equal(h.state.target,Math.round(h.state.target));
});
test('mouse dragging orbits without advancing chapters',()=>{
  const h=boot();const down=h.point(700,500);h.canvas.dispatch('pointerdown',down);h.canvas.dispatch('pointermove',{...down,clientX:down.clientX+120,clientY:down.clientY-40});
  assert.ok(h.state.drag[0]>0);assert.ok(h.state.drag[1]>0);assert.equal(h.state.target,0);
  h.canvas.dispatch('pointerup',{...down,clientX:down.clientX+120,clientY:down.clientY-40});
});
test('GLSL picking selects every project and restores shaded drawing',()=>{
  const h=boot();h.frame();for(let id=1;id<=6;id++){h.setPick(id);h.tap(750,500);assert.equal(h.state.target,id);assert.equal(h.draws.at(-2).pick,1);assert.equal(h.draws.at(-1).pick,0);}
});
test('core and maker plate picking select Assembly and About',()=>{
  const h=boot();h.frame();h.setPick(8);h.tap(750,500);assert.equal(h.state.target,7);h.setPick(7);h.tap(750,500);assert.equal(h.state.target,0);
  h.setPick(0);h.tap(750,500);assert.equal(h.state.target,0);
});
test('Source canvas control downloads the exact shader locally',()=>{
  const h=boot();h.tap(h.logicalWidth-70,850);
  assert.equal(h.links.at(-1).download,'cybr-computational-instrument.frag');assert.equal(h.blobs.at(-1).text,source);
  assert.ok(h.links.every(link=>link.href.startsWith('blob:')));
});
test('FragCoord source URL is created only by explicit editor action',()=>{
  const h=boot();assert.equal(h.links.length,0);h.key('e');const url=h.links.at(-1).href;
  assert.ok(url.startsWith('https://fragcoord.xyz/#code='));
  assert.equal(Buffer.from(url.split('#code=')[1].replace(/-/g,'+').replace(/_/g,'/'),'base64').toString('utf8'),source);
});
test('About links use the displayed mobile hit regions',()=>{
  const h=boot({width:405,height:900,reduced:true});h.key('8');h.tap(60,125);assert.equal(h.links.at(-1).href,'https://github.com/cybrdelic');
  h.tap(280,125);assert.equal(h.links.at(-1).href,'https://x.com/cybrdelic');
});
test('quality changes pixel budget and rendering quality together',()=>{
  const h=boot();h.frame();const before=h.state.resolution[0]*h.state.resolution[1];h.key('q');h.frame();
  assert.equal(h.state.quality,'High detail');assert.ok(h.state.resolution[0]*h.state.resolution[1]>before);assert.equal(h.uniforms.get('u_quality'),2);
  h.key('q');h.frame();assert.equal(h.uniforms.get('u_quality'),0);
});
test('paused settled canvases become idle and redraw on demand',()=>{
  const h=boot();h.frames(4);h.key(' ');h.frames(3);const elapsed=h.uniforms.get('u_time');assert.equal(h.raf.size,0);
  h.frames(4);assert.equal(h.uniforms.get('u_time'),elapsed);
  h.canvas.dispatch('pointermove',h.point(500,600));assert.equal(h.raf.size,1);h.frame();assert.equal(h.raf.size,0);
  h.key(' ');assert.equal(h.raf.size,1);
});
test('reduced motion begins paused and changes chapters immediately',()=>{
  const h=boot({reduced:true});assert.equal(h.state.playing,false);h.key('6');assert.equal(h.state.chapter,5);h.frames(3);assert.equal(h.raf.size,0);
});
test('context loss stops rendering while preserving source export',()=>{
  const h=boot();h.frame();h.canvas.dispatch('webglcontextlost');assert.equal(h.state.lost,true);assert.equal(h.state.ready,false);assert.equal(h.raf.size,0);
  h.elements.get('fallback-download').dispatch('click');assert.equal(h.blobs.at(-1).text,source);
  h.canvas.dispatch('webglcontextrestored');assert.equal(h.state.ready,true);h.frame();assert.equal(h.state.lost,false);
});
test('unsupported WebGL leaves a usable source-download fallback',()=>{
  const h=boot({supported:false});assert.equal(h.state.ready,false);assert.equal(h.elements.get('status').hidden,false);
  h.elements.get('fallback-download').dispatch('click');assert.equal(h.blobs.at(-1).text,source);
});
test('compile errors show a fallback and preserve the exact source',()=>{
  const h=boot({linked:false});assert.equal(h.state.ready,false);assert.equal(h.elements.get('status-actions').hidden,false);
  h.elements.get('fallback-download').dispatch('click');assert.equal(h.blobs.at(-1).text,source);
});
test('Space on a semantic button does not toggle animation twice',()=>{
  const h=boot();h.key(' ','BUTTON');assert.equal(h.state.playing,true);
});
test('tour reaches the eighth chapter and stops without wrapping',()=>{
  const h=boot();h.key('t');h.frames(600,100);assert.equal(h.state.target,7);assert.equal(h.state.tour,false);
});
test('still query and source share behavior remain local',()=>{
  const h=boot({query:'?still=1&chapter=6&time=3'});h.frame();assert.equal(h.state.playing,false);assert.equal(h.state.chapter,6);assert.equal(h.uniforms.get('u_time'),3);
  h.key('s');assert.equal(h.blobs.at(-1).text,source);assert.equal(h.links.at(-1).download,'cybr-computational-instrument.frag');
});
console.log(`${checks} host behavior checks passed.`);
