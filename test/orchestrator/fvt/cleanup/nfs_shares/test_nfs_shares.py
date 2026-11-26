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

"""
Orchestrator cleanup - NFS shares of the Slurm and Kubernetes storage.

The orchestrator cleanup unmounts the Slurm and Kubernetes storage and removes its fstab
entries, whether ``cleanup_slurm`` / ``cleanup_k8s`` of test_config.yml are true or false. It
does not empty the NFS export, so this suite does, for the ``nfs_slurm`` and ``nfs_k8s``
mounts of ``storage_config.yml``:

1. ``*_share_detached`` (always): the share is unmounted and has no fstab entry.
2. ``*_share_emptied`` (only when the flag is true; skipped when it is false, and the data
   is kept): the share is checked to be detached again, mounted on a private temporary
   folder (never added to fstab), emptied completely, unmounted, and checked to be empty
   with a fresh read-only mount (up to three attempts). Afterwards it must still be
   unmounted and out of fstab.

Emptying mounts the share on the execution OIM, so it needs a local run as root there. A
missing or invalid ``storage_config.yml`` fails the tests; a share that is not an NFS mount
skips them. A share the OIM cannot mount (server unreachable, not exported to it) fails the
emptying test before anything is deleted.
"""

import pytest

from library.functions import (
    TestLogger,
    can_run_locally,
    check_nfs_share_detached,
    empty_nfs_share,
    get_nfs_mount,
    get_protected_paths,
    get_storage_config_path,
    nfs_share_selected,
)
from library.messages import NFS_MSGS
from library.vars import TEST_CASES as TC


def _skip(test_log, reason):
    """Record the skip in the report and skip the test."""
    test_log.skipped(reason)
    pytest.skip(reason)


def _configured_share(host, test_log, name):
    """Return the NFS mount ``name`` of storage_config.yml.

    Fails when the file is missing or invalid; skips when it has no NFS mount of that name.
    """
    storage_config = get_storage_config_path(host)
    found = get_nfs_mount(storage_config, name)
    if found["missing"]:
        message = NFS_MSGS["config_missing"].format(name=name, path=storage_config)
        test_log.failed(message)
        pytest.fail(message)
    if not found["success"]:
        test_log.failed(found["error"])
        pytest.fail(found["error"])
    if not found["source"]:
        _skip(test_log, NFS_MSGS["no_share"].format(name=name, path=storage_config))
    return found


def _flag(test_log, name):
    """Return the cleanup_slurm / cleanup_k8s value of the share ``name``."""
    try:
        return nfs_share_selected(name)
    except TypeError as exc:
        test_log.failed(str(exc))
        pytest.fail(str(exc))
    return False


def _verify_detached(host, case, name, flag):
    """Check that the share is unmounted and out of fstab, whatever ``flag`` says."""
    tc = TC[case]
    test_log = TestLogger(tc["title"], tc["id"])
    selected = _flag(test_log, name)
    found = _configured_share(host, test_log, name)
    result = check_nfs_share_detached(host, name, found["source"], found["mount_point"])
    policy = (f"{flag} is {str(selected).lower()}: the share is "
              f"{'emptied next' if selected else 'kept, nothing is deleted'}")
    fields = [*result["fields"], ("Policy", policy)]
    if result["success"]:
        test_log.passed_fields(
            NFS_MSGS["detached"].format(name=name, mount_point=found["mount_point"] or name),
            fields)
    else:
        test_log.failed_fields(
            NFS_MSGS["not_detached"].format(name=name, problems=result["error"]),
            [*fields, ("Error", result["error"])])
    assert result["success"], NFS_MSGS["not_detached"].format(
        name=name, problems=result["error"])


def _empty_share(host, case, name, flag):
    """Empty the share when ``flag`` is true: gate on detachment, empty, verify, re-check."""
    tc = TC[case]
    test_log = TestLogger(tc["title"], tc["id"])
    if not _flag(test_log, name):
        _skip(test_log, NFS_MSGS["flag_off"].format(flag=flag, name=name))
    if not can_run_locally():
        _skip(test_log, NFS_MSGS["need_local_root"])
    found = _configured_share(host, test_log, name)

    before = check_nfs_share_detached(host, name, found["source"], found["mount_point"])
    if not before["success"]:
        message = NFS_MSGS["not_detached"].format(name=name, problems=before["error"])
        test_log.failed_fields(message, before["fields"])
        pytest.fail(message)

    result = empty_nfs_share(name, found["source"], get_protected_paths(host))
    if not result["success"]:
        test_log.failed(result["error"])
        pytest.fail(result["error"])

    after = check_nfs_share_detached(host, name, found["source"], found["mount_point"])
    stats = result["stats"]
    if not after["success"]:
        message = NFS_MSGS["attached_after"].format(name=name, problems=after["error"])
        test_log.failed_fields(message, after["fields"])
        pytest.fail(message)
    test_log.passed_fields(
        NFS_MSGS["emptied"].format(name=name, source=found["source"], files=stats["files"],
                                   dirs=stats["dirs"], attempts=stats["attempts"]),
        after["fields"])


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50701)
def test_nfs_slurm_share_detached(host):
    """Verify the Slurm NFS share (nfs_slurm) is unmounted and has no fstab entry."""
    _verify_detached(host, "cleanup_nfs_slurm_detached", "nfs_slurm", "cleanup_slurm")


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50702)
def test_nfs_k8s_share_detached(host):
    """Verify the Kubernetes NFS share (nfs_k8s) is unmounted and has no fstab entry."""
    _verify_detached(host, "cleanup_nfs_k8s_detached", "nfs_k8s", "cleanup_k8s")


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50703)
def test_nfs_slurm_share_emptied(host):
    """Empty the Slurm NFS share (nfs_slurm) when cleanup_slurm is true."""
    _empty_share(host, "cleanup_nfs_slurm", "nfs_slurm", "cleanup_slurm")


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50704)
def test_nfs_k8s_share_emptied(host):
    """Empty the Kubernetes NFS share (nfs_k8s) when cleanup_k8s is true."""
    _empty_share(host, "cleanup_nfs_k8s", "nfs_k8s", "cleanup_k8s")
