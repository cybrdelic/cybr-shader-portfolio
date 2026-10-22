"""Restore byte-identical caches from verified transport parts (Python 3 stdlib)."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'transport' / 'cache-parts.json'
CHUNK = 1024 * 1024


def local_path(value):
    if not isinstance(value, str):
        raise ValueError('Manifest paths must be strings.')
    rel = PurePosixPath(value)
    if not rel.parts or rel.is_absolute() or '..' in rel.parts or '\\' in value:
        raise ValueError('Unsafe manifest path: ' + value)
    path = ROOT.joinpath(*rel.parts)
    for component in [path, *path.parents]:
        if component == ROOT:
            break
        if component.is_symlink():
            raise ValueError('Refusing symlink in cache path: ' + value)
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError('Cache path leaves repository: ' + value)
    return path


def signature(path):
    size = 0
    sha = hashlib.sha256()
    with path.open('rb') as source:
        for data in iter(lambda: source.read(CHUNK), b''):
            size += len(data)
            sha.update(data)
    return size, sha.hexdigest()


def expected(item):
    size, sha = item.get('bytes'), item.get('sha256')
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError('Invalid expected byte count.')
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('Invalid expected SHA-256.')
    return size, sha


def restore():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('schema') != 'lossless-cache-transport/v1':
        raise ValueError('Unsupported transport manifest.')
    jobs = []
    seen = set()
    # Check every target and part before writing anything.
    for entry in manifest['files']:
        target = local_path(entry['path'])
        wanted = expected(entry)
        if target in seen:
            raise ValueError('Duplicate cache target: ' + entry['path'])
        seen.add(target)
        exists = target.exists()
        if exists and (not target.is_file() or signature(target) != wanted):
            raise FileExistsError('Refusing to overwrite differing existing file: ' + entry['path'])
        parts = []
        part_bytes = 0
        for part in entry['parts']:
            source = local_path(part['path'])
            part_expected = expected(part)
            if source == target or part_expected[0] > 8 * 1024 * 1024:
                raise ValueError('Invalid transport part: ' + part['path'])
            if signature(source) != part_expected:
                raise ValueError('Transport part integrity failure: ' + part['path'])
            parts.append((source, part_expected))
            part_bytes += part_expected[0]
        if not parts or part_bytes != wanted[0]:
            raise ValueError('Transport part sizes do not match cache: ' + entry['path'])
        jobs.append((target, wanted, parts, exists))
    restored = 0
    already_present = 0
    for target, wanted, parts, exists in jobs:
        if exists:
            already_present += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', prefix='.' + target.name + '.restore-', dir=target.parent, delete=False) as out:
                temporary = Path(out.name)
                total = 0
                whole = hashlib.sha256()
                for source, part_expected in parts:
                    part_size = 0
                    part_sha = hashlib.sha256()
                    with source.open('rb') as src:
                        for data in iter(lambda: src.read(CHUNK), b''):
                            out.write(data)
                            total += len(data)
                            whole.update(data)
                            part_size += len(data)
                            part_sha.update(data)
                    if (part_size, part_sha.hexdigest()) != part_expected:
                        raise ValueError('Transport part changed during restoration: ' + str(source.relative_to(ROOT)))
                if (total, whole.hexdigest()) != wanted:
                    raise ValueError('Restored cache integrity failure: ' + str(target.relative_to(ROOT)))
            # Linking is atomic and never replaces an existing destination.
            try:
                os.link(temporary, target)
                restored += 1
            except FileExistsError:
                if target.is_symlink() or not target.is_file() or signature(target) != wanted:
                    raise FileExistsError('Refusing to overwrite differing existing file: ' + str(target.relative_to(ROOT)))
                already_present += 1
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    print(f'Verified {len(jobs)} caches: restored {restored}; already exact {already_present}.')


if __name__ == '__main__':
    if len(sys.argv) != 1:
        raise SystemExit('Usage: python restore_assets.py')
    try:
        restore()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
