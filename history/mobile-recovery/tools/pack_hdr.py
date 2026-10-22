"""Convert an existing RGBA16F environment/probe cache to RGB9_E5.

Usage:
    python tools/pack_hdr.py old/environment.bin.gz old/environment.json output/environment

No screen-space images are generated. Cubemap faces and mip ordering are retained.
Requires NumPy. Build.py itself needs only the Python standard library.
"""
from __future__ import annotations
import argparse, gzip, json
from pathlib import Path
import numpy as np

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input_cache', type=Path)
    p.add_argument('input_metadata', type=Path)
    p.add_argument('output_prefix', type=Path)
    args = p.parse_args()
    meta = json.loads(args.input_metadata.read_text())
    data = gzip.decompress(args.input_cache.read_bytes())
    if meta.get('type') != 'RGBA16F' or len(data) % 8:
        raise SystemExit('Input must be an RGBA16F cache, with complete four-channel half-float texels.')
    rgb = np.frombuffer(data, '<f2').reshape(-1, 4)[:, :3].astype(np.float32)
    if not np.isfinite(rgb).all() or (rgb < 0).any() or (rgb > 65408).any():
        raise SystemExit('Input radiance is outside the finite positive RGB9_E5 representable range.')
    brightest = rgb.max(axis=1)
    exponent = np.maximum(0, np.floor(np.log2(np.maximum(brightest, 1e-30))).astype(np.int32) + 16)
    scale = np.exp2(24 - exponent).astype(np.float32)
    exponent += (np.floor(brightest * scale + .5) >= 512).astype(np.int32)
    exponent = np.minimum(exponent, 31)
    scale = np.exp2(24 - exponent).astype(np.float32)
    mantissa = np.minimum(511, np.floor(rgb * scale[:, None] + .5)).astype(np.uint32)
    packed = (mantissa[:, 0] | (mantissa[:, 1] << 9) | (mantissa[:, 2] << 18) | (exponent.astype(np.uint32) << 27)).astype('<u4')
    decoded = mantissa.astype(np.float32) / scale[:, None]
    error = np.abs(decoded-rgb)
    compressed = gzip.compress(packed.tobytes(), compresslevel=6, mtime=0)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    args.output_prefix.with_suffix('.bin.gz').write_bytes(compressed)
    meta.update(type='RGB9_E5', bytes=packed.nbytes, compressedBytes=len(compressed), encoding='Shared exponent RGB; complete original mip chain and face dimensions.')
    args.output_prefix.with_suffix('.json').write_text(json.dumps(meta, indent=2))
    audit = dict(inputBytes=len(data), outputBytes=packed.nbytes,
                 meanAbsoluteError=float(error.mean()), maxAbsoluteError=float(error.max()),
                 maxErrorRelativeToBrightestChannel=float((error/np.maximum(brightest,1e-9)[:,None]).max()))
    args.output_prefix.with_suffix('.audit.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))

if __name__ == '__main__':
    main()
