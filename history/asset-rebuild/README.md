# CYBR — Asset Rebuild

An asset-level revision of the Mobile Recovery portfolio. The new standalone
page is an interactive WebGL 2 renderer, not a picture or a prerecorded video.
It retains the recovery renderer's two-pass architecture and native drawing
buffer. It does not load the earlier triangle path tracer, BVH textures,
progressive histories, MSAA targets, or depth-of-field buffers.

## Open and navigate

Open `dist/index.html` in a full WebGL 2 browser. Everything needed at runtime is
embedded. There are no external asset, library, or font requests. Swipe or scroll
through the eight chapters, drag to orbit, or select a chapter. The visible
Diagnostics button offers Copy report, Download JSON, selectable text, and
explicit Native / 75% / 50% choices. Native is the default; no automatic
resolution reduction occurs. Browser allocation limits and the 320 MiB
application-resource estimate are reported separately.

## What was reconstructed

- **Tree:** a new irregular trunk, fused root collar and branch junctions,
  tapered twigs, individual curved/serrated leaves with nine venation variants,
  and mineral soil with localized moss/litter. The organic field is meshed
  offline; it is not ray-marched at runtime. The forest camera was moved back
  so the tree is not clipped by the top of the frame.
- **Stone:** a new non-convex specimen with unequal cut faces, eroded fractures,
  concave chipped regions, mineral surface variation, and scattered fragments.
  It replaces the old repeated faceted outcrop. Wetting near the base is an
  authored material transition, not a fluid simulation.
- **Mechanism:** an open turbine support with three bearing bridges and
  rectangular windings around the stator teeth, rather than stacked ring coils.
  Enamel skirts and a coated central housing replace decorative stripe stacks.
  Fine machining remains surface detail instead of more tiny geometry.
- **Flame:** a 48-frame compact temperature/density volume, generated offline
  using buoyancy, advection, pressure projection, fuel and heat. Runtime uses
  this 3D flow to modulate analytic thin reaction sheets in a 40-step bounded
  volume integration; it is not a flame image
  pasted onto the scene. The coarse standalone-volume appearance was rejected during visual review;
  sub-grid sheets preserve the previous flame detail. It uses 6 MiB of RG8 GPU storage and a 7.92-second loop
  with a six-volume crossfade. This is simplified, artist-directed combustion,
  not a validated combustion or fire-safety solver.
- **Surfaces:** new mineral, bark, leaf, basalt, enamel and directional-metal
  data. Material texture arrays remain 1024 x 1024 with eight layers. The leaf
  atlas occupies the former studio-floor layer rather than adding another
  texture array. The floor is analytic.

The rebuilt geometry has freshly baked static direct-light visibility and
one-bounce diffuse irradiance, plus seven freshly rendered local reflection
captures. This is not the old lighting cache transferred onto changed geometry.
The final pass includes edge-adaptive spatial antialiasing; pixel dimensions
remain native and shader-drawn interface text is composed after the filter.

## Provenance and remaining limitations

All replacement assets are authored procedural geometry, surfaces and flow.
**No photographs, photogrammetry scans, external 3D models, or AI-generated
images are embedded.** They must not be described as scanned or photographic
source assets. The tree and stone have changed substantially, but the result
is not a claim of convincing photorealism across every exhibit. Fire remains
stylized; glass uses cached scene transmission/reflections rather than an
accurate solution for arbitrary changing geometry. The original reference
assembly and portfolio identity are retained.

Lighting and probes describe a static rest pose. Rotating mechanisms do not
update every shadow/reflection. Some thin geometry can alias. The spatial edge
filter is not multisample or temporal antialiasing. Reflection captures are
256-pixel cubemap faces, so close-up optical detail has a finite resolution.

The software browser checks establish that the real programs draw, navigate,
retain native pixels, expose diagnostics, and recover from a deliberately
triggered context loss. They are **not** Adreno 830 performance measurements,
photorealism scores, or proof that the earlier physical-device crash cannot recur.
Sixty frames per second on the user's phone remains unverified.

## Build the self-contained page

The generated compressed assets are included. Rebuilding HTML requires only
Python's standard library:

```sh
python build.py
```

The output is `dist/index.html`. Its SHA-256 appears in `build-info.json` and the
verification report. The historical single-fragment build is preserved in
`reference/original-ray-traced.html`; the current live renderer is multi-pass.

## Regenerate assets and lighting

For asset generation install Python packages `numpy scipy scikit-image trimesh`.
For browser probe capture and verification also install `playwright pillow`,
Chromium and Xvfb. The CPU lighting tools require a C++ compiler with OpenMP.
The default browser executable in the supplied scripts is `/usr/bin/chromium`;
adjust it for another installation.

```sh
python studio/rebuild_surface_maps.py
python studio/bake_flame.py
python studio/geometry.py

g++ -O3 -fopenmp -std=c++17 studio/bake_lighting.cpp -o studio/bake_lighting
g++ -O3 -fopenmp -std=c++17 studio/bake_irradiance.cpp -o studio/bake_irradiance
./studio/bake_lighting geometry/mesh.bin geometry/mesh-lit.bin
python studio/pack_lighting.py
./studio/bake_irradiance geometry/mesh.bin studio/irradiance.f32
python studio/pack_irradiance.py

# Build once so the browser can render the new geometry for reflection probes.
python build.py
python studio/bake_probes.py
python build.py
python studio/verify_assets.py
```

The material generator preserves the existing walnut/marble layers, so the
included source texture arrays are required. The flow and geometry generators
use deterministic seeds. CPU/compiler differences can affect baked floats.
`studio/optical_environment.py` regenerates the analytic studio environment;
no downloaded HDR photograph is required. BVHs built by the **offline** CPU
baking programs are not included in the browser runtime.

## Visual evidence

`verification/` contains actual rendered browser captures and functional checks.
The matched-before/after review is generated from the Recovery and Asset Rebuild
pages with the same render resolution. In the forest comparison both versions
use the revised camera; other chapter viewpoints are unchanged. Comparison
layout and labels do not alter the render content. No concept render substitutes
for the working canvas.
