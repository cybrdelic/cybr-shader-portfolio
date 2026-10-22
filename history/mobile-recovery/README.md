# CYBR — Mobile Recovery

A memory/workload repair for the Precision Lab browser artifact. This is **not** a photorealism upgrade, a single-fragment-shader implementation, or a verified 60-fps release.

## Open

Open the generated standalone HTML in the browser. It embeds its geometry, textures, shaders and lighting; no CDN, account or runtime network request is required.

The initial renderer is native-resolution rasterization. Swipe vertically or scroll to move between eight chapters; drag horizontally to orbit. Mouse dragging orbits in both directions. Arrow keys and 1–8 also select chapters. Tap **Play animation** for continuous animation. The default draws on demand and stops submitting work when the view is idle. This is an explicit behavioral change, not a claim that a still image is running at 60 fps.

The normal **Diagnostics** button remains visible above the bottom navigation. It opens selectable report text, Copy report, Download JSON, explicit resolution choices, and Restart renderer. Neither diagnostics nor restart depends on hitting a shader-drawn control. If clipboard access is blocked for a local `content:` or `file:` page, the complete report is selected for manual copying and JSON download remains available.

## What changed

* The progressive path-tracing shader, triangle-ray hierarchy, duplicated ray vertex attributes, accumulation history, reconstruction buffers and depth-of-field pass are absent from this build. They are not merely disabled by a uniform. A legacy `mode=studio` URL cannot load them.
* One native-resolution opaque color/depth framebuffer replaces the multiple live, multisample, accumulation and reconstruction targets. Optics, tone mapping and shader-drawn interface run together in the second pass, directly to the display buffer.
* The HDR color target uses R11F_G11F_B10F when float rendering is supported; a same-size RGBM/RGBA8 fallback is available otherwise. No change in screen resolution is automatic.
* Environment and local reflection captures retain their original dimensions and every mip level, but use shared-exponent RGB9_E5 rather than RGBA16F. They do not need an alpha channel. The conversion audit records its small quantization error; this is not lossless storage.
* Full-resolution 1024 × 1024 material maps, all 1,765,775 mesh triangles, and baked vertex lighting are preserved. The exact original mesh SHA-256 is recorded. Conservative group bounds allow offscreen culling and front-to-back ordering; no mesh decimation or scanned replacement is used.
* Asset decompression and upload run sequentially. Decompressed CPU asset arrays are not deliberately retained after upload. Garbage collection timing is controlled by the browser.
* Resize waits for already-submitted work to drain, deletes the previous target, then allocates the new native target. It does not keep a set of old portrait/landscape targets.
* Native-pixel edge filtering replaces multisample attachments. This is a different antialiasing method; turn it off in Diagnostics to inspect unfiltered pixels. It may retain more edge aliasing than MSAA, especially on lower-density displays.
* Following a context loss, rendering stops and the report retains a pre-loss allocation/workload snapshot. Browser restoration is handled once; repeated failures require an explicit restart. Restart creates a fresh canvas/context and reconstructs resources. It does not repeatedly relaunch a heavy Studio mode.

## Allocation audit at 1440 × 2654

The source-derived application texture/buffer payload estimate is approximately **606.15 MiB** for the old Studio allocation path and **188.12 MiB** for this build. Native offscreen render targets fall from **335.31 MiB** to **29.16 MiB**.

These estimates exclude browser/compositor drawing buffers, driver padding, shader programs, miscellaneous implementation allocations and CPU memory. They are not measurements of physical VRAM, nor proof that the user's previous reset was specifically an out-of-memory failure. The old context may have been lost before all requested allocations completed. The browser did not provide a root-cause message.

The audit is in `verification/allocation-audit.json`. The runtime report lists each tracked application texture/buffer payload and its estimate. A context loss invalidates that ledger; the prior payload is preserved separately in `lastFailure`.

## Remaining tradeoffs

This build uses the same authored objects and procedural materials. It does not fix the toy-like design or certify photorealism. Glass retains analytic lens/crystal boundaries, but reflections and transmitted surroundings use **static local captures**, not live geometry-ray intersections. Baked indirect lighting and shadow visibility remain tied to the rest pose. Flame rendering remains procedural compositing, not a fluid simulation.

No progressive Studio renderer is offered here. The earlier Precision Lab artifact and source are left untouched outside this package. `reference/original-ray-traced.html` is the earlier single-fragment reference, not the heavy Precision Lab Studio renderer.

60-fps animation and physical Adreno stability remain unverified. Browser tests use actual WebGL2 through ANGLE/Mesa software graphics with native portrait dimensions and touch emulation. Passing them establishes rendering and control behavior in that environment, not performance on a phone.

## Rebuild

Python 3 standard library only:

```sh
python build.py
```

This produces `dist/index.html` and a SHA-256 build record. `host.html` contains the complete readable runtime. `shaders/` contains the two vertex and two fragment programs. `geometry/`, `materials/`, and `studio/` contain the embedded asset caches.

## Tests

Browser checks additionally need Python packages `playwright`, `numpy`, and `Pillow`, plus Chromium and Xvfb. The supplied test script uses `/usr/bin/chromium`; adjust that executable path and the Xvfb display number for a different environment.

```sh
python verification/verify_browser.py
```

The restricted execution environment used for this release blocks local URL navigation, so the test loader incrementally parses the **exact standalone HTML** using `document.write`. It does not replace the scene or rendering implementation. Real `content:` navigation and the Adreno driver were not emulated.

The verification report includes actual framebuffer captures, native dimensions, context loss/restoration, fresh-canvas restart, allocation counts after resizes, touch/keyboard navigation, clipboard-denied fallback, JSON download and a no-float-color fallback. Frame-rate observations from software rendering are not extrapolated to mobile hardware.
