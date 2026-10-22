# CYBR — Procedural Workshop

Interactive, standalone WebGL 2 portfolio. This revision changes procedural
asset construction and surface/lighting response. It does not use scans,
photographs as textures, photogrammetry, downloaded 3D models, or generated imagery.
It is not a claim that every exhibit has reached photographic realism or ARX-6
quality. The included browser captures show the result rather than a concept render.

## Open

Open `dist/index.html` in a full WebGL 2 browser. All required runtime data is
embedded: there are no external libraries, fonts, images, or asset requests.
Scroll/swipe between the eight chapters; drag to orbit; click the mechanisms or
chapter navigation. Visible HTML controls expose diagnostics and animation.
Diagnostics supports copying, JSON download, and selectable text when clipboard
access is blocked. Native device pixels are the default. The 75% and 50% settings
are explicit choices, never automatic resolution changes.

## What changed from Asset Rebuild

* The stone is constructed from intersecting cleavage planes, tilted strata,
  local wedge/flake losses, and subordinate erosion, not an ellipsoid displaced
  with large noise. Its surface uses quartz/mineral variation, bedding-related
  stains, and blended three-axis material mapping.
* Branches and leaf placement are less regular; leaves have asymmetric cupping,
  drooping tips, and nine procedural venation variants. The forest camera fits
  the full crown rather than cropping it.
* The impeller has finite-thickness swept blade cross sections. Bearing balls
  are spheres rather than toroidal ornaments. Larger lathed profiles have more
  silhouette samples. These are authored visual models, not manufactured designs.
* Eight material layers were regenerated: abrasive-track metal, enamel,
  growth-ring/porous walnut, layered stone, cellular bark, calcite-veined marble,
  porous basalt, and leaves. Color, roughness, height-derived normal and cavity
  data are generated with deterministic numerical procedures.
* Metal/black coating/enamel/copper response is separated. Reflected studio
  panels depend on surface position and emitter dimensions instead of using
  only a direction lookup. This is an efficient area-reflection approximation,
  not an exact GGX area integral. Baked visibility suppresses reflection leakage.
* The bench optic is a thinner biconvex lens with restrained coating reflectance.
  It combines a stable projected platter term with cached scene transmission.
  The crystal uses analytic entry/exit surfaces and scene-local radiance caches.
  These optics are approximate; hidden moving geometry cannot be recovered.
* Flame changes are to coherent flow-modulated reaction sheets and the heat/color
  response. The existing procedural simulated flow cache is retained. This is
  not a new combustion solver and not a verified physically accurate fire.
* Direct visibility, one-bounce diffuse irradiance and seven reflection probes
  were regenerated for the revised geometry. They remain static rest-pose data.
* Specular normal variance is filtered in squared microfacet-slope space. Modest
  viewports also receive native MSAA when it fits a separate 256 MiB estimated
  application-resource ceiling. Dense buffers above 1.8 million pixels receive
  no extra MSAA attachments; pixel dimensions remain native.

The user's ARX-6 shader and rendered reference were inspected for the visual
comparison. No frame from it, or from any other image/video, is used as this
portfolio's background, texture, model, or runtime replacement.

## Runtime and mobile boundaries

This stays on the two-program raster path. No triangle BVH is uploaded, no
progressive ten-bounce tracer is compiled, and no accumulation or denoising
history is allocated. The two native target textures are HDR color and depth.
Optional MSAA adds two bounded renderbuffers and a resolve, not a third shader
or a lower-resolution image. At 1440 x 2654 the build uses only the two native
textures and does not enable those extra coverage buffers.

The scene contains 1,207,464 triangles and 664,242 vertices. This is more geometry
than Asset Rebuild, not an asserted speed improvement. At 1440 x 2654 the
format-sized application allocation estimate is 225,104,196 bytes (about
214.7 MiB). This excludes browser presentation surfaces, driver overhead,
shader memory, upload transients and CPU/HTML memory. It is not measured VRAM.

The 320 MiB application-resource guard, visible diagnostics, explicit scale
choices and context-restoration path remain. Restoration pauses animation.
These controls do not prove that an Adreno driver reset cannot recur. Physical
Adreno 830 performance and stability were not measured. Sixty fps is not verified.

## Rebuild the exact HTML

The compressed generated caches are included. Only Python's standard library is
needed to assemble the page:

```sh
python build.py
```

`build-info.json` records the actual output size and SHA-256. The verification
report is bound to that HTML hash. Editing the shader/host invalidates the old
report until verification is rerun.

## Regenerate procedural assets and lighting

Python dependencies: numpy, scipy, scikit-image, trimesh. Browser tools additionally
need playwright, Pillow, Chromium, and Xvfb. The lighting baker requires a C++17
compiler with OpenMP. The scripts default to `/usr/bin/chromium` on Linux.

```sh
python studio/workshop_surfaces.py
python studio/geometry.py
python studio/optical_environment.py
# Optional: regenerate the inherited procedural flow animation.
python studio/bake_flame.py

g++ -O3 -fopenmp -std=c++17 studio/bake_lighting.cpp -o studio/bake_lighting
g++ -O3 -fopenmp -std=c++17 studio/bake_irradiance.cpp -o studio/bake_irradiance
OMP_NUM_THREADS=4 ./studio/bake_lighting geometry/mesh.bin geometry/mesh-lit.bin
python studio/pack_lighting.py
OMP_NUM_THREADS=4 ./studio/bake_irradiance geometry/mesh.bin studio/irradiance.f32
python studio/pack_irradiance.py
python build.py
python studio/bake_probes.py
python build.py
python studio/verify_workshop.py
python studio/visual_review.py
# Optional matched comparison with an explicitly supplied older build:
python studio/visual_review.py --baseline /path/to/CYBR-Portfolio-Asset-Rebuild.html
```

All asset seeds and generation code are included. Floating-point/compiler
changes can affect rebuilt geometry/bake bytes; HTML assembly from the included
caches is deterministic. Offline BVHs used by the CPU lighting bakers are not
part of the browser runtime.

## Evidence and known visual limits

`verification/final/test-report.json` records actual Chromium WebGL drawing,
all eight chapters, touch, diagnostics, denied clipboard fallback, JSON export,
context loss/restoration, allocation interception, and HDR-extension fallback.
They are functionality/resource tests, not visual-quality scores or phone fps.

`verification/visual/` contains unmodified 1920 x 1200 native browser-canvas PNGs.
The capture manifest records cameras, animation time, hashes and GL errors.
Before/after views share the same camera, native resolution and animation time.
A labeled comparison sheet only resizes the complete views for layout; native
captures are provided separately. No retouching, sharpening or image generation
is applied to those pixels.

Remaining limitations include cached glass, static bounce/reflection data,
procedural flame styling, residual edge aliasing, and artist-authored natural
forms. The full assembly is not certified or described as convincingly photographic.

## Technical background

These documents were consulted for material/roughness terminology and filtering;
the renderer here is custom code, not the Filament runtime:

- https://google.github.io/filament/Materials.md.html
- https://google.github.io/filament/Filament.md.html
- https://www.pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory
