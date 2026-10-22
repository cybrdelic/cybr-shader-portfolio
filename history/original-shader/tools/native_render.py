#!/usr/bin/env python3
"""Render the actual portfolio fragment shader through surfaceless EGL / GLES3.

This is an offline presentation harness, not an alternate scene implementation.
It loads the same complete GLSL exported for FragCoord and the browser host.
No geometry, materials, camera, lettering, or visual assets are implemented here.
"""
from __future__ import annotations

import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
os.environ.setdefault("EGL_PLATFORM", "surfaceless")
os.environ.setdefault("LP_NUM_THREADS", "8")
os.environ.setdefault("MESA_SHADER_CACHE_DIR", str(PROJECT / ".mesa-cache"))

GL_VERTEX_SHADER = 0x8B31
GL_FRAGMENT_SHADER = 0x8B30
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_INFO_LOG_LENGTH = 0x8B84
GL_TEXTURE_2D = 0x0DE1
GL_RGBA8 = 0x8058
GL_RGBA = 0x1908
GL_UNSIGNED_BYTE = 0x1401
GL_FRAMEBUFFER = 0x8D40
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
GL_PACK_ALIGNMENT = 0x0D05
GL_TRIANGLES = 0x0004
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02

VERTEX_SOURCE = """#version 300 es
precision highp float;
void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

FRAGMENT_PREFIX = """#version 300 es
precision highp float;
precision highp int;
uniform vec2 u_resolution;
uniform float u_time;
uniform vec4 u_mouse;
uniform vec2 u_drag;
uniform float u_scroll;
out vec4 fragColor;
"""


def atomic_png(path: Path, rgb: np.ndarray) -> None:
    """Write a complete, decodable image before exposing its final filename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial.png")
    Image.fromarray(rgb, "RGB").save(partial)
    with Image.open(partial) as im:
        im.load()
        if im.size != (rgb.shape[1], rgb.shape[0]):
            raise RuntimeError("PNG dimensions changed during encoding")
    partial.replace(path)


class NativeRenderer:
    """Persistent GLES context for stills and genuine sequential video frames."""

    def __init__(self, shader: str | Path):
        if isinstance(shader, Path):
            self.source_path = shader.resolve()
            self.source = shader.read_text()
        elif "\n" not in shader and Path(shader).is_file():
            self.source_path = Path(shader).resolve()
            self.source = self.source_path.read_text()
        else:
            self.source_path = None
            self.source = str(shader)
        self.source_hash = hashlib.sha256(self.source.encode()).hexdigest()
        self.egl = C.CDLL(ctypes.util.find_library("EGL") or "libEGL.so.1")
        # libGL dispatch exposes the GLES entry points on this managed image.
        self.gl = C.CDLL(ctypes.util.find_library("GLESv2") or ctypes.util.find_library("GL") or "libGL.so.1")
        self.display = self.context = self.surface = None
        self.program = self.fbo = self.texture = self.vao = 0
        self.width = self.height = 0
        self.uniforms = {}
        self.started = time.perf_counter()
        self.first_draw = True
        self._declare_egl()
        self._create_context()
        self._declare_gl()
        self.renderer_name = self.gl.glGetString(GL_RENDERER).decode()
        self.gl_version = self.gl.glGetString(GL_VERSION).decode()
        self._stage("context", renderer=self.renderer_name)
        self._build_program()
        self._allocate_targets()

    def _stage(self, stage, **extra):
        if os.environ.get("CYBR_RENDER_QUIET") != "1":
            print(json.dumps({"event":"native_stage", "stage":stage,
                              "elapsed_seconds":round(time.perf_counter()-self.started,3), **extra}), flush=True)

    def _egl_fn(self, name, result, args):
        fn = getattr(self.egl, name)
        fn.restype, fn.argtypes = result, args
        return fn

    def _declare_egl(self):
        ptr, integer = C.c_void_p, C.c_int
        self._egl_fn("eglGetProcAddress", ptr, [C.c_char_p])
        self._egl_fn("eglInitialize", C.c_uint, [ptr, C.POINTER(integer), C.POINTER(integer)])
        self._egl_fn("eglBindAPI", C.c_uint, [C.c_uint])
        self._egl_fn("eglChooseConfig", C.c_uint, [ptr, C.POINTER(integer), C.POINTER(ptr), integer, C.POINTER(integer)])
        self._egl_fn("eglCreateContext", ptr, [ptr, ptr, ptr, C.POINTER(integer)])
        self._egl_fn("eglCreatePbufferSurface", ptr, [ptr, ptr, C.POINTER(integer)])
        self._egl_fn("eglMakeCurrent", C.c_uint, [ptr, ptr, ptr, ptr])
        self._egl_fn("eglDestroyContext", C.c_uint, [ptr, ptr])
        self._egl_fn("eglDestroySurface", C.c_uint, [ptr, ptr])
        self._egl_fn("eglTerminate", C.c_uint, [ptr])
        self._egl_fn("eglGetError", C.c_uint, [])

    def _egl_check(self, success, operation):
        if not success:
            raise RuntimeError(f"{operation}: EGL error 0x{self.egl.eglGetError():04x}")
        return success

    def _create_context(self):
        proc = self.egl.eglGetProcAddress(b"eglGetPlatformDisplayEXT")
        if not proc:
            raise RuntimeError("Surfaceless EGL platform extension is unavailable")
        platform_display = C.CFUNCTYPE(C.c_void_p, C.c_uint, C.c_void_p, C.POINTER(C.c_int))(proc)
        self.display = platform_display(0x31DD, None, None)  # EGL_PLATFORM_SURFACELESS_MESA
        major, minor = C.c_int(), C.c_int()
        self._egl_check(self.egl.eglInitialize(self.display, C.byref(major), C.byref(minor)), "eglInitialize")
        self._egl_check(self.egl.eglBindAPI(0x30A0), "eglBindAPI GLES")
        attrs = (C.c_int * 15)(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3025, 0, 0x3038)
        config, count = C.c_void_p(), C.c_int()
        self._egl_check(self.egl.eglChooseConfig(self.display, attrs, C.byref(config), 1, C.byref(count)), "eglChooseConfig")
        if count.value < 1:
            raise RuntimeError("No GLES3 pbuffer configuration")
        context_attrs = (C.c_int * 3)(0x3098, 3, 0x3038)
        self.context = self._egl_check(self.egl.eglCreateContext(self.display, config, None, context_attrs), "eglCreateContext")
        surface_attrs = (C.c_int * 5)(0x3057, 1, 0x3056, 1, 0x3038)
        self.surface = self._egl_check(self.egl.eglCreatePbufferSurface(self.display, config, surface_attrs), "eglCreatePbufferSurface")
        self._egl_check(self.egl.eglMakeCurrent(self.display, self.surface, self.surface, self.context), "eglMakeCurrent")

    def _gl_fn(self, name, result, args):
        try:
            fn = getattr(self.gl, name)
        except AttributeError:
            address = self.egl.eglGetProcAddress(name.encode())
            if not address:
                raise RuntimeError(f"Missing required GLES3 function {name}")
            fn = C.CFUNCTYPE(result, *args)(address)
            setattr(self.gl, name, fn)
        fn.restype, fn.argtypes = result, args
        return fn

    def _declare_gl(self):
        u, i, f, p = C.c_uint, C.c_int, C.c_float, C.c_void_p
        declarations = {
            "glGetString": (C.c_char_p, [u]),
            "glGetError": (u, []),
            "glCreateShader": (u, [u]),
            "glShaderSource": (None, [u, i, C.POINTER(C.c_char_p), C.POINTER(i)]),
            "glCompileShader": (None, [u]),
            "glGetShaderiv": (None, [u, u, C.POINTER(i)]),
            "glGetShaderInfoLog": (None, [u, i, C.POINTER(i), C.c_char_p]),
            "glDeleteShader": (None, [u]),
            "glCreateProgram": (u, []),
            "glAttachShader": (None, [u, u]),
            "glLinkProgram": (None, [u]),
            "glGetProgramiv": (None, [u, u, C.POINTER(i)]),
            "glGetProgramInfoLog": (None, [u, i, C.POINTER(i), C.c_char_p]),
            "glUseProgram": (None, [u]),
            "glDeleteProgram": (None, [u]),
            "glGetUniformLocation": (i, [u, C.c_char_p]),
            "glUniform1f": (None, [i, f]),
            "glUniform2f": (None, [i, f, f]),
            "glUniform4f": (None, [i, f, f, f, f]),
            "glGenVertexArrays": (None, [i, C.POINTER(u)]),
            "glBindVertexArray": (None, [u]),
            "glDeleteVertexArrays": (None, [i, C.POINTER(u)]),
            "glGenFramebuffers": (None, [i, C.POINTER(u)]),
            "glBindFramebuffer": (None, [u, u]),
            "glDeleteFramebuffers": (None, [i, C.POINTER(u)]),
            "glGenTextures": (None, [i, C.POINTER(u)]),
            "glBindTexture": (None, [u, u]),
            "glTexImage2D": (None, [u, i, i, i, i, i, u, u, p]),
            "glTexParameteri": (None, [u, u, i]),
            "glDeleteTextures": (None, [i, C.POINTER(u)]),
            "glFramebufferTexture2D": (None, [u, u, u, u, i]),
            "glCheckFramebufferStatus": (u, [u]),
            "glViewport": (None, [i, i, i, i]),
            "glPixelStorei": (None, [u, i]),
            "glReadPixels": (None, [i, i, i, i, u, u, p]),
            "glDrawArrays": (None, [u, i, i]),
            "glFinish": (None, []),
            "glDisable": (None, [u]),
        }
        for name, (result, args) in declarations.items():
            self._gl_fn(name, result, args)

    def _compile_shader(self, kind, source):
        shader = self.gl.glCreateShader(kind)
        data = source.encode()
        c_source = C.c_char_p(data)
        length = C.c_int(len(data))
        self.gl.glShaderSource(shader, 1, C.byref(c_source), C.byref(length))
        self.gl.glCompileShader(shader)
        ok = C.c_int()
        self.gl.glGetShaderiv(shader, GL_COMPILE_STATUS, C.byref(ok))
        if not ok.value:
            log_length = C.c_int()
            self.gl.glGetShaderiv(shader, GL_INFO_LOG_LENGTH, C.byref(log_length))
            log = C.create_string_buffer(max(1, log_length.value))
            self.gl.glGetShaderInfoLog(shader, len(log), None, log)
            self.gl.glDeleteShader(shader)
            raise RuntimeError("Shader compile failed:\n" + log.value.decode(errors="replace"))
        return shader

    def _build_program(self):
        self._stage("compiling_glsl", source_bytes=len(self.source.encode()))
        vertex = self._compile_shader(GL_VERTEX_SHADER, VERTEX_SOURCE)
        fragment = self._compile_shader(GL_FRAGMENT_SHADER, FRAGMENT_PREFIX + self.source)
        self._stage("glsl_compiled")
        self.program = self.gl.glCreateProgram()
        self.gl.glAttachShader(self.program, vertex)
        self.gl.glAttachShader(self.program, fragment)
        self.gl.glLinkProgram(self.program)
        self._stage("program_linked")
        self.gl.glDeleteShader(vertex)
        self.gl.glDeleteShader(fragment)
        ok = C.c_int()
        self.gl.glGetProgramiv(self.program, GL_LINK_STATUS, C.byref(ok))
        if not ok.value:
            log_length = C.c_int()
            self.gl.glGetProgramiv(self.program, GL_INFO_LOG_LENGTH, C.byref(log_length))
            log = C.create_string_buffer(max(1, log_length.value))
            self.gl.glGetProgramInfoLog(self.program, len(log), None, log)
            raise RuntimeError("Program link failed:\n" + log.value.decode(errors="replace"))
        self.gl.glUseProgram(self.program)
        for name in ("u_resolution", "u_time", "u_mouse", "u_drag", "u_scroll", "u_chapter", "u_exposure", "u_quality", "u_tour", "u_pick"):
            self.uniforms[name] = self.gl.glGetUniformLocation(self.program, name.encode())

    def _allocate_targets(self):
        vao, fbo, texture = C.c_uint(), C.c_uint(), C.c_uint()
        self.gl.glGenVertexArrays(1, C.byref(vao))
        self.gl.glGenFramebuffers(1, C.byref(fbo))
        self.gl.glGenTextures(1, C.byref(texture))
        self.vao, self.fbo, self.texture = vao.value, fbo.value, texture.value
        self.gl.glBindVertexArray(self.vao)
        self.gl.glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        self.gl.glBindTexture(GL_TEXTURE_2D, self.texture)
        self.gl.glTexParameteri(GL_TEXTURE_2D, 0x2801, 0x2600)  # min: nearest
        self.gl.glTexParameteri(GL_TEXTURE_2D, 0x2800, 0x2600)  # mag: nearest
        self.gl.glPixelStorei(GL_PACK_ALIGNMENT, 1)
        self.gl.glDisable(0x0BD0)  # Dithering off, shader owns stable display dither.

    def _resize(self, width, height):
        if (width, height) == (self.width, self.height):
            return
        if width <= 0 or height <= 0:
            raise ValueError("Render dimensions must be positive")
        self.width, self.height = int(width), int(height)
        self.gl.glBindTexture(GL_TEXTURE_2D, self.texture)
        self.gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        self.gl.glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.texture, 0)
        status = self.gl.glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError(f"Incomplete render framebuffer: 0x{status:x}")
        self.gl.glViewport(0, 0, self.width, self.height)
        self.pixels = np.empty((self.height, self.width, 4), dtype=np.uint8)

    def _one(self, name, value):
        location = self.uniforms.get(name, -1)
        if location >= 0:
            self.gl.glUniform1f(location, float(value))

    def render(self, width, height, time=0.0, chapter=0.0, quality=1.0, exposure=1.0, pick=0.0, drag=(0.0, 0.0)):
        self._resize(int(width), int(height))
        self.gl.glUseProgram(self.program)
        self.gl.glUniform2f(self.uniforms["u_resolution"], self.width, self.height)
        for name, value in {"u_time":time, "u_chapter":chapter, "u_quality":quality, "u_exposure":exposure, "u_pick":pick, "u_scroll":0.0, "u_tour":0.0}.items():
            self._one(name, value)
        if self.uniforms.get("u_drag", -1) >= 0:
            self.gl.glUniform2f(self.uniforms["u_drag"], *drag)
        if self.uniforms.get("u_mouse", -1) >= 0:
            self.gl.glUniform4f(self.uniforms["u_mouse"], self.width * 0.5, self.height * 0.5, -1.0, -1.0)
        if self.first_draw:
            self._stage("first_draw_jit", width=self.width, height=self.height)
        self.gl.glDrawArrays(GL_TRIANGLES, 0, 3)
        self.gl.glReadPixels(0, 0, self.width, self.height, GL_RGBA, GL_UNSIGNED_BYTE, self.pixels.ctypes.data_as(C.c_void_p))
        error = self.gl.glGetError()
        if error:
            raise RuntimeError(f"GLES render error: 0x{error:04x}")
        if self.first_draw:
            self._stage("first_frame_complete")
            self.first_draw = False
        return np.ascontiguousarray(self.pixels[::-1, :, :3])

    def metadata(self):
        return {"renderer":self.renderer_name, "gl_version":self.gl_version, "source_sha256":self.source_hash, "source_bytes":len(self.source.encode())}

    def close(self):
        if not self.display:
            return
        if self.program:
            self.gl.glDeleteProgram(self.program)
        for attr, fn in (("vao", "glDeleteVertexArrays"), ("fbo", "glDeleteFramebuffers"), ("texture", "glDeleteTextures")):
            value = C.c_uint(getattr(self, attr, 0))
            if value.value:
                getattr(self.gl, fn)(1, C.byref(value))
        self.egl.eglMakeCurrent(self.display, None, None, None)
        self.egl.eglDestroySurface(self.display, self.surface)
        self.egl.eglDestroyContext(self.display, self.context)
        self.egl.eglTerminate(self.display)
        self.display = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shader", type=Path, default=PROJECT / "dist" / "cybr-computational-instrument.frag")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--time", type=float, default=3.0)
    parser.add_argument("--chapter", type=float, default=0.0)
    parser.add_argument("--quality", type=float, default=1.0)
    parser.add_argument("--exposure", type=float, default=1.0)
    parser.add_argument("--pick", type=float, default=0.0)
    args = parser.parse_args()
    start = time.perf_counter()
    with NativeRenderer(args.shader) as renderer:
        compiled = time.perf_counter()
        pixels = renderer.render(args.width, args.height, args.time, args.chapter, args.quality, args.exposure, args.pick)
        atomic_png(args.output, pixels)
        metadata = renderer.metadata() | {"width":args.width, "height":args.height, "time":args.time, "chapter":args.chapter, "quality":args.quality, "compile_seconds":compiled-start, "render_seconds":time.perf_counter()-compiled, "output":str(args.output.resolve())}
        args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
        print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
