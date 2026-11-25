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


"""Empty the NFS shares of storage_config.yml before a clean reinstall.

The orchestrator cleanup detaches a share (unmount and remove its fstab entry) but does not
empty the export, and stale data in the Slurm and Kubernetes shares survives a reinstall. The
``nfs_shares`` suite of the orchestrator cleanup FVT therefore checks the detachment and
empties the shares (``cleanup_slurm`` and ``cleanup_k8s`` of test_config.yml select them):

1. the suite first checks that the share is unmounted and has no fstab entry; the share is
   emptied only when it is (``nfs_cleanup_func``);
2. the share is mounted read-only and unmounted again (preflight): a share that cannot be
   reached fails the cleanup before anything is deleted;
3. it is mounted read-write on a private temporary folder, emptied completely (the export
   itself stays) and unmounted again; the mount is never added to fstab;
4. it is mounted read-only once more and must hold no entry; otherwise steps 3 and 4 are
   repeated, up to ``CLEANUP_ATTEMPTS`` times.

Safety (the lessons of the product's own security fixes):

* no shell: every command is an argument list, with ``--`` before the operands;
* ``host:/export`` is checked before use (an IPv4 address or a host name, an absolute path
  of plain characters without ``.`` or ``..``), and system directories are never emptied
  (the deny list of omnia.sh); an export on this OIM that holds the checkout, the data
  path or the Omnia checkout is refused;
* the mount point is a new private folder (mode 0700, unpredictable name); after mounting
  it is checked in /proc/self/mountinfo to be an NFS mount of exactly that source, and
  nothing is deleted otherwise;
* deletion works relative to open directory descriptors, never follows a symbolic link
  (the link itself is removed), does not cross into another mount and has a depth limit;
* the share is always unmounted (lazily as a last resort); a mount that cannot be removed
  is reported, and its folder is left alone.

Standard library only (mount, umount, mount.nfs of nfs-utils).
"""

import os
import re
import socket
import stat
import subprocess  # nosec B404  # fixed argument lists, no shell
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Tuple

import yaml

from ..messages.nfs_msgs import NFS_MSGS

from ..vars.nfs_vars import (
    CLEANUP_ATTEMPTS,
    NFSD_CLIENTS_DIR,
    COMMAND_ENV,
    DENIED_EXPORTS,
    EXPORT_RE,
    HOST_RE,
    IPV4_RE,
    MAX_DEPTH,
    MAX_ERRORS,
    MOUNT_OPTIONS,
    MOUNT_ROOT,
    MOUNT_TIMEOUT,
    RETRY_PAUSE_SECONDS,
    UNMOUNT_TIMEOUT,
)
Emit = Callable[[str], None]



class NfsError(RuntimeError):
    """A share cannot be emptied; the message says why and how to fix it."""


def configured_mounts(path: str, emit: Emit) -> Dict[str, Dict[str, str]]:
    """Return {mount name: {"source", "mount_point"}} of the ``mounts`` of storage_config.yml.

    ``mount_point`` is "" when the entry has none. The result is {} when there are no mounts.
    """
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
    except OSError:
        emit(NFS_MSGS["no_storage_config"].format(path=path))
        return {}
    except yaml.YAMLError as exc:
        raise NfsError(f"{path} is not valid YAML: {exc}") from exc
    mounts = data.get("mounts") if isinstance(data, dict) else None
    return {str(item["name"]): {"source": item["source"],
                                "mount_point": str(item.get("mount_point") or "")}
            for item in (mounts or [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
            and isinstance(item.get("source"), str)}


def looks_like_nfs(source: str) -> bool:
    """Return whether ``source`` is host:/path (not a device, UUID or //cifs/share)."""
    return not source.startswith(("/", "UUID=", "LABEL=", "//")) and ":/" in source


def parse_source(name: str, source: str) -> Tuple[str, str]:
    """Return (host, export) of ``host:/export``, or raise NfsError.

    The host is an IPv4 address or a host name; the export an absolute path of plain
    characters without ``.`` or ``..`` components, and not a system directory.
    """
    host, _, export = source.partition(":")
    ip = IPV4_RE.fullmatch(host)
    if ip and any(int(part) > 255 for part in ip.groups()):
        raise NfsError(NFS_MSGS["bad_source"].format(name=name, why=f"{host!r} is not an IP"))
    if not HOST_RE.fullmatch(host) or len(host) > 253:
        raise NfsError(NFS_MSGS["bad_source"].format(
            name=name, why=f"the server {host!r} is not an IPv4 address or a host name"))
    if not EXPORT_RE.fullmatch(export) or {".", ".."} & set(export.split("/")):
        raise NfsError(NFS_MSGS["bad_source"].format(
            name=name, why=f"the export path {export!r} must be absolute, of letters, digits "
                           "and _ . @ + = : - only, without . or .. parts"))
    if export in DENIED_EXPORTS:
        raise NfsError(NFS_MSGS["denied"].format(name=name, export=export))
    return host, export


def _is_local(host: str) -> bool:
    """Return whether ``host`` is an address of this machine (a bind to it succeeds)."""
    try:
        address = socket.gethostbyname(host)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((address, 0))
        return True
    except OSError:
        return False


def _check_protected(name: str, host: str, export: str, protected: List[str]) -> None:
    """Refuse an export on this OIM that holds a path Omnia needs."""
    if not _is_local(host):
        return
    for path in protected:
        real = os.path.realpath(path)
        for root in (export, os.path.realpath(export)):
            if real == root or real.startswith(root.rstrip("/") + "/"):
                raise NfsError(NFS_MSGS["protected"].format(name=name, export=export, path=path))


def _run(argv: List[str], timeout: int) -> subprocess.CompletedProcess:
    """Run a command without a shell and with a fixed environment."""
    try:
        return subprocess.run(  # nosec B603  # argument list, no shell, fixed environment
            argv, capture_output=True, text=True, timeout=timeout, check=False,
            env=COMMAND_ENV)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", f"timed out after {timeout}s")
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", exc.strerror or str(exc))


def _mountinfo(mountpoint: str) -> Tuple[str, str]:
    """Return (fstype, source) of the mount at ``mountpoint`` ("", "" when none)."""
    target = os.path.realpath(mountpoint)
    try:
        with open("/proc/self/mountinfo", "r", encoding="utf-8") as stream:
            lines = stream.read().splitlines()
    except OSError:
        return "", ""
    found = ("", "")
    for line in lines:  # the last mount at a path wins
        left, _, right = line.partition(" - ")
        fields, tail = left.split(), right.split()
        if len(fields) > 4 and fields[4] == target and len(tail) > 1:
            found = (tail[0], tail[1])
    return found


def _unmount(name: str, mountpoint: str, emit: Emit) -> None:
    """Unmount and remove the private mount point; raise NfsError when it stays mounted."""
    result = _run(["umount", "--", mountpoint], UNMOUNT_TIMEOUT)
    if result.returncode != 0 and os.path.ismount(mountpoint):
        reason = (result.stderr or "").strip() or f"rc={result.returncode}"
        emit(NFS_MSGS["lazy_unmount"].format(mountpoint=mountpoint, reason=reason))
        result = _run(["umount", "-l", "--", mountpoint], UNMOUNT_TIMEOUT)
    if os.path.ismount(mountpoint):
        raise NfsError(NFS_MSGS["unmount_failed"].format(
            name=name, mountpoint=mountpoint, reason=(result.stderr or "").strip() or "busy"))
    emit(NFS_MSGS["unmount"].format(mountpoint=mountpoint))
    try:
        os.rmdir(mountpoint)
    except OSError:
        pass


@contextmanager
def mounted(share: Tuple[str, str, str], read_only: bool, emit: Emit,
            protected: List[str]) -> Iterator[str]:
    """Mount a share (name, share key, source) on a new private folder; yield it;
    always unmount.

    Raises:
        NfsError: Not root, no mount.nfs, an invalid or protected source, the mount fails or
            is not the NFS mount of ``source``.
    """
    name, flag, source = share
    if os.geteuid() != 0:
        raise NfsError(NFS_MSGS["need_root"])
    if not any(os.access(os.path.join(directory, "mount.nfs"), os.X_OK)
               for directory in COMMAND_ENV["PATH"].split(":")):
        raise NfsError(NFS_MSGS["no_mount_nfs"])
    host, export = parse_source(name, source)
    _check_protected(name, host, export, protected)
    mountpoint = tempfile.mkdtemp(prefix="omnia-nfs-", dir=MOUNT_ROOT if os.path.isdir(
        MOUNT_ROOT) else None)
    mode = "read-only" if read_only else "read-write"
    emit(NFS_MSGS["mount"].format(source=source, mountpoint=mountpoint, mode=mode))
    result = _run(["mount", "-t", "nfs", "-o", f"{MOUNT_OPTIONS},{'ro' if read_only else 'rw'}",
                   "--", f"{host}:{export}", mountpoint], MOUNT_TIMEOUT)
    try:
        if result.returncode != 0:
            raise NfsError(NFS_MSGS["mount_failed"].format(
                name=name, source=source, flag=flag,
                reason=(result.stderr or "").strip() or f"rc={result.returncode}"))
        fstype, found = _mountinfo(mountpoint)
        if not (fstype.startswith("nfs") and found == f"{host}:{export}"):
            raise NfsError(NFS_MSGS["mount_mismatch"].format(
                name=name, mountpoint=mountpoint, source=source,
                found=f"{fstype or 'nothing'} {found}".strip()))
        yield mountpoint
    finally:
        if os.path.ismount(mountpoint) or result.returncode == 0:
            _unmount(name, mountpoint, emit)
        else:
            try:
                os.rmdir(mountpoint)
            except OSError:
                pass


def _empty_directory(dir_fd: int, device: int, stats: Dict[str, int], errors: List[str],
                     depth: int = 0) -> None:
    """Remove everything inside the open directory ``dir_fd``, without following links."""
    if depth > MAX_DEPTH:
        errors.append(NFS_MSGS["too_deep"].format(depth=MAX_DEPTH))
        return
    with os.scandir(dir_fd) as scanner:
        names = [entry.name for entry in scanner]
    for name in names:
        try:
            info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                os.unlink(name, dir_fd=dir_fd)
                stats["files"] += 1
                stats["bytes"] += info.st_size if stat.S_ISREG(info.st_mode) else 0
            elif info.st_dev != device:
                stats["other_mounts"] += 1
            else:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=dir_fd)
                try:
                    _empty_directory(child, device, stats, errors, depth + 1)
                finally:
                    os.close(child)
                os.rmdir(name, dir_fd=dir_fd)
                stats["dirs"] += 1
        except OSError as exc:
            stats["errors"] += 1
            if len(errors) < MAX_ERRORS:
                errors.append(f"{name}: {exc.strerror or exc}")


def empty_directory(path: str) -> Dict[str, Any]:
    """Remove everything inside ``path`` (not ``path`` itself); return the counts and errors.

    Never follows a symbolic link, never leaves the filesystem of ``path``.
    """
    stats = {"files": 0, "dirs": 0, "bytes": 0, "errors": 0, "other_mounts": 0}
    errors: List[str] = []
    root = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _empty_directory(root, os.fstat(root).st_dev, stats, errors)
    finally:
        os.close(root)
    return {**stats, "messages": errors}


def _size(count: int) -> str:
    size = float(count)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{count} B"


def check_share(name: str, flag: str, source: str, emit: Emit, protected: List[str]) -> int:
    """Mount ``source`` read-only, count its top-level entries, unmount; return the count."""
    with mounted((name, flag, source), True, emit, protected) as mountpoint:
        entries = len(os.listdir(mountpoint))
    emit(NFS_MSGS["share_ok"].format(name=name, source=source, entries=entries))
    return entries


def connected_clients() -> List[str]:
    """Return "name (ip)" of the NFS clients connected to this machine's NFS server ([] when
    it serves nothing), without this host itself."""
    found = []
    try:
        entries = sorted(os.listdir(NFSD_CLIENTS_DIR))
    except OSError:
        return found
    for entry in entries:
        try:
            with open(os.path.join(NFSD_CLIENTS_DIR, entry, "info"), "r",
                      encoding="utf-8") as stream:
                text = stream.read()
        except OSError:
            continue
        address = re.search(r'address: "([^":]+)', text)
        client = re.search(r'name: "Linux NFSv4\.\d+ ([^"]+)"', text)
        if client and client.group(1).split(".")[0] != socket.gethostname().split(".")[0]:
            found.append(f"{client.group(1)} ({address.group(1) if address else '?'})")
    return found


def _failure_hint(first_error: str, clients: List[str]) -> str:
    """Return the hint for the first error: a squashed root, or a client still writing."""
    if "ermission" in first_error or "not permitted" in first_error:
        return NFS_MSGS["squash_hint"]
    return NFS_MSGS["clients_hint"].format(clients=", ".join(clients)) if clients else ""


def wipe_share(name: str, flag: str, source: str, emit: Emit,
               protected: List[str]) -> Dict[str, Any]:
    """Empty the share completely, unmount it and check that it is empty; return the counts.

    Each attempt mounts the share read-write, empties it, unmounts it and mounts it read-only
    to count what is left. The attempt is repeated (``CLEANUP_ATTEMPTS`` in all) while
    entries remain, because a client may recreate them.

    Raises:
        NfsError: The share cannot be mounted, or entries are left after the last attempt
            (the share is unmounted in every case).
    """
    started = time.monotonic()
    clients = connected_clients()
    if clients:
        emit(NFS_MSGS["clients"].format(clients=", ".join(clients)))
    totals = {"files": 0, "dirs": 0, "bytes": 0}
    other_mounts = left = attempt = 0
    first = ""
    for attempt in range(1, CLEANUP_ATTEMPTS + 1):
        with mounted((name, flag, source), False, emit, protected) as mountpoint:
            stats = empty_directory(mountpoint)
        for key in totals:
            totals[key] += stats[key]
        other_mounts = max(other_mounts, stats["other_mounts"])
        first = stats["messages"][0] if stats["messages"] else first
        left = check_share(name, flag, source, emit, protected)
        if not left:
            break
        if attempt < CLEANUP_ATTEMPTS:
            emit(NFS_MSGS["retry"].format(name=name, count=left, number=attempt,
                                          total=CLEANUP_ATTEMPTS, pause=RETRY_PAUSE_SECONDS))
            time.sleep(RETRY_PAUSE_SECONDS)
    emit(NFS_MSGS["removed"].format(name=name, files=totals["files"], dirs=totals["dirs"],
                                    size=_size(totals["bytes"]), source=source))
    if other_mounts:
        emit(NFS_MSGS["skipped_mounts"].format(name=name, count=other_mounts))
    if left:
        raise NfsError(NFS_MSGS["empty_failed"].format(
            name=name, count=left, source=source, attempts=CLEANUP_ATTEMPTS,
            first=first or "entries are still present", hint=_failure_hint(first, clients)))
    return {**totals, "other_mounts": other_mounts, "attempts": attempt, "left": 0,
            "seconds": time.monotonic() - started}
