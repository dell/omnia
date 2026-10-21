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

"""Regression coverage for S3 artifact layout validation."""

import pytest

from library.functions.s3_func import _artifact_records
from library.vars.common_vars import IMAGE_BUILD_TYPE_SUFFIXES


_BUCKET = "boot-images"
_GROUP = "slurm_node_rhel_10_0_x86_64"
_IMAGE_DIRECTORY = "rhel-slurm-node-imgth"
_RELEASE = "10.0"
_PREFIX = f"{_BUCKET}/{_GROUP}/{_IMAGE_DIRECTORY}/{_RELEASE}"
_THRILLHOUSE_SUFFIX = IMAGE_BUILD_TYPE_SUFFIXES["image-thrillhouse"]


def _status_entry(kernel: str, initrd: str) -> dict:
    return {
        "functional_group": _GROUP,
        "kernel": f"{_PREFIX}/{kernel}",
        "initrd": f"{_PREFIX}/{initrd}",
        "image": f"{_PREFIX}/rootfs.squashfs",
    }


@pytest.mark.parametrize(
    ("kernel", "initrd"),
    [
        ("vmlinuz", "initramfs.img"),
        (
            "vmlinuz-6.12.0-55.103.1.el10_0.x86_64",
            "initramfs-6.12.0-55.103.1.el10_0.x86_64.img",
        ),
    ],
)
def test_thrillhouse_accepts_legacy_and_versioned_boot_pairs(kernel, initrd):
    """Accept the two supported Thrillhouse boot-artifact generations."""
    records = _artifact_records(
        _status_entry(kernel, initrd),
        _BUCKET,
        _GROUP,
        _THRILLHOUSE_SUFFIX,
    )

    assert [record["error"] for record in records] == ["", "", ""]
    assert {record["cohort"] for record in records} == {
        f"{_IMAGE_DIRECTORY}/{_RELEASE}"
    }


@pytest.mark.parametrize(
    ("kernel", "initrd"),
    [
        (
            "vmlinuz-6.12.0-55.103.1.el10_0.x86_64",
            "initramfs-6.12.0-55.99.1.el10_0.x86_64.img",
        ),
        (
            "vmlinuz-6.12.0-55.103.1.el10_0.x86_64",
            "initramfs.img",
        ),
    ],
)
def test_thrillhouse_rejects_unmatched_boot_pairs(kernel, initrd):
    """Reject mixed-generation and different-version boot artifact pairs."""
    records = _artifact_records(
        _status_entry(kernel, initrd),
        _BUCKET,
        _GROUP,
        _THRILLHOUSE_SUFFIX,
    )

    errors = {
        record["field"]: record["error"]
        for record in records
    }
    assert "same kernel version" in errors["kernel"]
    assert "same kernel version" in errors["initrd"]
    assert errors["image"] == ""


@pytest.mark.parametrize(
    ("kernel", "initrd", "invalid_field"),
    [
        ("vmlinuz-", "initramfs-6.12.0.img", "kernel"),
        ("vmlinuz-6.12.0", "initramfs-.img", "initrd"),
        ("vmlinuz-current", "initramfs-current", "initrd"),
    ],
)
def test_thrillhouse_rejects_malformed_boot_filenames(
    kernel, initrd, invalid_field,
):
    """Reject incomplete or incorrectly suffixed boot artifact names."""
    records = _artifact_records(
        _status_entry(kernel, initrd),
        _BUCKET,
        _GROUP,
        _THRILLHOUSE_SUFFIX,
    )

    errors = {
        record["field"]: record["error"]
        for record in records
    }
    assert "must be" in errors[invalid_field]
