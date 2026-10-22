#!/usr/bin/env python3
"""Build one self-contained portfolio and the identical FragCoord fragment source."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
PARTS = ('header.glsl', 'scene.glsl', 'transport.glsl', 'interface.glsl', 'main.glsl')

def build():
    pieces = []
    for name in PARTS:
        path = ROOT / 'src' / name
        if not path.is_file():
            raise SystemExit(f'Missing source module: {name}')
        pieces.append(f'\n// ---------------- {name} ----------------\n' + path.read_text(encoding='utf-8').rstrip() + '\n')
    shader = '\n'.join(pieces).lstrip()
    if re.search(r'\bsampler(?:2D|Cube|3D)\b', shader):
        raise SystemExit('A texture sampler unexpectedly entered the asset-free source.')
    if '__FRAGMENT_SOURCE__' in shader:
        raise SystemExit('Unresolved fragment marker in shader.')
    template = (ROOT / 'host.html').read_text(encoding='utf-8')
    if template.count('__FRAGMENT_SOURCE__') != 1:
        raise SystemExit('The host must contain exactly one fragment source marker.')
    # Host embeds a String.raw template. Escape only syntax that could terminate it.
    escaped = shader.replace('`', '\\`').replace('${', '\\${').replace('</script', '<\\/script')
    html = template.replace('__FRAGMENT_SOURCE__', escaped)
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    (out / 'cybr-computational-instrument.frag').write_text(shader)
    (out / 'index.html').write_text(html)
    report = {
        'title': 'CYBR / The Computational Instrument',
        'revision': 'reconstruction-2026-10-21',
        'source_bytes': len(shader.encode()),
        'source_lines': len(shader.splitlines()),
        'source_sha256': hashlib.sha256(shader.encode()).hexdigest(),
        'html_bytes': len(html.encode()),
        'chapters': ['Assembly','Light','Geometry','Scenes','Elements','Materials','Forest','About'],
        'external_assets': 0,
        'modules': list(PARTS),
    }
    (out / 'build-info.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    build()
