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

Empties the NFS shares of the orchestrator ``storage_config.yml`` (``nfs_slurm`` and
``nfs_k8s``) so that a reinstall starts without stale data. The shares are selected by the
cleanup settings of test_config.yml:

- ``cleanup_slurm: true`` empties ``nfs_slurm``, ``false`` skips its test.
- ``cleanup_k8s: true`` empties ``nfs_k8s``, ``false`` skips its test.

Each test mounts the share read-only first (nothing is deleted when it cannot be reached),
empties it (the export stays) and checks that no entry is left. A share that is not an NFS
mount of the storage_config.yml has nothing to empty and skips. The tests need a local run
as root on the execution OIM, because the shares are mounted there.
"""

import pytest

from library.functions import (
    TestLogger,
    can_run_locally,
    empty_nfs_share,
    get_nfs_source,
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


def _cleanup_share(host, case, name, flag):
    """Empty the share ``name`` when ``flag`` of test_config.yml is true, else skip."""
    tc = TC[case]
    test_log = TestLogger(tc["title"], tc["id"])
    try:
        selected = nfs_share_selected(name)
    except TypeError as exc:
        test_log.failed(str(exc))
        pytest.fail(str(exc))
    if not selected:
        _skip(test_log, NFS_MSGS["flag_off"].format(flag=flag, name=name))
    if not can_run_locally():
        _skip(test_log, NFS_MSGS["need_local_root"])
    storage_config = get_storage_config_path(host)
    found = get_nfs_source(storage_config, name)
    assert found["success"], found["error"]
    if not found["source"]:
        _skip(test_log, NFS_MSGS["no_share"].format(name=name, path=storage_config))

    result = empty_nfs_share(name, found["source"], get_protected_paths(host))
    if result["success"]:
        stats = result["stats"]
        test_log.passed(NFS_MSGS["emptied"].format(
            name=name, source=found["source"], files=stats["files"], dirs=stats["dirs"]))
    else:
        test_log.failed(result["error"])
    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50701)
def test_nfs_slurm_share_emptied(host):
    """Empty the Slurm NFS share (nfs_slurm) when cleanup_slurm is true."""
    _cleanup_share(host, "cleanup_nfs_slurm", "nfs_slurm", "cleanup_slurm")


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50702)
def test_nfs_k8s_share_emptied(host):
    """Empty the Kubernetes NFS share (nfs_k8s) when cleanup_k8s is true."""
    _cleanup_share(host, "cleanup_nfs_k8s", "nfs_k8s", "cleanup_k8s")
