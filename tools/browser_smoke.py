"""Bounded real browser check; no physical mobile performance claim."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"instrument-rebuild/studio"))
from browser_runtime import launch_browser
from playwright.sync_api import sync_playwright
from PIL import Image
p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=ROOT/"output/portable-smoke");a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True);results=[]
with sync_playwright() as pw:
 browser=launch_browser(pw);version=browser.version
 try:
  for name,width,height,touch in [("desktop",640,400,False),("touch-layout",390,844,True)]:
   context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1,has_touch=touch,is_mobile=touch,reduced_motion="reduce")
   page=context.new_page();errors=[];remote=[]
   page.on("pageerror",lambda e:errors.append(str(e)));page.on("request",lambda r:remote.append(r.url) if r.url.startswith(("http://","https://")) else None)
   page.goto((ROOT/"instrument-rebuild/dist/index.html").as_uri(),timeout=120000);page.wait_for_function("window.CYBR && (CYBR.report.ready || CYBR.report.error)",timeout=120000)
   report=page.evaluate("CYBR.report")
   if not report["ready"]:raise RuntimeError(report["error"])
   page.wait_for_function("CYBR.report.antialiasing.samples===8",timeout=120000)
   shot=a.output/(name+".png");page.screenshot(path=str(shot))
   pixels=Image.open(shot).convert("RGB").resize((80,50)).tobytes();colors=len({pixels[i:i+3] for i in range(0,len(pixels),3)})
   page.keyboard.press("ArrowRight");page.wait_for_function("CYBR.diagnostics.target===1",timeout=30000);bounds=page.locator("#visible-diagnostics").bounding_box()
   entry={"name":name,"ready":report["ready"],"gpu":report["gpu"],"resolution":report["resolution"],"playing":report["playing"],"colors":colors,"gl_error":page.evaluate("CYBR.test.gl.getError()"),"keyboard_navigation":page.evaluate("CYBR.diagnostics.target")==1,"diagnostics_in_view":bool(bounds and bounds["x"]>=0 and bounds["x"]+bounds["width"]<=width+1),"uncaught_errors":errors,"external_requests":remote,"screenshot":shot.name}
   entry["passed"]=bool(entry["ready"] and colors>100 and entry["gl_error"]==0 and entry["keyboard_navigation"] and entry["diagnostics_in_view"] and not errors and not remote and not entry["playing"]);results.append(entry);context.close()
 finally:browser.close()
output={"browser":version,"physical_mobile_test":False,"scope":"Bounded startup, real pixels, paused raster refinement, navigation and touch viewport layout.","results":results}
(a.output/"report.json").write_text(json.dumps(output,indent=2),encoding="utf-8");print(json.dumps(output,indent=2))
if not all(x["passed"] for x in results):raise SystemExit(1)
