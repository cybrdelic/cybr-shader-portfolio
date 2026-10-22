#!/usr/bin/env python3
"""Render a recoverable, frame-authentic film of the complete GLSL portfolio.

The output is real shader animation: each frame changes its own time and camera
chapter uniforms. Complete two-second H.264 chunks are checkpointed atomically.
An interrupted process can resume only when the shader and render settings match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

from PIL import Image

from native_render import NativeRenderer, PROJECT


FILM_KEYS = [
    (0.00, 0.0), (2.25, 0.0),
    (4.10, 1.0), (5.60, 1.0),
    (7.30, 2.0), (8.80, 2.0),
    (10.50, 3.0), (12.00, 3.0),
    (13.70, 4.0), (15.20, 4.0),
    (16.90, 5.0), (18.40, 5.0),
    (20.10, 6.0), (21.60, 6.0),
    (23.45, 7.0), (26.00, 7.0),
]


def film_chapter(seconds: float, duration: float) -> float:
    t = min(26.0, max(0.0, seconds * 26.0 / duration))
    for (ta, a), (tb, b) in zip(FILM_KEYS, FILM_KEYS[1:]):
        if ta <= t <= tb:
            f = (t - ta) / (tb - ta)
            # Quintic ease has zero velocity and acceleration at each hold.
            f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0)
            return a + (b - a) * f
    return 7.0


def probe(path: Path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_read_frames:format=duration,size",
        "-of", "json", str(path),
    ], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def validate_video(path: Path, width: int, height: int, fps: int, frames: int):
    info = probe(path)
    streams = info.get("streams", [])
    if len(streams) != 1:
        raise RuntimeError(f"Expected one video stream in {path}")
    stream = streams[0]
    for key, expected in (("codec_name", "h264"), ("width", width), ("height", height), ("pix_fmt", "yuv420p")):
        if stream.get(key) != expected:
            raise RuntimeError(f"{path.name}: {key} is {stream.get(key)!r}; expected {expected!r}")
    count = int(stream["nb_read_frames"])
    if count != frames:
        raise RuntimeError(f"{path.name}: {count} decoded frames; expected {frames}")
    numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
    if abs(numerator / denominator - fps) > 0.001:
        raise RuntimeError(f"{path.name}: incorrect frame rate")
    expected_duration = frames / fps
    if abs(float(info["format"]["duration"]) - expected_duration) > 1.0 / fps + 0.002:
        raise RuntimeError(f"{path.name}: duration mismatch")
    return info


def write_json_atomic(path: Path, data):
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data, indent=2))
    partial.replace(path)


def ffmpeg_encoder(path: Path, args):
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{args.width}x{args.height}",
        "-framerate", str(args.fps), "-i", "pipe:0", "-an",
        "-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-r", str(args.fps),
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-movflags", "+faststart", str(path),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shader", type=Path, default=PROJECT / "dist" / "cybr-computational-instrument.frag")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--seconds", type=float, default=26.0)
    parser.add_argument("--quality", type=float, default=1.0)
    parser.add_argument("--render-scale", type=float, default=1.0,
                        help="Render the real GLSL at this multiple, then Lanczos downsample to the requested movie dimensions")
    parser.add_argument("--exposure", type=float, default=1.0)
    parser.add_argument("--clock-offset", type=float, default=3.0)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--checkpoints", type=Path)
    args = parser.parse_args()
    if args.width % 2 or args.height % 2:
        parser.error("H.264 YUV420 output dimensions must be even")
    if args.seconds <= 0 or args.fps <= 0 or args.chunk_seconds <= 0:
        parser.error("Duration, frame rate, and chunk duration must be positive")
    if args.render_scale < 1.0 or args.render_scale > 4.0:
        parser.error("Render scale must be between 1 and 4")
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = (args.checkpoints or args.output.parent / (args.output.stem + "-checkpoints")).resolve()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = checkpoint_dir / "manifest.json"
    source_hash = hashlib.sha256(args.shader.read_bytes()).hexdigest()
    total_frames = round(args.seconds * args.fps)
    chunk_frames = max(1, round(args.chunk_seconds * args.fps))
    render_width = round(args.width * args.render_scale)
    render_height = round(args.height * args.render_scale)
    settings = {
        "source_sha256":source_hash, "width":args.width, "height":args.height,
        "fps":args.fps, "frames":total_frames, "seconds":args.seconds,
        "quality":args.quality, "exposure":args.exposure,
        "render_scale":args.render_scale, "render_width":render_width, "render_height":render_height,
        "clock_offset":args.clock_offset, "chunk_frames":chunk_frames,
        "crf":args.crf, "film_keys":FILM_KEYS,
    }
    # JSON-normalize tuples so a resumed manifest compares byte-for-byte.
    settings = json.loads(json.dumps(settings))
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("settings") != settings:
            raise RuntimeError("Checkpoint settings or shader differ. Use a new --checkpoints directory; existing completed work was preserved.")
    else:
        manifest = {"settings":settings, "chunks":[], "completed_frames":0, "render_seconds":0.0}
        write_json_atomic(manifest_path, manifest)

    completed = {item["index"]:item for item in manifest["chunks"]}
    chunk_count = math.ceil(total_frames / chunk_frames)
    start_wall = time.perf_counter()
    rendered_this_run = 0
    metadata = {}
    with NativeRenderer(args.shader) as renderer:
        metadata = renderer.metadata()
        print(json.dumps({"event":"started", "frames":total_frames, "chunks":chunk_count, "already_checkpointed":manifest["completed_frames"], **metadata}), flush=True)
        for chunk_index in range(chunk_count):
            first = chunk_index * chunk_frames
            count = min(chunk_frames, total_frames - first)
            destination = checkpoint_dir / f"chunk-{chunk_index:04d}.mp4"
            if chunk_index in completed:
                validate_video(destination, args.width, args.height, args.fps, count)
                print(json.dumps({"event":"reused", "chunk":chunk_index, "frames":count}), flush=True)
                continue
            partial = checkpoint_dir / f"chunk-{chunk_index:04d}.rendering.mp4"
            encoder = ffmpeg_encoder(partial, args)
            frame_hashes = []
            chunk_started = time.perf_counter()
            try:
                for frame_index in range(first, first + count):
                    seconds = frame_index / args.fps
                    chapter = film_chapter(seconds, args.seconds)
                    pixels = renderer.render(render_width, render_height, args.clock_offset + seconds, chapter, args.quality, args.exposure)
                    if (render_width, render_height) != (args.width, args.height):
                        encoded_rgb = Image.fromarray(pixels, "RGB").resize((args.width, args.height), Image.Resampling.LANCZOS).tobytes()
                    else:
                        encoded_rgb = pixels.tobytes()
                    frame_hashes.append(hashlib.sha256(encoded_rgb).hexdigest())
                    encoder.stdin.write(encoded_rgb)
                    rendered_this_run += 1
                    if (frame_index + 1) % 12 == 0:
                        elapsed = time.perf_counter() - start_wall
                        print(json.dumps({"event":"progress", "frame":frame_index+1, "total":total_frames, "chapter":round(chapter,4), "elapsed_seconds":round(elapsed,2), "seconds_per_new_frame":round(elapsed/max(rendered_this_run,1),3)}), flush=True)
                encoder.stdin.close()
                error = encoder.stderr.read().decode(errors="replace")
                returncode = encoder.wait()
                if returncode:
                    raise RuntimeError(f"FFmpeg chunk failed ({returncode}): {error}")
                info = validate_video(partial, args.width, args.height, args.fps, count)
                partial.replace(destination)
                item = {"index":chunk_index, "path":destination.name, "first_frame":first, "frames":count,
                        "frame_sha256":frame_hashes, "bytes":destination.stat().st_size,
                        "render_seconds":round(time.perf_counter()-chunk_started,4)}
                manifest["chunks"].append(item)
                manifest["chunks"].sort(key=lambda x:x["index"])
                manifest["completed_frames"] = sum(x["frames"] for x in manifest["chunks"])
                manifest["render_seconds"] = sum(x["render_seconds"] for x in manifest["chunks"])
                manifest["renderer"] = metadata
                write_json_atomic(manifest_path, manifest)
                print(json.dumps({"event":"checkpoint", "chunk":chunk_index, "completed_frames":manifest["completed_frames"], "bytes":item["bytes"]}), flush=True)
            except BaseException:
                try:
                    encoder.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    pass
                encoder.terminate()
                encoder.wait()
                raise

    if manifest["completed_frames"] != total_frames:
        raise RuntimeError("Refusing incomplete movie assembly")
    frame_hashes = [value for item in manifest["chunks"] for value in item["frame_sha256"]]
    if len(set(frame_hashes)) < total_frames * 0.95:
        raise RuntimeError("Too many identical shader frames; refusing to present repeated stills as animation")
    concat_file = checkpoint_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{item['path']}'\n" for item in manifest["chunks"]))
    partial_output = args.output.with_name(args.output.stem + ".assembling.mp4")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(partial_output),
    ], check=True)
    final_probe = validate_video(partial_output, args.width, args.height, args.fps, total_frames)
    partial_output.replace(args.output)
    result = {
        "output":str(args.output), "bytes":args.output.stat().st_size,
        "sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "unique_shader_frames":len(set(frame_hashes)), "frames":total_frames,
        "duration":total_frames / args.fps, "fps":args.fps,
        "width":args.width, "height":args.height,
        "total_render_seconds":manifest["render_seconds"],
        "settings":settings, "renderer":metadata, "probe":final_probe,
    }
    write_json_atomic(args.output.with_suffix(".json"), result)
    print(json.dumps({"event":"complete", **result}), flush=True)


if __name__ == "__main__":
    main()
