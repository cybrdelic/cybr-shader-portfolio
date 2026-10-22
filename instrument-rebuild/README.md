# CYBR — Instrument Rebuild

An actual, self-contained WebGL 2 portfolio revision. All six exhibits, the shared
chassis, and the central instrument have been rebuilt from dimensions and seeded
procedural models. The supplied ARX-6 shader/render is the construction and material
reference, not a backdrop or an asset embedded in the live canvas.

No scans, photographs, photogrammetry, external model downloads, or image-generation
outputs are used to construct the scene. The shader text, material arrays, optical
captures, environmental radiance, illumination caches, flame flow, and mesh have
explicit source generators in this package.

## Open

Run `python build.py`, then open `dist/index.html` in a full WebGL 2 browser. The
standalone HTML is also distributed separately. There are no network dependencies,
CDN scripts, external fonts, or runtime asset downloads. Android content/file URLs
are supported by embedding the compressed assets directly.

Scroll/swipe through Assembly, Light, Geometry, Scenes, Elements, Materials,
Forest, and About. Drag to orbit. Chapter buttons and arrow keys navigate directly.
The always-visible Diagnostics button opens copy/download/selectable JSON controls.
Native device-pixel resolution is the default. The 75% and 50% buttons are explicit
choices, never automatic changes.

Animation begins paused. A stationary view refines pixel coverage with eight
subpixel-offset **raster** frames, then stops submitting work. This is bounded
antialiasing, not a path tracer or a progressive illumination convergence mode.
Moving the camera resets that history immediately and renders at native resolution.
Play animation starts the moving mechanisms and flame. The diagnostic readout says
idle/refining while paused rather than mislabeling that cadence as animation FPS.

## Construction changes

### Shared structure and central instrument

The base is a solid enamel-coated platter with a restrained bead-blasted rim,
recessed hardware, elastomer feet, connected paired cable runs, clips, and a thin
supported identity plate. The central bearing housing no longer relies on many
bright decorative rings. Four slender structural rods support its enamel cap.
Two calibrated gimbals surround a procedurally cut seven-sided crystal, with a
supported carriage and micrometer details.

### Light

The optical station has a dimensioned kinematic mount, black baffle, retaining
shoulder, eight fasteners, bearing pivots, adjustment barrels, and smaller
collimators. Its large biconvex lens is defined by the intersection of two spheres.
The lens's optical axis now agrees with the geometry's actual mounting transform.
Entry and exit refraction are solved analytically; the old screen-depth crossings
that produced discontinuous false intersections have been removed.

The central crystal uses exactly the convex face planes of the generated mesh.
A ray undergoing total internal reflection remains inside the solid until it
reaches a valid exit, within a four-interface bound. These are optical surface
intersections, not ray tracing through the entire scene.

### Geometry

The compressor/motor cutaway has 19 twisted, cambered, closed-thickness airfoils,
a smooth revolved spinner, enamel end bells, substantial casing ribs, three
bearing bridges, and nine independently wound stator teeth. Hardware and
machined shoulders have explicit profiles rather than point-like decorations.
An inward-normal defect in the first generated airfoil iteration was found and
corrected before the final lighting bake.

This is a visually coherent designed mechanism, not a torque-rated, manufactured,
or independently validated machine. It should not be described as a released
engineering design merely because parts are visibly connected.

### Scenes

The specimen is authored as fractured slate: unequal intersecting cleavage
planes, folded seams, concave flake loss, weathered discontinuities, and fine
material variation share coherent spatial coordinates. Larger fragments and
small chips sit in a three-point holding fixture. It is not displaced scan data
or a uniformly noisy sphere.

### Elements

The crucible has a thick refractory insert, heat-darkened collar, retaining feet,
thermocouple and supply leads. Its sintered crust is composed of irregular warped
plates with thickness, boundary clipping, and narrow exposed molten channels.
The cell-boundary winding is explicitly normalized: a prior generation produced
inward-facing tops for roughly half of the cells, creating artificial bright
holes. The final geometry audit checks outward-facing tops.

The flame retains the previous compact, procedurally generated temperature/density
flow cache and analytic reaction-sheet detail. It is not a photographic sprite,
and it is not a fully validated combustion simulation. This revision chiefly
reconstructs the thermal container/crust and their material treatment; it does
not claim a wholly new high-resolution fire solver.

### Materials

Walnut, marble, enamel, a turned metal specimen, and woven carbon cloth are
separated physical coupons. Their thickness and mounting are visible. New
walnut growth-coordinate grain includes knot/fiber distortion and separate
end-grain treatment. Marble uses sparse, forked mineral seams. Coated surfaces,
black anodized housings, aluminum, steel, copper and bronze have distinct
reflectance and roughness rather than a shared glossy finish.

### Forest

A continuous, irregularly tapered root/trunk structure carries unequal branch
tiers, secondary twigs, terminal shoots, paired pine needles and buds. Needles
have tapered cross-sections and bend; they are geometry, not transparent leaf
billboards. Bark coordinates follow the trunk. The pot includes mineral grains
and localized lichen. It is an authored procedural pine/bonsai, not a scan.

## Lighting and rendering

The two draw passes remain opaque surfaces, then optical/flame/display/interface
composition. A small mathematical lookup fitted to the GGX distribution evaluates
finite rectangular light reflections. The fitting script and numerical residuals
are included. This is an approximation, not an exact anisotropic reference solver.
ARX-6 informed the restrained enamel, anodized and machined-metal values and broad
area-light presentation; no assertion of identical appearance is inferred from
sharing parameter choices.

Direct visibility (56 key and 24 fill samples), ambient visibility (40 directions),
and approximate one-bounce diffuse irradiance (80 directions) are baked offline
for the final geometry. Seven 256-pixel local reflection captures and two dedicated
512-pixel optical captures are rendered from that same geometry. Optical captures
include their mounts while the analytic core glass itself is absent from the
opaque capture pass. Each cache records the geometry hash.

No triangle BVH, full-scene path tracer, multiple-bounce GPU scene integration,
MSAA targets, depth-of-field pass, or HDR denoising history is allocated in the
browser. Offline CPU baking tools use a BVH, but that structure is not shipped to
the GPU. One RGB8 history is used only for the eight-frame stationary edge resolve.

The glass samples static scene-local radiance after its analytic interface solve.
It cannot reveal correct arbitrary moving off-screen geometry, update all dynamic
reflections, or solve physical caustics. The normal shadow/indirect-light caches
also describe the rest pose. Increasing the number of light bounces was not used
as a substitute for rebuilding the assets.

## Resource and performance boundaries

Native 1440 x 2654 rendering is tested in software-rendered Chromium at the user's
reported pixel dimensions. Resource accounting includes mesh/index buffers,
material arrays, baked lighting, environment/probes, optical captures, flame/noise
and the native color/depth plus RGB edge history. The 320 MiB application-payload
guard is not a measurement of available device memory. Browser presentation,
shader/driver storage, alignment, transient upload and CPU/HTML memory are excluded.

Functional tests and software readbacks do **not** verify 60 fps on the physical
Adreno 830 or guarantee that its driver cannot reset. There is no physical Android
benchmark in this package. Submission/PNG readback timing is not GPU execution time.
Actual rendering quality is evidenced by canvas captures, not by a test count.

## Build and regenerate

The included compressed data are enough for `python build.py`; only Python's
standard library is needed to reconstruct the exact standalone HTML.

For complete regeneration, use Python with NumPy, SciPy, scikit-image, trimesh,
Pillow and Playwright, plus Chromium, Xvfb, a C++17 compiler and OpenMP:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
python studio/rebuild_surface_maps.py
python studio/fit_area_lights.py
python studio/optical_environment.py
python studio/bake_flame.py
python studio/geometry.py

g++ -O3 -fopenmp -std=c++17 studio/bake_lighting.cpp -o studio/bake_lighting
g++ -O3 -fopenmp -std=c++17 studio/bake_irradiance.cpp -o studio/bake_irradiance
./studio/bake_lighting geometry/mesh.bin geometry/mesh-lit.bin
python studio/pack_lighting.py
./studio/bake_irradiance geometry/mesh.bin studio/irradiance.f32
python studio/pack_irradiance.py

# Existing compressed captures bootstrap the first browser build. They are
# regenerated below and are not accepted as final until provenance matches.
python build.py
python studio/bake_probes.py
python build.py
python studio/bake_optical_probes.py
python build.py
python studio/audit_geometry.py
python studio/verify_instruments.py
```

The material generator starts with the supplied texture arrays and replaces its
authored layers. The compact noise lattice is deterministic included data.
Compiler and floating-point differences can alter bake hashes; the final audit
requires all caches to agree with the geometry produced in that regeneration.
Browser executable and display numbers are configurable in the Python scripts.

`verification/` contains actual captures, geometry/bake audit and browser checks.
The separately distributed comparison uses the same chapter, camera, timestamp
and pixel dimensions in the old and new browser builds. Layout labels are not
part of the render; no image-generation output or offline beauty render replaces
the interactive scene in those comparisons.
