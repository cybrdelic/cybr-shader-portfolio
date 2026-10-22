#!/usr/bin/env python3
"""Package authored source, built output, and any completed final media exports."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=[
    'README.md','build.py','host.html',
    'src/header.glsl','src/scene.glsl','src/transport.glsl','src/interface.glsl','src/main.glsl',
    'tools/native_render.py','tools/render_movie.py','tools/render_suite.py','tools/final_review.py','tools/verify_host.mjs','tools/package_source.py',
    'dist/index.html','dist/cybr-computational-instrument.frag','dist/build-info.json',
]
OPTIONAL_MEDIA={
    'artifacts/cybr-computational-instrument-rebuilt.mp4': 'media/cybr-computational-instrument-rebuilt.mp4',
    'artifacts/cybr-computational-instrument-rebuilt.json': 'media/cybr-computational-instrument-rebuilt.json',
    'artifacts/cybr-computational-instrument-poster.png': 'media/cybr-computational-instrument-poster.png',
}

def package(source_only=False):
    output=ROOT/'artifacts';output.mkdir(exist_ok=True)
    dest=output/'cybr-computational-instrument-rebuilt-source.zip'
    partial=dest.with_suffix('.partial.zip')
    manifest={}
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:
            p=ROOT/name
            if not p.is_file():raise FileNotFoundError(name)
            data=p.read_bytes();z.writestr(name,data)
            manifest[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        # Only final export names are eligible; partial renders and this ZIP are excluded.
        for source,name in ({} if source_only else OPTIONAL_MEDIA).items():
            p=ROOT/source
            if not p.is_file():continue
            data=p.read_bytes()
            compression=zipfile.ZIP_STORED if p.suffix in {'.mp4','.png'} else zipfile.ZIP_DEFLATED
            z.writestr(name,data,compress_type=compression)
            manifest[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(partial) as z:
        bad=z.testzip()
        if bad:raise RuntimeError(f'Archive checksum failure: {bad}')
    partial.replace(dest)
    shutil.copy2(ROOT/'dist/index.html',output/'cybr-computational-instrument.html')
    shutil.copy2(ROOT/'dist/cybr-computational-instrument.frag',output/'cybr-computational-instrument.frag')
    backup_marker=ROOT/'qa/checkpoint-location.txt'
    backup_marker.parent.mkdir(parents=True,exist_ok=True)
    if backup_marker.exists():
        backup=Path(backup_marker.read_text().strip());backup.mkdir(exist_ok=True)
    else:
        backup=Path(tempfile.mkdtemp(prefix='cybr-instrument-checkpoint.'))
        backup_marker.write_text(str(backup)+'\n')
    shutil.copy2(dest,backup/dest.name)
    result={'archive':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'files':len(manifest)+1,'source_files':len(FILES)+1,'media_files':[name for name in OPTIONAL_MEDIA.values() if name in manifest],'local_checkpoint':str(backup/dest.name)}
    (output/'source-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true',help='Include the complete source set and skip all optional media.')
    args=parser.parse_args()
    package(source_only=args.source_only)
