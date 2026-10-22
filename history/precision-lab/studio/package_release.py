"""Package only the final editable source and verified release assets."""
from pathlib import Path
import hashlib,json,shutil,zipfile
R=Path(__file__).resolve().parent.parent
OUT=R.parent
HTML=R/'dist/index.html'
report_path=R/'verification/final/test-report.json'
review_path=R/'verification/review/review.json'
report=json.loads(report_path.read_text())
review=json.loads(review_path.read_text())
sha=hashlib.sha256(HTML.read_bytes()).hexdigest()
assert sha==report['htmlSHA256']==review['htmlSHA256'], 'Reports do not match this HTML'
assert report['passed']==report['total'] and not report['errors'], 'Functional checks have failures'
assert not review['errors'], 'Review has browser errors'
assert all(v.get('glError')==0 for v in review['views']), 'Review has GL errors'
files={
 'CYBR-Portfolio-Precision-Lab.html':HTML,
 'CYBR-Precision-Lab-Assembly.png':R/'verification/review/studio-0-128.png',
 'CYBR-Precision-Lab-Assembly-Raw.png':R/'verification/review/raw-0-128.png',
 'CYBR-Precision-Lab-Geometry.png':R/'verification/review/studio-2-64.png',
 'CYBR-Precision-Lab-Geometry-Raw.png':R/'verification/review/raw-2-64.png',
 'CYBR-Precision-Lab-Test-Report.json':report_path,
 'CYBR-Precision-Lab-README.md':R/'README.md',
}
for name,src in files.items():
 assert src.is_file(),src
 shutil.copy2(src,OUT/name)
manifest={'build':'cybr-precision-lab-2026-10-22','htmlSHA256':sha,'htmlBytes':HTML.stat().st_size,
 'geometry':json.loads((R/'geometry/packed.json').read_text()),
 'verification':{'passed':report['passed'],'total':report['total'],'physicalAndroidTested':False,'sixtyFPSVerified':False,'visualTargetCertified':False},
 'captures':[{ 'file':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'provenance':'Actual WebGL canvas, 1280 x 800. Raw or reconstructed as labelled; no retouching or image generation.'} for n,p in files.items() if n.endswith('.png')],
 'mode':'Native-pixel interactive Live renderer and progressive Studio path tracer. Multi-pass geometry, not one fragment shader.',
 'assetSource':'Procedurally authored; no photographic scans or captured HDRI.'}
(R/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
# These were one-off migrations, not reproducible authoring/build steps.
exclude={'add_anisotropy.py','add_reconstruction.py','fix_stone.py','rebuild_art_direction.py','rebuild_shading.py','refine_silhouettes.py'}
allowed=[]
for p in R.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(R);parts=rel.parts
 if '__pycache__' in parts or parts[0]=='dist' or p.name in exclude:continue
 if parts[0]=='verification':
  keep=rel.as_posix() in {'verification/final/test-report.json','verification/shader-compile.json','verification/review/review.json','verification/review/studio-0-128.png','verification/review/raw-0-128.png','verification/review/studio-2-64.png','verification/review/raw-2-64.png'}
  if not keep:continue
 if p.suffix in {'.bin','.f32','.npy','.pyc','.log'}:continue
 if parts[0]=='studio' and p.suffix=='' :continue
 if p.suffix.lower() in {'.ttf','.otf','.woff','.woff2'}:raise AssertionError('Font binaries must not be packaged')
 allowed.append((p,Path('CYBR-Precision-Lab')/rel))
zip_path=OUT/'CYBR-Precision-Lab-Source.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
 for p,rel in sorted(allowed):z.write(p,rel.as_posix())
print(json.dumps({'html':str(OUT/'CYBR-Portfolio-Precision-Lab.html'),'bytes':HTML.stat().st_size,'sha256':sha,'packageFiles':len(allowed),'packageBytes':zip_path.stat().st_size,'checks':f"{report['passed']}/{report['total']}"},indent=2))
