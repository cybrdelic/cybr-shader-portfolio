#!/bin/bash
set -e
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
for b in bake_lighting bake_irradiance; do g++ -O3 -std=c++17 -fopenmp studio/$b.cpp -o studio/$b; done
g++ -O3 -std=c++17 studio/build_optical_bvh.cpp -o studio/build_optical_bvh
studio/bake_lighting geometry/mesh.bin geometry/mesh-lit.bin
python studio/pack_lighting.py
studio/bake_irradiance geometry/mesh.bin studio/irradiance.f32
python studio/pack_irradiance.py
studio/build_optical_bvh geometry/mesh.bin geometry/optical-bvh.bin > geometry/optical-bvh.json
python - <<'PY'
from pathlib import Path
import gzip
p=Path('geometry/optical-bvh.bin');p.with_suffix('.bin.gz').write_bytes(gzip.compress(p.read_bytes(),6,mtime=0))
PY
python studio/build_progressive_shader.py
python build.py
echo BUILD_DONE
