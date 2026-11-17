# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-CRYPTO-001.6
# ****

"""Safe OCI layer flattening and boot-set selection (ER-UTIL-001 FR-4.1)."""

from __future__ import annotations

import contextlib
import json
import os
import posixpath
import shutil
import subprocess
import tarfile
from typing import Iterable, Iterator

WHITEOUT_PREFIX = ".wh."
OPAQUE_MARKER = ".wh..wh..opq"
MAX_SYMLINK_HOPS = 40


class UnsafeLayerError(Exception):
    """A layer entry would write outside the extraction root."""


class BootSetError(Exception):
    """The image does not hold a usable boot set."""


class UnsupportedLayerError(Exception):
    """A layer uses a media type or compressor this utility cannot read."""


TAR_EXTRACT_OPTS = ["--numeric-owner", "--xattrs", "--xattrs-include=*", "--acls", "--exclude=.wh.*"]


def _normalize(name: str) -> str:
    """Normalize an archive path; reject absolute or escaping names."""
    if name.startswith("/") or os.path.isabs(name):
        raise UnsafeLayerError(f"absolute path in layer: {name}")
    norm = posixpath.normpath(name)
    if norm == ".." or norm.startswith("../"):
        raise UnsafeLayerError(f"path escapes the extraction root: {name}")
    return "" if norm == "." else norm


def resolve_in_root(root: str, rel: str, strict_absolute: bool = True) -> str:
    """Resolve rel under root following on-disk symlinks; raise if it leaves root.

    Absolute symlink targets are rejected when strict_absolute is set, because tar
    would follow them on the host while extracting.
    """
    parts = [p for p in rel.split("/") if p]
    resolved: list[str] = []
    hops = 0
    while parts:
        part = parts.pop(0)
        if part == "..":
            if not resolved:
                raise UnsafeLayerError(f"path escapes the extraction root: {rel}")
            resolved.pop()
            continue
        candidate = os.path.join(root, *resolved, part)
        if os.path.islink(candidate):
            hops += 1
            if hops > MAX_SYMLINK_HOPS:
                raise UnsafeLayerError(f"too many symlink hops resolving: {rel}")
            target = os.readlink(candidate)
            if target.startswith("/"):
                if strict_absolute:
                    raise UnsafeLayerError(f"path traverses absolute symlink '{part}': {rel}")
                resolved = []
            parts = [p for p in target.split("/") if p] + parts
        else:
            resolved.append(part)
    return os.path.join(root, *resolved)


def check_member(member: tarfile.TarInfo, root: str, layer_symlinks: set[str]) -> str:
    """Validate one layer entry and return its normalized path."""
    path = _normalize(member.name)
    if not path:
        return path
    parent = posixpath.dirname(path)
    parts = parent.split("/") if parent else []
    for idx in range(len(parts)):
        if "/".join(parts[: idx + 1]) in layer_symlinks:
            raise UnsafeLayerError(
                f"entry written through a symlink created in the same layer: {member.name}")
    resolve_in_root(root, parent)
    if member.issym():
        if not member.linkname.startswith("/"):
            joined = posixpath.normpath(posixpath.join(parent, member.linkname))
            if joined == ".." or joined.startswith("../"):
                raise UnsafeLayerError(f"symlink escapes the extraction root: {member.name}")
        layer_symlinks.add(path)
    elif member.islnk():
        _normalize(member.linkname)
    return path


def apply_whiteouts(root: str, paths: Iterable[str]) -> int:
    """Delete lower-layer content named by whiteout markers; return count applied."""
    applied = 0
    for path in paths:
        base = posixpath.basename(path)
        parent = posixpath.dirname(path)
        parent_abs = resolve_in_root(root, parent)
        if base == OPAQUE_MARKER:
            if os.path.isdir(parent_abs):
                for child in os.listdir(parent_abs):
                    _remove(os.path.join(parent_abs, child))
            applied += 1
        elif base.startswith(WHITEOUT_PREFIX):
            _remove(os.path.join(parent_abs, base[len(WHITEOUT_PREFIX):]))
            applied += 1
    return applied


def _remove(path: str) -> None:
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def compression_for(media_type: str) -> str:
    """Map a layer media type from the image manifest to a decompression method.

    Returns "zstd" for zstd-compressed tar layers and "auto" for gzip or uncompressed tar
    layers, which tar detects itself. Any other media type is rejected.
    """
    kind = media_type.lower()
    if "tar" in kind:
        if kind.endswith("zstd"):
            return "zstd"
        if kind.endswith(("gzip", "gz", "tar")):
            return "auto"
    raise UnsupportedLayerError(f"unsupported layer media type: {media_type}")


@contextlib.contextmanager
def _open_layer(layer: str, compression: str) -> Iterator[tarfile.TarFile]:
    """Open one layer for scanning; zstd layers are streamed through the zstd binary."""
    if compression != "zstd":
        with tarfile.open(layer, "r:*") as tar:
            yield tar
        return
    proc = subprocess.Popen(["zstd", "-dc", layer], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            yield tar
    finally:
        proc.stdout.close()
        rc = proc.wait()
    if rc:
        raise UnsupportedLayerError(f"zstd failed to decompress a layer (exit {rc})")


def _extract_layer(layer: str, root: str, compression: str) -> None:
    """Apply one layer into root with ownership, xattrs and ACLs preserved."""
    if compression != "zstd":
        subprocess.run(["tar", "-xpf", layer, "-C", root, *TAR_EXTRACT_OPTS],
                       check=True, capture_output=True)
        return
    zst = subprocess.Popen(["zstd", "-dc", layer], stdout=subprocess.PIPE)
    untar = subprocess.run(["tar", "-xpf", "-", "-C", root, *TAR_EXTRACT_OPTS],
                           stdin=zst.stdout, capture_output=True, check=False)
    zst.stdout.close()
    rc = zst.wait()
    if rc or untar.returncode:
        raise subprocess.CalledProcessError(untar.returncode or rc, ["tar"], stderr=untar.stderr)


def read_layers(image_tar: str, scratch: str) -> list[str]:
    """Extract manifest.json and the layer blobs from the exported archive, in order."""
    os.makedirs(scratch, exist_ok=True)
    with tarfile.open(image_tar) as outer:
        names = {m.name for m in outer.getmembers()}
        if "manifest.json" not in names:
            raise UnsafeLayerError("manifest.json not found in the exported image archive")
        manifest = json.load(outer.extractfile("manifest.json"))
        layers = manifest[0]["Layers"]
        out = []
        for layer in layers:
            safe = _normalize(layer)
            if safe not in names:
                raise UnsafeLayerError(
                    f"layer listed in manifest but missing from archive: {layer}")
            outer.extract(safe, scratch, filter="data")
            out.append(os.path.join(scratch, safe))
        return out


def flatten_layers(layer_files: list[str], root: str, media_types: list[str] | None = None) -> dict:
    """Apply layers in order with whiteout semantics into root.

    media_types, when given, holds the manifest media type of each layer in the same order.
    """
    os.makedirs(root, exist_ok=True)
    compressions = [compression_for(m) for m in media_types] if media_types else ["auto"] * len(layer_files)
    if len(compressions) != len(layer_files):
        raise UnsupportedLayerError("layer media types do not match the layers in the image")
    if "zstd" in compressions and shutil.which("zstd") is None:
        raise UnsupportedLayerError("zstd layers are present but the zstd binary is not installed on the OIM")
    whiteouts = 0
    entries = 0
    for layer, compression in zip(layer_files, compressions):
        layer_symlinks: set[str] = set()
        markers = []
        with _open_layer(layer, compression) as tar:
            for member in tar:
                path = check_member(member, root, layer_symlinks)
                entries += 1
                if posixpath.basename(path).startswith(WHITEOUT_PREFIX):
                    markers.append(path)
        whiteouts += apply_whiteouts(root, markers)
        _extract_layer(layer, root, compression)
    return {"layers": len(layer_files), "entries": entries, "whiteouts": whiteouts}


def _modules_dir_exists(root: str, version: str) -> bool:
    for rel in (f"usr/lib/modules/{version}", f"lib/modules/{version}"):
        try:
            if os.path.isdir(resolve_in_root(root, rel, strict_absolute=False)):
                return True
        except UnsafeLayerError:
            continue
    return False


def select_boot_set(root: str, kernel_version: str = "") -> dict:
    """Pick the single complete boot set, or the explicitly requested one."""
    boot = resolve_in_root(root, "boot", strict_absolute=False)
    names = sorted(os.listdir(boot)) if os.path.isdir(boot) else []
    versions = [n[len("vmlinuz-"):] for n in names
                if n.startswith("vmlinuz-") and "rescue" not in n
                and not n.endswith("+debug")]
    if not versions:
        raise BootSetError("kernel not found in OCI image: no vmlinuz-* in /boot "
                           "(rescue and debug kernels are excluded)")
    status = {}
    for ver in versions:
        if not os.path.isfile(os.path.join(boot, f"initramfs-{ver}.img")):
            status[ver] = "initramfs not found in OCI image"
        elif not _modules_dir_exists(root, ver):
            status[ver] = f"/lib/modules/{ver} directory not found in OCI image"
    complete = [v for v in versions if v not in status]
    if kernel_version:
        if kernel_version not in complete:
            reason = status.get(kernel_version, "kernel version not present in /boot")
            raise BootSetError(
                f"kernel_version '{kernel_version}' is not a complete boot set ({reason}); "
                f"available complete versions: {', '.join(complete) or 'none'}")
        chosen = kernel_version
    elif not complete:
        first = versions[0]
        raise BootSetError(
            status[first] if len(versions) == 1
            else "no complete boot set: " + "; ".join(f"{v}: {r}" for v, r in status.items()))
    elif len(complete) > 1:
        raise BootSetError("multiple complete boot sets found: " + ", ".join(complete)
                           + "; set kernel_version in the image mapping to choose one")
    else:
        chosen = complete[0]
    return {"kernel_version": chosen, "candidates": versions, "complete": complete,
            "kernel_path": os.path.join(boot, f"vmlinuz-{chosen}"),
            "initrd_path": os.path.join(boot, f"initramfs-{chosen}.img")}
