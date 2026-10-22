from pathlib import Path
import json,base64,gzip,hashlib
R=Path(__file__).parent;s=(R/'host.html').read_text()
for key,name in [('GEOMETRY_INFO','geometry/packed.json'),('ENV_INFO','studio/environment.json'),('PROBE_INFO','studio/probes.json'),('IRR_INFO','studio/irradiance.json'),('SURFACE_INFO','materials/maps.json'),('FLAME_INFO','materials/flame.json')]:
 s=s.replace('__'+key+'__',json.dumps(json.loads((R/name).read_text())))
for key,name in [('GEOMETRY_GZIP','geometry/mesh.bin.gz'),('ENV_GZIP','studio/environment.bin.gz'),('PROBE_GZIP','studio/probes.bin.gz'),('IRR_GZIP','studio/irradiance.bin.gz'),('SURFACE_COLOR','materials/color.rgba.gz'),('SURFACE_NORMAL','materials/normal.rgba.gz'),('NOISE_GZIP','materials/noise.r8.gz'),('FLAME_GZIP','materials/flame.rg8.gz')]:
 s=s.replace('__'+key+'__',base64.b64encode((R/name).read_bytes()).decode())
s=s.replace('__ORIGINAL_GZIP__',base64.b64encode(gzip.compress((R/'reference/original-ray-traced.html').read_bytes(),mtime=0)).decode())
s=s.replace('__SHADERS__',json.dumps({p.name:p.read_text() for p in sorted((R/'shaders').iterdir())}).replace('</',r'<\/'))
s=s.replace('__ACCESSIBLE_NAV__',''.join(f'<button data-chapter="{i}">{n}</button>' for i,n in enumerate(['Assembly','Light','Geometry','Scenes','Elements','Materials','Forest','About'])))
out=R/'dist/index.html';out.parent.mkdir(exist_ok=True);out.write_text(s)
(R/'build-info.json').write_text(json.dumps({'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2));print(out,out.stat().st_size)
