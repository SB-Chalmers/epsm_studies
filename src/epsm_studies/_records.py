# SPDX-License-Identifier: MIT
"""Small strict JSON and publication helpers for Studies-owned formats."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


def _check_keys(value):
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Portable record keys must be strings")
        for item in value.values():
            _check_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _check_keys(item)


def canonical(value):
    _check_keys(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def checksum(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON field: {key}")
        value[key] = item
    return value


def _nonfinite(value):
    raise ValueError(f"Nonfinite JSON value: {value}")


def _finite_float(value):
    import math
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Nonfinite JSON value: {value}")
    return number


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=_unique, parse_constant=_nonfinite, parse_float=_finite_float)


def publish_json(path, value):
    """Publish finite UTF-8 JSON exclusively; never replace existing evidence."""
    content = canonical(value) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def relative_path(root, name):
    """Resolve a relative archive reference, rejecting traversal and symlinks."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("Artifact reference must be a nonempty relative path")
    if ".." in Path(name).parts:
        raise ValueError("Artifact reference escapes its archive")
    root = Path(root).resolve()
    path = root / name
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("Archive artifacts must not use symlinks")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Artifact reference escapes its archive")
    return path


def short(value, width=60):
    value = str(value)
    while len(repr(value)) > width:
        value = value[: max(0, len(value) - 4)] + "…"
    return repr(value)
