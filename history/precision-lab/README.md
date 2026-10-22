# CYBR — Precision Lab

An editable mechanical portfolio with eight chapters. All displayed objects are
actual generated geometry rendered in WebGL 2; there is no rendered photograph,
video, or generated concept image hiding behind the interface.

## Run

Open `index.html` in a full browser. The standalone file embeds its own geometry,
material maps, lighting caches, GLSL programs and original reference source.
No CDN, external texture, model, font or API request is needed at runtime.

The default **Studio** mode refines the stationary view. It displays the live
preview during navigation and the first few samples, then reconstructs the
accumulated path-traced image. **Live** keeps the moving mechanisms animated.
Both render native device pixels unless you explicitly choose another scale.
The sample counter is not an animation FPS claim.

Scroll/swipe through chapters; drag to orbit. Arrow keys and 1–8 select chapters.
The visible **Diagnostics** button has selectable text, Copy report and Download
JSON. The panel also offers an explicit resolution scale, optical focus,
geometry-traced optics and reconstruction on/off. Disable reconstruction to
inspect the raw accumulated Monte Carlo image.

## This revision

* Source-built turned service collars, connected cables, adjustments, bearing
  details, gimbal hardware, smaller fasteners and threaded components.
* A large, inclined, physically supported identity plate, closer to the original
  foreground composition. Text is shader-drawn, not a font texture.
* Angular geological specimens with continuous displaced fracture faces. The
  rejected stacked-plate prototype is not the delivered rock.
* Revised soil/litter and foliage geometry; these are still authored procedural
  specimens rather than biological reconstructions or scans.
* A more directional studio key, reduced fill, dark flags, matched baked
  visibility/indirect lighting and scene-local reflection captures.
* Elliptical anisotropic GGX in the progressive material evaluator and sampler;
  machining directions follow the component rather than screen coordinates.
* Native-resolution Studio reconstruction using depth, primary normal and
  luminance-variance guides. Three edge-aware a-trous passes are optional.
* Studio is selected initially rather than requiring a hidden quality switch.

These are concrete implementation changes, not a certification of photorealism
or a numerical visual-improvement score. Inspect the supplied native captures.

## Important limits

This remains a **multi-pass mesh renderer**, not the original one-fragment
shader. The geometry, surface maps and environment are procedural; no scan or
captured HDRI is claimed. The Studio integrator is bounded to ten interactions,
uses radiance clamping and approximate straight-through next-event visibility
across glass. The flame is composited procedural emission, not a fluid simulation
or a volumetric multiple-scattering solution. Reconstruction is a biased filter.

Live indirect lighting and reflection captures are static rest-pose caches.
Live glass can trace geometry, but terminal shading is approximate; Studio traces
successive surface/glass interactions. Animation and quality refinement are
separate modes, not a 60-fps path-tracing result.

No physical Adreno 830 has been measured in this revision. Browser tests use
ANGLE/Mesa software graphics and emulate native pixel dimensions and touch.
A successful functional check does not establish smooth mobile frame rate.

## Rebuild from the supplied caches

Python 3's standard library is sufficient:

```sh
python build.py
```

The standalone artifact is written to `dist/index.html`.

## Edit and regenerate

Readable scene recipes are in `studio/geometry.py` and `studio/exhibits.py`.
Materials and the Studio BSDF are in `shaders/scene.frag` and
`shaders/progressive-body.glsl`. `shaders/denoise.frag` implements reconstruction.
The host, input handling and render graph are in `host.html`.

For asset authoring, install NumPy, SciPy and trimesh. Lighting/BVH rebuilds also
need a C++17 compiler with OpenMP support. Rebuild in this order:

```sh
python studio/geometry.py
python studio/make_surface_maps.py
python studio/optical_environment.py
bash studio/rebake.sh
python studio/bake_probes.py
python build.py
```

Probe capture and browser checks require Playwright, Chromium, Pillow and Xvfb.
In the restricted test container, `studio/browser_loading.py` incrementally loads
the same standalone HTML to avoid a very large CDP message; it does not replace
the rendered scene or any shader. Paths to Chromium/Xvfb can be adjusted for a
local environment.

`studio/review_precision.py` captures actual canvas pixels, both reconstructed and
raw. `studio/verify_optical.py` records functional tests and graphics diagnostics.
The original ray-traced source remains in `reference/original-ray-traced.html`.
