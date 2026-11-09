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


"""Unit tests of library/functions/nfs_func.py: validation and the safe emptying of a share.

No NFS server and no mount is needed: the mount commands are replaced, and a temporary
folder plays the mounted share.  Run: ``.venv/bin/python -m pytest ut``.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pylint: disable=wrong-import-position
from library.functions import nfs_func  # noqa: E402
from library.functions.nfs_func import NfsError  # noqa: E402


# ----------------------------------------------------------------- the source
@pytest.mark.parametrize("source", [
    "10.0.0.1:/nfs_share/slurm", "nfs-server.example.com:/export/k8s",
    "10.0.0.1:/a", "host:/a/b-c_d.e/f@g"])
def test_valid_sources_are_accepted(source):
    """Test valid sources are accepted."""
    host, export = nfs_func.parse_source("nfs_slurm", source)
    assert f"{host}:{export}" == source


@pytest.mark.parametrize("source", [
    "-oProxyCommand=id:/x", "--help:/x", "a b:/x", "999.1.1.1:/x", "host:", "host:rel/path",
    "host:/a/../b", "host:/a/./b", "host:/..", "host:/a b", "host:/a;rm -rf /", "host:/a$(id)",
    "host:/a\nb", "host:/a//b", "[::1]:/x", "host/x:/y", ":/x", "host:/x:y z"])
def test_malformed_sources_are_refused(source):
    """Test malformed sources are refused."""
    with pytest.raises(NfsError):
        nfs_func.parse_source("nfs_slurm", source)


@pytest.mark.parametrize("export", sorted(nfs_func.DENIED_EXPORTS))
def test_system_directories_are_never_emptied(export):
    """Test system directories are never emptied."""
    with pytest.raises(NfsError):
        nfs_func.parse_source("nfs_slurm", f"10.0.0.1:{export}")


def test_looks_like_nfs():
    """Test looks like nfs."""
    assert nfs_func.looks_like_nfs("10.0.0.1:/share")
    for other in ("/dev/sdc", "UUID=abc", "LABEL=x", "//server/share", "plain"):
        assert not nfs_func.looks_like_nfs(other)


def test_configured_sources_reads_the_mounts(tmp_path):
    """Test configured sources reads the mounts."""
    path = tmp_path / "storage_config.yml"
    path.write_text("mounts:\n  - name: nfs_slurm\n    source: '10.0.0.1:/s'\n"
                    "  - name: nfs_k8s\n    source: '10.0.0.2:/k'\n  - 7\n  - {name: x}\n",
                    encoding="utf-8")
    assert nfs_func.configured_sources(str(path), print) == {
        "nfs_slurm": "10.0.0.1:/s", "nfs_k8s": "10.0.0.2:/k"}
    assert nfs_func.configured_sources(str(tmp_path / "missing.yml"), lambda text: None) == {}


def test_an_export_on_this_oim_holding_the_checkout_is_refused(monkeypatch):
    """Test an export on this oim holding the checkout is refused."""
    monkeypatch.setattr(nfs_func, "_is_local", lambda host: True)
    with pytest.raises(NfsError, match="needs"):
        nfs_func._check_protected("nfs_slurm", "10.0.0.1", "/srv", ["/srv/omnia"])
    nfs_func._check_protected("nfs_slurm", "10.0.0.1", "/nfs_share/slurm", ["/srv/omnia"])
    monkeypatch.setattr(nfs_func, "_is_local", lambda host: False)
    nfs_func._check_protected("nfs_slurm", "10.0.0.9", "/srv", ["/srv/omnia"])


# ------------------------------------------------------------------ emptying
def _tree(root):
    """Tree."""
    (root / "a" / "b" / "c").mkdir(parents=True)
    (root / "a" / "file1").write_bytes(b"x" * 100)
    (root / "a" / "b" / "file2").write_bytes(b"y" * 50)
    (root / "a" / "b" / "c" / ".hidden").write_text("z", encoding="utf-8")
    (root / "top").write_text("t", encoding="utf-8")
    (root / "empty_dir").mkdir()
    os.mkfifo(root / "fifo")
    os.link(root / "top", root / "hardlink")


def test_everything_inside_is_removed_and_the_root_stays(tmp_path):
    """Test everything inside is removed and the root stays."""
    share = tmp_path / "share"
    share.mkdir()
    _tree(share)
    result = nfs_func.empty_directory(str(share))
    assert os.listdir(share) == [] and share.is_dir()
    assert result["errors"] == 0
    assert result["dirs"] == 4 and result["files"] == 6 and result["bytes"] == 153


def test_symbolic_links_are_removed_not_followed(tmp_path):
    """Test symbolic links are removed not followed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious").write_text("keep", encoding="utf-8")
    share = tmp_path / "share"
    share.mkdir()
    (share / "dir_link").symlink_to(outside)
    (share / "file_link").symlink_to(outside / "precious")
    (share / "dangling").symlink_to(tmp_path / "nowhere")
    (share / "sub").mkdir()
    (share / "sub" / "up").symlink_to("..")
    (share / "loop").symlink_to("loop")
    nfs_func.empty_directory(str(share))
    assert os.listdir(share) == []
    assert (outside / "precious").read_text(encoding="utf-8") == "keep"


def test_a_symbolic_link_as_the_root_is_not_followed(tmp_path):
    """Test a symbolic link as the root is not followed."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "keep").write_text("k", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(OSError):
        nfs_func.empty_directory(str(link))
    assert (real / "keep").exists()


def test_a_directory_swapped_for_a_link_is_not_followed(tmp_path, monkeypatch):
    """Test a directory swapped for a link is not followed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious").write_text("keep", encoding="utf-8")
    share = tmp_path / "share"
    (share / "victim").mkdir(parents=True)
    real_stat = os.stat

    def swap(name, *args, **kwargs):
        """Swap."""
        info = real_stat(name, *args, **kwargs)
        if name == "victim" and (share / "victim").is_dir() and not (share / "victim").is_symlink():
            os.rmdir(share / "victim")
            (share / "victim").symlink_to(outside)
        return info

    monkeypatch.setattr(os, "stat", swap)
    result = nfs_func.empty_directory(str(share))
    monkeypatch.undo()
    assert (outside / "precious").exists()
    assert result["errors"] >= 1


def test_a_tree_deeper_than_the_limit_is_reported(tmp_path):
    """Test a tree deeper than the limit is reported."""
    share = tmp_path / "share"
    node = share
    for _ in range(nfs_func.MAX_DEPTH + 4):
        node = node / "d"
    node.mkdir(parents=True)
    result = nfs_func.empty_directory(str(share))
    assert result["messages"] and "deeper" in result["messages"][0] + " ".join(result["messages"])


def test_entries_that_cannot_be_removed_are_counted(tmp_path, monkeypatch):
    """Test entries that cannot be removed are counted."""
    share = tmp_path / "share"
    share.mkdir()
    (share / "ok").write_text("1", encoding="utf-8")
    (share / "locked").write_text("2", encoding="utf-8")
    real_unlink = os.unlink

    def refuse(name, *args, **kwargs):
        """Refuse."""
        if name == "locked":
            raise PermissionError(1, "Operation not permitted")
        return real_unlink(name, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", refuse)
    result = nfs_func.empty_directory(str(share))
    assert result["errors"] == 1 and result["files"] == 1
    assert "locked" in result["messages"][0]


# ------------------------------------------------------------------ the mount
class FakeMounts:
    """Stands for mount/umount: records the argument lists and keeps the mount state."""

    def __init__(self, monkeypatch, mount_rc=0, fstype="nfs4", source=None, umount_rc=0):
        """Init."""
        self.calls, self.mounted, self.source = [], set(), source
        self.mount_rc, self.fstype, self.umount_rc = mount_rc, fstype, umount_rc
        monkeypatch.setattr(nfs_func, "_run", self.run)
        monkeypatch.setattr(nfs_func, "_mountinfo", self.mountinfo)
        monkeypatch.setattr(nfs_func.os.path, "ismount", lambda path: path in self.mounted)
        monkeypatch.setattr(nfs_func.os, "geteuid", lambda: 0)
        monkeypatch.setattr(nfs_func.os, "access", lambda *args: True)

    def run(self, argv, timeout):
        """Run."""
        self.calls.append(argv)
        target = argv[-1]
        if argv[0] == "mount":
            if self.mount_rc == 0:
                self.mounted.add(target)
            return subprocess.CompletedProcess(argv, self.mount_rc, "", "mount failed: denied")
        if argv[0] == "umount":
            if self.umount_rc == 0 or "-l" in argv:
                self.mounted.discard(target)
            return subprocess.CompletedProcess(argv, self.umount_rc, "", "target is busy")
        raise AssertionError(argv)

    def mountinfo(self, mountpoint):
        """Mountinfo."""
        host_export = self.source or self.calls[0][-2]
        return (self.fstype, host_export) if mountpoint in self.mounted else ("", "")


def test_mount_uses_an_argument_list_with_double_dash_and_safe_options(monkeypatch):
    """Test mount uses an argument list with double dash and safe options."""
    fake = FakeMounts(monkeypatch)
    with nfs_func.mounted(("nfs_slurm", "slurm_share", "10.0.0.1:/s"), True, print,
                          []) as mountpoint:
        assert os.path.isdir(mountpoint) and oct(os.stat(mountpoint).st_mode & 0o777) == "0o700"
        assert os.path.basename(mountpoint).startswith("svt-nfs-")
    mount = fake.calls[0]
    assert mount[:2] == ["mount", "-t"] and mount[2] == "nfs" and "--" in mount
    assert mount[mount.index("--") + 1] == "10.0.0.1:/s"
    options = mount[mount.index("-o") + 1]
    assert {"nosuid", "nodev", "noexec", "soft", "ro"} <= set(options.split(","))
    assert fake.calls[-1][:2] == ["umount", "--"]
    assert not os.path.exists(mountpoint)


def test_the_share_is_unmounted_even_when_the_body_fails(monkeypatch):
    """Test the share is unmounted even when the body fails."""
    fake = FakeMounts(monkeypatch)
    with pytest.raises(RuntimeError, match="boom"):
        with nfs_func.mounted(("nfs_slurm", "slurm_share", "10.0.0.1:/s"), False, print, []):
            raise RuntimeError("boom")
    assert fake.mounted == set() and fake.calls[-1][0] == "umount"


def test_a_failed_mount_is_reported_and_leaves_no_folder(monkeypatch):
    """Test a failed mount is reported and leaves no folder."""
    fake = FakeMounts(monkeypatch, mount_rc=32)
    with pytest.raises(NfsError, match="cannot mount"):
        with nfs_func.mounted(("nfs_slurm", "slurm_share", "10.0.0.1:/s"), True, print, []):
            pytest.fail("the body must not run")
    mountpoint = fake.calls[0][-1]
    assert not os.path.exists(mountpoint) and [c[0] for c in fake.calls] == ["mount"]


def test_nothing_is_deleted_when_the_mount_is_not_the_requested_nfs(monkeypatch):
    """Test nothing is deleted when the mount is not the requested nfs."""
    for fstype, source in (("ext4", "10.0.0.1:/s"), ("nfs4", "10.0.0.9:/other")):
        FakeMounts(monkeypatch, fstype=fstype, source=source)
        with pytest.raises(NfsError, match="not the NFS mount"):
            with nfs_func.mounted(("nfs_slurm", "slurm_share", "10.0.0.1:/s"), False, print, []):
                pytest.fail("the body must not run")


def test_a_busy_mount_is_detached_lazily_then_reported_if_it_stays(monkeypatch):
    """Test a busy mount is detached lazily then reported if it stays."""
    fake = FakeMounts(monkeypatch, umount_rc=1)
    messages = []
    with nfs_func.mounted(("nfs_slurm", "slurm_share", "10.0.0.1:/s"), True, messages.append, []):
        pass
    assert any(call[:2] == ["umount", "-l"] for call in fake.calls)
    assert any("lazily" in text for text in messages)


def test_root_and_mount_nfs_are_required(monkeypatch):
    """Test root and mount nfs are required."""
    FakeMounts(monkeypatch)
    monkeypatch.setattr(nfs_func.os, "geteuid", lambda: 1000)
    with pytest.raises(NfsError, match="root"):
        with nfs_func.mounted(("n", "f", "10.0.0.1:/s"), True, print, []):
            pass
    monkeypatch.setattr(nfs_func.os, "geteuid", lambda: 0)
    monkeypatch.setattr(nfs_func.os, "access", lambda *args: False)
    with pytest.raises(NfsError, match="mount.nfs"):
        with nfs_func.mounted(("n", "f", "10.0.0.1:/s"), True, print, []):
            pass


def test_wipe_share_empties_the_mounted_folder_and_reports_the_counts(monkeypatch):
    """Test wipe share empties the mounted folder and reports the counts."""
    fake = FakeMounts(monkeypatch)
    seen = {}
    real_empty = nfs_func.empty_directory

    def fill_then_empty(path):
        """Fill then empty."""
        _tree(__import__("pathlib").Path(path))
        seen["path"] = path
        return real_empty(path)

    monkeypatch.setattr(nfs_func, "empty_directory", fill_then_empty)
    messages = []
    result = nfs_func.wipe_share("nfs_slurm", "slurm_share", "10.0.0.1:/s", messages.append, [])
    assert result["files"] == 6 and result["dirs"] == 4 and not fake.mounted
    assert any("removed 6 files, 4 directories" in text for text in messages)


def test_wipe_share_fails_with_a_root_squash_hint(monkeypatch):
    """Test wipe share fails with a root squash hint."""
    FakeMounts(monkeypatch)
    monkeypatch.setattr(nfs_func, "empty_directory", lambda path: {
        "files": 0, "dirs": 0, "bytes": 0, "errors": 2, "other_mounts": 0,
        "messages": ["data: Permission denied"]})
    with pytest.raises(NfsError, match="no_root_squash"):
        nfs_func.wipe_share("nfs_slurm", "slurm_share", "10.0.0.1:/s", print, [])
