# CYBR / The Computational Instrument

An eight-chapter engineering portfolio drawn entirely in one fragment shader.

This is a **fresh reconstruction** of the missing October 21, 2026 revision. It is not a byte-for-byte recovery of that deleted source or its original MP4.

The scene, camera, procedural materials, lighting, typography, labels, chapter navigation, and object-picking map all live in GLSL. The HTML host creates a WebGL 2 context, forwards input, controls rendering resolution, and provides accessible text and explicit download/link actions. It does not draw the visible portfolio.

## Open the portfolio

Open `dist/index.html` in a WebGL 2 capable browser. It is self-contained and makes no external asset requests. If your browser restricts local HTML, serve this directory with `python -m http.server 8000` and visit `http://localhost:8000/dist/`.

Controls:

- Scroll, swipe, or press Left/Right to move between the eight chapters.
- Press 1–8 to jump directly to a chapter.
- Click a mechanism or a chapter in the bottom navigation to inspect it.
- Drag with a mouse to orbit the current view. On a phone, swipe to travel between chapters.
- Press T to toggle the tour, Space to pause, Q to cycle quality, F for fullscreen, and S to download the complete GLSL source.
- Press E to open the complete source in FragCoord, P to export the current rendered image, and R to reset the camera. The bracket keys adjust exposure; Home and End select the first and last chapters.
- The visible Source control downloads GLSL locally. Opening the portfolio does not upload the shader; opening it in FragCoord requires an explicit editor action.

The host honors the browser's reduced-motion preference, begins paused when that preference is enabled, and stops drawing when a paused view has settled. A missing WebGL 2 context or a shader compilation error leaves the complete source available to download.

## Chapters

1. **Assembly** — the connected machined chassis and optical core.
2. **CYBR LIGHT** — a glass optical element suspended in a precision cradle.
3. **CYBR GEO** — a radial rotor and its mechanical construction.
4. **CYBR SCENES** — miniature architecture, terrain, and water.
5. **CYBR ELEMENTS** — heated material and a contained molten chamber.
6. **CYBR MATERIALS** — a set of procedural surface specimens.
7. **CYBR FOREST** — a miniature branching tree.
8. **About** — Alejandro Figueroa, graphics, simulation, and systems.

These objects are procedural portfolio motifs. They are not exports from the individual CYBR project repositories, and they do not establish benchmarks or simulation-validation claims for those projects.

## Build and source

Run `python build.py` to concatenate the five source modules and embed that exact output in the host. No npm packages or build server are needed. `dist/build-info.json` records the assembled source hash, byte count, and line count.

`dist/cybr-computational-instrument.frag` is the complete FragCoord source. FragCoord supplies the standard `u_resolution`, `u_time`, `u_mouse`, `u_drag`, `u_scroll`, and `fragColor` symbols. The exported file declares its own chapter, exposure, quality, tour, and picking controls.

Paste the whole `.frag` file into one GLSL fragment pass in FragCoord. Do not paste individual modules or add the browser host's `#version`, built-in uniforms, or output declaration. Use these custom controls:

| Uniform | Purpose | Normal value |
| --- | --- | --- |
| `u_chapter` | Continuous camera position through chapters 0–7 | `0.0` for Assembly |
| `u_exposure` | Photographic exposure multiplier | `1.0` |
| `u_quality` | Renderer quality, from fast to high detail | `1.0` |
| `u_tour` | Automatic shader camera tour | `0.0`; set to `1.0` to run |
| `u_pick` | Object identifier output used by the HTML host | Keep at `0.0` for the visible portfolio |

The FragCoord editor uses its chapter slider, scroll, and drag inputs. Clickable chapter navigation, project picking, external links, and downloads are implemented by the included HTML host. Both environments render the same assembled shader.

## Rendering the actual shader

`tools/native_render.py` creates a surfaceless EGL / GLES 3 context through ctypes and compiles the same full GLSL source as the browser. It uses NumPy and Pillow for readback and image writing. The video renderer sends genuinely rendered frames to FFmpeg; it does not animate or crossfade still pictures.

The supplied native renderer targets a Linux environment with EGL and GLES 3 libraries, Python 3 with NumPy and Pillow, and `ffmpeg`/`ffprobe` on PATH. FFmpeg must include the `libx264` encoder. The harness defaults to Mesa software rendering, so it can run without a dedicated GPU; the browser portfolio does not require any Python dependencies.

Render the review suite:

```bash
python build.py
python tools/render_suite.py --width 800 --height 500
```

Render the reconstructed **26-second, 24 fps, 1280 × 800** tour:

```bash
python build.py
python tools/render_movie.py \
  --shader dist/cybr-computational-instrument.frag \
  --output artifacts/cybr-computational-instrument-rebuilt.mp4 \
  --width 1280 --height 800 --fps 24 --seconds 26 \
  --quality 1 --render-scale 1.5 --exposure 1 --clock-offset 3 \
  --chunk-seconds 2 --crf 18
```

This renders **624 actual shader frames at 1920 × 1200**, then downsamples each frame to the final 1280 × 800 movie. The camera holds on each of the eight chapters and travels continuously between them. The resulting video is H.264, YUV 4:2:0, with BT.709 color metadata and fast-start playback.

Run `python tools/render_movie.py --help` for the other movie options. The renderer records the exact source hash and render settings, validates the decoded frame count and duration, and retains completed two-second chunks. Rerun the same command to resume an interrupted export. Changing the shader or settings requires a new `--checkpoints` directory; existing completed chunks are preserved.

Run `node tools/verify_host.mjs` for the browser host's event-level behavior checks. These checks cover navigation, input, picking dispatch, source export, context recovery, and reduced motion; native image rendering is checked separately. `tools/final_review.py` contains the final native review workflow.

After rebuilding, run `python tools/package_source.py` to create `artifacts/cybr-computational-instrument-rebuilt-source.zip`, standalone HTML, and standalone GLSL. The archive always includes the complete 18-entry source set, counting its per-file SHA-256 manifest, and the build's source provenance.

Completed exports are also included when present, under these archive paths:

- `media/cybr-computational-instrument-rebuilt.mp4` — the rendered tour.
- `media/cybr-computational-instrument-rebuilt.json` — its source hash, render settings, and validation provenance.
- `media/cybr-computational-instrument-poster.png` — the portfolio poster.

The packager reads these exact final filenames from `artifacts/`, records their hashes in the same manifest, and skips any that do not exist yet. It works before the film is rendered; rerun it after the export finishes to produce one complete download with the movie and poster. Partial renders and intermediate chunks are excluded.

Use `python tools/package_source.py --source-only` to create the complete 18-entry source archive without optional media; the default includes any completed exports that exist.

The lighting is a deterministic real-time approximation with procedural studio illumination, microfacet material response, soft shadowing, contact occlusion, traced reflections, and analytic glass refraction. This is not an unbiased path tracer or a fluid simulation. No raster textures, generated images, scanned assets, mesh files, font atlases, or neural rendering are used.

## Preservation

Keep the final archive: it contains the complete scene and renderer needed to regenerate every frame, plus the video and poster when packaged after export. A local download alone is not a durable backup; save it to your own storage after downloading.
