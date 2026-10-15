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

"""Unit tests for Image Build Manager artifact filename contracts."""

import pytest

from library.cadence_artifact_contract import (
    artifact_basenames_match_engine,
)

pytestmark = pytest.mark.unit


def test_current_thrillhouse_artifact_names_are_accepted():
    """Accept a matched versioned kernel/initrd Thrillhouse cohort."""
    artifacts = {
        "image": "boot-images/slurm/rhel-slurm-imgth/10.2/rootfs.squashfs",
        "kernel": (
            "boot-images/slurm/rhel-slurm-imgth/10.2/"
            "vmlinuz-6.12.0-124.8.1.el10_1.x86_64"
        ),
        "initrd": (
            "boot-images/slurm/rhel-slurm-imgth/10.2/"
            "initramfs-6.12.0-124.8.1.el10_1.x86_64.img"
        ),
    }
    assert artifact_basenames_match_engine("image-thrillhouse", artifacts)


def test_legacy_thrillhouse_artifact_names_are_accepted():
    """Accept fixed filenames retained for old Thrillhouse cache entries."""
    artifacts = {
        "image": "boot-images/slurm/rhel-slurm-imgth/10.2/rootfs.squashfs",
        "kernel": "boot-images/slurm/rhel-slurm-imgth/10.2/vmlinuz",
        "initrd": "boot-images/slurm/rhel-slurm-imgth/10.2/initramfs.img",
    }
    assert artifact_basenames_match_engine("image-thrillhouse", artifacts)


@pytest.mark.parametrize(
    ("engine", "artifacts"),
    [
        (
            "image-thrillhouse",
            {
                "image": "boot-images/slurm/rootfs.squashfs",
                "kernel": "boot-images/slurm/vmlinuz-1",
                "initrd": "boot-images/slurm/initramfs-2.img",
            },
        ),
    ],
)
def test_mixed_or_invalid_engine_artifacts_are_rejected(engine, artifacts):
    """Reject wrong rootfs contracts and unmatched Thrillhouse cohorts."""
    assert not artifact_basenames_match_engine(engine, artifacts)
