"""Run unchanged baker sampling on one synthetic triangle, never the full scene."""
import math, os, struct, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="cybr-baker-") as scratch:
    root = Path(scratch)
    source = root / "triangle.bin"
    points = [(0., 0., 0.), (1., 0., 0.), (0., 0., 1.)]
    source.write_bytes(struct.pack("<4sIII", b"CYBR", 3, 3, 28) + b"".join(
        struct.pack("<3f3h", *point, 0, 32767, 0) + bytes([13,255,0,0,255,255,0,0,0,0])
        for point in points) + struct.pack("<3I", 0, 1, 2))
    for executable, size in [(sys.argv[1], source.stat().st_size), (sys.argv[2], 36)]:
        outputs = []
        for threads in (1, 2):
            target = root / (Path(executable).stem + str(threads) + ".bin")
            env = dict(os.environ, OMP_NUM_THREADS=str(threads))
            subprocess.run([executable, str(source), str(target)], env=env, check=True, timeout=30)
            data = target.read_bytes()
            assert len(data) == size, (executable, len(data), size)
            outputs.append(data)
        assert outputs[0] == outputs[1], "Thread counts changed deterministic results"
        if size == 36:
            assert all(math.isfinite(value) and value >= 0 for value in struct.unpack("<9f", outputs[0]))
        else:
            # Geometry, normals, materials and indices remain exactly unchanged.
            original = source.read_bytes()
            changed = {16 + vertex * 28 + channel for vertex in range(3) for channel in (19, 22, 23)}
            assert all(a == b or index in changed for index, (a, b) in enumerate(zip(original, outputs[0])))
    print("Both native bakers passed bounded, deterministic one/two-thread execution.")
