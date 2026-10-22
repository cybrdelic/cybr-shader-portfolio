#!/usr/bin/env python3
"""Single-context visual review and poster export of the exact final shader.

Review images and contact-sheet labels are QA outputs. The poster is an actual
supersampled shader frame; there is no alternate scene or generated imagery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw

from native_render import NativeRenderer, PROJECT, atomic_png

CHAPTERS = ["Assembly", "Light", "Geometry", "Scenes", "Elements", "Materials", "Forest", "About"]
HOLD_TIMES = [4.125, 7.85, 11.05, 14.25, 17.45, 20.65, 23.85, 27.725]
TRANSITION_TIMES = [6.175, 9.45, 12.65, 15.85, 19.05, 22.25, 25.525]


def image_sha(pixels):
    return hashlib.sha256(pixels.tobytes()).hexdigest()


def downsample(pixels, width, height):
    if pixels.shape[:2] == (height, width):
        return pixels
    return np.asarray(Image.fromarray(pixels, "RGB").resize((width, height), Image.Resampling.LANCZOS))


def sheet(items, path, columns, tile_width, tile_height):
    label_height = 30
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * tile_width, rows * (tile_height + label_height)), (14, 17, 20))
    draw = ImageDraw.Draw(canvas)
    for i, item in enumerate(items):
        x, y = (i % columns) * tile_width, (i // columns) * (tile_height + label_height)
        with Image.open(item["path"]) as source:
            source.load()
            tile = source.convert("RGB").resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x, y))
        draw.text((x + 10, y + tile_height + 8), item["label"], fill=(230, 230, 218))
    atomic_png(path, np.asarray(canvas))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shader", type=Path, default=PROJECT / "dist" / "cybr-computational-instrument.frag")
    parser.add_argument("--output", type=Path, default=PROJECT / "qa" / "final-review")
    parser.add_argument("--artifacts", type=Path, default=PROJECT / "artifacts")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--quality", type=float, default=1.0)
    args = parser.parse_args()
    args.shader = args.shader.resolve()
    args.output = args.output.resolve()
    args.artifacts = args.artifacts.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(args.shader.read_bytes()).hexdigest()
    if args.expected_sha256 and args.expected_sha256 != source_hash:
        raise RuntimeError(f"Source freeze mismatch: {source_hash}, expected {args.expected_sha256}")
    started = time.perf_counter()
    report = {"shader":str(args.shader), "source_sha256":source_hash,
              "source_bytes":args.shader.stat().st_size, "quality":args.quality,
              "desktop":[], "mobile":[], "transitions":[]}

    def save_report():
        partial = args.output / "report.partial.json"
        partial.write_text(json.dumps(report, indent=2) + "\n")
        partial.replace(args.output / "report.json")

    with NativeRenderer(args.shader) as renderer:
        report["renderer"] = renderer.metadata()
        save_report()

        def render_review(kind, chapter, clock, render_size, output_size, filename, label):
            start = time.perf_counter()
            original = renderer.render(*render_size, time=clock, chapter=chapter, quality=args.quality)
            pixels = downsample(original, *output_size)
            path = args.output / filename
            atomic_png(path, pixels)
            record = {"kind":kind, "chapter":chapter, "clock_time":clock, "label":label,
                      "path":str(path), "render_width":render_size[0], "render_height":render_size[1],
                      "width":output_size[0], "height":output_size[1],
                      "seconds":round(time.perf_counter()-start,3),
                      "pixel_sha256":image_sha(pixels),
                      "mean_rgb":np.mean(pixels, axis=(0,1)).round(3).tolist(),
                      "white_fraction":float(np.mean(np.all(pixels >= 253, axis=2))),
                      "black_fraction":float(np.mean(np.all(pixels <= 2, axis=2)))}
            report[kind].append(record)
            save_report()
            print(json.dumps({"event":"review_frame", **record}), flush=True)
            return record

        # The foliage correction is the last material visual risk, so its
        # actual desktop proof is the first frame emitted after shader JIT.
        for chapter in [6, 0, 1, 2, 3, 4, 5, 7]:
            render_review("desktop", chapter, HOLD_TIMES[chapter], (1440,900), (960,600),
                          f"desktop-{chapter}-{CHAPTERS[chapter].lower()}.png", f"{chapter+1:02d}  {CHAPTERS[chapter]}")
        report["desktop"].sort(key=lambda item:item["chapter"])
        desktop_sheet = args.output / "desktop-contact.png"
        sheet(report["desktop"], desktop_sheet, 4, 480, 300)
        report["desktop_contact"] = str(desktop_sheet)
        save_report()

        for chapter in [0, 1, 7]:
            render_review("mobile", chapter, HOLD_TIMES[chapter], (608,1350), (405,900),
                          f"mobile-{chapter}-{CHAPTERS[chapter].lower()}.png", f"{chapter+1:02d}  {CHAPTERS[chapter]} / phone")
        mobile_sheet = args.output / "mobile-contact.png"
        sheet(report["mobile"], mobile_sheet, 3, 270, 600)
        report["mobile_contact"] = str(mobile_sheet)
        save_report()

        for index, clock in enumerate(TRANSITION_TIMES):
            chapter = index + 0.5
            label = f"{CHAPTERS[index]} -> {CHAPTERS[index+1]}"
            render_review("transitions", chapter, clock, (640,400), (640,400),
                          f"transition-{index+1:02d}.png", label)
        transition_sheet = args.output / "transitions-contact.png"
        sheet(report["transitions"], transition_sheet, 4, 400, 250)
        report["transitions_contact"] = str(transition_sheet)
        save_report()

        pick_start = time.perf_counter()
        pick_pixels = renderer.render(320, 200, time=HOLD_TIMES[0], chapter=0.0, quality=args.quality, pick=1.0)
        if np.any(pick_pixels[:,:,1:]):
            raise RuntimeError("Pick map is not raw red-channel object identifiers")
        values, counts = np.unique(pick_pixels[:,:,0], return_counts=True)
        if any(int(v) > 8 for v in values):
            raise RuntimeError(f"Unexpected pick IDs: {values.tolist()}")
        palette = np.asarray([
            [15,20,25], [235,191,68], [109,171,233], [215,158,98], [248,93,40],
            [194,140,214], [116,190,103], [218,224,229], [245,217,169]], dtype=np.uint8)
        pick_path = args.output / "pick-overview-falsecolor.png"
        atomic_png(pick_path, palette[pick_pixels[:,:,0]])
        count_map = {str(int(v)):int(count) for v,count in zip(values,counts)}
        report["picking"] = {"path":str(pick_path), "width":320, "height":200,
                             "ids":count_map, "missing_project_ids":[i for i in range(1,7) if str(i) not in count_map],
                             "missing_auxiliary_ids":[i for i in (7,8) if str(i) not in count_map],
                             "seconds":round(time.perf_counter()-pick_start,3)}
        save_report()
        print(json.dumps({"event":"pick_review", **report["picking"]}), flush=True)

        poster_start = time.perf_counter()
        poster_pixels = renderer.render(2560,1600,time=HOLD_TIMES[0],chapter=0.0,quality=args.quality)
        poster_pixels = downsample(poster_pixels,1920,1200)
        poster_path = args.artifacts / "cybr-computational-instrument-poster.png"
        atomic_png(poster_path, poster_pixels)
        report["poster"] = {"path":str(poster_path), "render_width":2560, "render_height":1600,
                            "width":1920, "height":1200, "clock_time":HOLD_TIMES[0],
                            "sha256":hashlib.sha256(poster_path.read_bytes()).hexdigest(),
                            "bytes":poster_path.stat().st_size,
                            "seconds":round(time.perf_counter()-poster_start,3)}
        print(json.dumps({"event":"poster", **report["poster"]}), flush=True)

    final_source_hash = hashlib.sha256(args.shader.read_bytes()).hexdigest()
    if final_source_hash != source_hash:
        raise RuntimeError("Source changed during final review; do not use this review as evidence for the newer shader")
    report["elapsed_seconds"] = round(time.perf_counter()-started,3)
    report["complete"] = True
    save_report()
    print(json.dumps({"event":"review_complete", "source_sha256":source_hash,
                      "elapsed_seconds":report["elapsed_seconds"], "report":str(args.output/"report.json"),
                      "desktop_contact":report["desktop_contact"], "mobile_contact":report["mobile_contact"],
                      "transitions_contact":report["transitions_contact"], "poster":report["poster"]}), flush=True)


if __name__ == "__main__":
    main()
