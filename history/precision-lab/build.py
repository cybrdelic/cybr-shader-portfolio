from pathlib import Path
import json,base64,gzip,hashlib
R=Path(__file__).parent
s=(R/'host.html').read_text()
shaders={p.name:p.read_text() for p in sorted((R/'shaders').glob('*'))}
info=json.loads((R/'geometry/packed.json').read_text())
original=(R/'reference/original-ray-traced.html').read_bytes()
s=s.replace('__SHADERS__',json.dumps(shaders).replace('</','<\\/')).replace('__GEOMETRY_INFO__',json.dumps(info)).replace('__GEOMETRY_GZIP__',base64.b64encode((R/'geometry/mesh.bin.gz').read_bytes()).decode()).replace('__ORIGINAL_GZIP__',base64.b64encode(gzip.compress(original,mtime=0)).decode())
s=s.replace('__ENV_INFO__',json.dumps(json.loads((R/'studio/environment.json').read_text()))).replace('__ENV_GZIP__',base64.b64encode((R/'studio/environment.bin.gz').read_bytes()).decode())
s=s.replace('__ACCESSIBLE_NAV__',''.join(f'<button data-chapter="{i}">{n}</button>' for i,n in enumerate(['Assembly','Light','Geometry','Scenes','Elements','Materials','Forest','About'])))
s=s.replace('__PROBE_INFO__',json.dumps(json.loads((R/'studio/probes.json').read_text()))).replace('__PROBE_GZIP__',base64.b64encode((R/'studio/probes.bin.gz').read_bytes()).decode())
s=s.replace('__IRR_INFO__',json.dumps(json.loads((R/'studio/irradiance.json').read_text()))).replace('__IRR_GZIP__',base64.b64encode((R/'studio/irradiance.bin.gz').read_bytes()).decode())
s=s.replace('__SURFACE_INFO__', (R/'materials/maps.json').read_text()).replace('__SURFACE_COLOR__',base64.b64encode((R/'materials/color.rgba.gz').read_bytes()).decode()).replace('__SURFACE_NORMAL__',base64.b64encode((R/'materials/normal.rgba.gz').read_bytes()).decode())
s=s.replace('__BVH_INFO__',(R/'geometry/optical-bvh.json').read_text()).replace('__BVH_GZIP__',base64.b64encode((R/'geometry/optical-bvh.bin.gz').read_bytes()).decode())
out=R/'dist/index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s)
(R/'build-info.json').write_text(json.dumps({'file':out.name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'geometry':info},indent=2))
print(out,out.stat().st_size)
