"""Build the standalone offline browser artifact. Python 3 standard library only."""
from pathlib import Path
import base64, gzip, hashlib, json
ROOT = Path(__file__).resolve().parent
html = (ROOT / 'host.html').read_text(encoding='utf-8')
shaders = {p.name: p.read_text(encoding='utf-8') for p in sorted((ROOT / 'shaders').iterdir())}
assert len(shaders) == 4
for shader in shaders.values():
    assert 'u_bvh_nodes' not in shader and 'traceIncidentRadiance' not in shader
values = {
    'SHADERS': json.dumps(shaders).replace('</', '<\\/'),
    'ACCESSIBLE_NAV': ''.join(f'<button data-chapter="{i}">{name}</button>' for i, name in enumerate(['Assembly','Light','Geometry','Scenes','Elements','Materials','Forest','About'])),
}
for key, path in [
    ('GEOMETRY_INFO', 'geometry/packed.json'), ('ENV_INFO', 'studio/environment.json'),
    ('PROBE_INFO', 'studio/probes.json'), ('IRR_INFO', 'studio/irradiance.json'), ('SURFACE_INFO', 'materials/maps.json')]:
    values[key] = (ROOT/path).read_text(encoding='utf-8')
for key, path in [
    ('GEOMETRY_GZIP', 'geometry/mesh.bin.gz'), ('ENV_GZIP', 'studio/environment.bin.gz'),
    ('PROBE_GZIP', 'studio/probes.bin.gz'), ('IRR_GZIP', 'studio/irradiance.bin.gz'),
    ('SURFACE_COLOR', 'materials/color.rgba.gz'), ('SURFACE_NORMAL', 'materials/normal.rgba.gz')]:
    values[key] = base64.b64encode((ROOT/path).read_bytes()).decode()
values['ORIGINAL_GZIP'] = base64.b64encode(gzip.compress((ROOT/'reference/original-ray-traced.html').read_bytes(),mtime=0)).decode()
for key, value in values.items():
    html = html.replace(f'__{key}__', value)
assert '__SHADERS__' not in html and '__GEOMETRY' not in html
output = ROOT/'dist/index.html';output.parent.mkdir(exist_ok=True)
output.write_text(html)
info = {'build': 'cybr-mobile-recovery-2026-10-22-r1','bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'physicalAndroidTested':False,'sixtyFPSVerified':False,'photorealismClaimed':False}
(ROOT/'build-info.json').write_text(json.dumps(info,indent=2))
print(json.dumps(info,indent=2))
