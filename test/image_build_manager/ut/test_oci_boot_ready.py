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
# Applicable rules used: CG-CONFIG-001.5, CG-DESER-001.1
# ****
"""Unit tests for the OCI boot-ready layer-listing merge (TC-UT-010, FR-1.5).

Layer entry names are merged in manifest order with whiteout and opaque
directory semantics. No registry, extraction or Ansible run is required.
"""

# Pytest injects fixtures by reusing fixture function names as test arguments,
# and descriptive test names make per-test docstrings redundant.
# pylint: disable=missing-function-docstring

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOT_READY_PATH = (
    REPO_ROOT / "src/image_build_manager/plugins/module_utils/oci_boot_ready.py"
)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


BOOT_READY = _load_module("oci_boot_ready_under_test", BOOT_READY_PATH)
evaluate_boot_set = BOOT_READY.evaluate_boot_set

NO_KERNEL_PATH = "boot/vmlinuz-*"


def _boot_set(version):
    return [
        f"boot/vmlinuz-{version}",
        f"boot/initramfs-{version}.img",
        f"lib/modules/{version}/kernel/fs/ext4.ko.xz",
    ]


def test_complete_boot_set_merged_across_layers():
    layers = [
        ["boot/vmlinuz-6.12.0"],
        ["boot/initramfs-6.12.0.img", "lib/modules/6.12.0/kernel/fs/ext4.ko.xz"],
    ]

    result = evaluate_boot_set(layers)

    assert result["complete_versions"] == ["6.12.0"]
    assert result["missing_path"] == ""


def test_missing_initramfs_names_the_path():
    result = evaluate_boot_set([["boot/vmlinuz-6.12.0", "lib/modules/6.12.0/"]])

    assert result["complete_versions"] == []
    assert result["missing_path"] == "boot/initramfs-6.12.0.img"


def test_missing_kernel_modules_names_the_path():
    result = evaluate_boot_set(
        [["boot/vmlinuz-6.12.0", "boot/initramfs-6.12.0.img"]]
    )

    assert result["complete_versions"] == []
    assert result["missing_path"] == "lib/modules/6.12.0"


def test_whiteout_removes_kernel_from_lower_layer():
    layers = [_boot_set("6.12.0"), ["boot/.wh.vmlinuz-6.12.0"]]

    result = evaluate_boot_set(layers)

    assert result["complete_versions"] == []
    assert result["missing_path"] == NO_KERNEL_PATH


def test_opaque_directory_hides_lower_layer_modules():
    layers = [
        _boot_set("6.12.0"),
        ["lib/modules/6.12.0/.wh..wh..opq"],
    ]

    result = evaluate_boot_set(layers)

    assert result["complete_versions"] == []
    assert result["missing_path"] == "lib/modules/6.12.0"


def test_opaque_directory_keeps_entries_from_its_own_layer():
    layers = [
        _boot_set("6.12.0"),
        ["lib/modules/6.12.0/.wh..wh..opq", "lib/modules/6.12.0/kernel/new.ko.xz"],
    ]

    result = evaluate_boot_set(layers)

    assert result["complete_versions"] == ["6.12.0"]
    assert result["missing_path"] == ""


@pytest.mark.parametrize("version", ["0-rescue-3f2a", "6.12.0-debug"])
def test_rescue_and_debug_kernels_do_not_count(version):
    result = evaluate_boot_set([_boot_set(version)])

    assert result["complete_versions"] == []
    assert result["missing_path"] == NO_KERNEL_PATH


@pytest.mark.parametrize(
    "kernel_name", ["/boot/vmlinuz-6.12.0", "../boot/vmlinuz-6.12.0"]
)
def test_absolute_and_parent_names_are_ignored(kernel_name):
    entries = [
        kernel_name,
        "boot/initramfs-6.12.0.img",
        "lib/modules/6.12.0/kernel/fs/ext4.ko.xz",
    ]

    result = evaluate_boot_set([entries])

    assert result["complete_versions"] == []
    assert result["missing_path"] == NO_KERNEL_PATH


def test_dot_slash_names_are_normalized():
    entries = [
        "./boot/vmlinuz-6.12.0",
        "./boot/initramfs-6.12.0.img",
        "./lib/modules/6.12.0/kernel/fs/ext4.ko.xz",
    ]

    result = evaluate_boot_set([entries])

    assert result["complete_versions"] == ["6.12.0"]


def test_several_complete_sets_are_all_listed():
    layers = [_boot_set("6.12.0") + _boot_set("6.11.5")]

    result = evaluate_boot_set(layers)

    assert result["complete_versions"] == ["6.11.5", "6.12.0"]
    assert result["missing_path"] == ""


def test_usr_merged_modules_directory_counts():
    entries = [
        "boot/vmlinuz-6.12.0",
        "boot/initramfs-6.12.0.img",
        "lib",
        "usr/lib/modules/6.12.0/",
    ]

    result = evaluate_boot_set([entries])

    assert result["complete_versions"] == ["6.12.0"]
    assert result["missing_path"] == ""
