#!/usr/bin/env python3
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
Reproducible fixture generator for Image Build Manager build_status fallback contracts.
Generates positive, negative, boundary, and regression fixtures for ER-ORCH-009 / AC-004 / AC-008.
"""

from pathlib import Path
import yaml

FIXTURES_DIR = Path(__file__).resolve().parent


def generate_all_fixtures():
    """Generate all build_status.yml contract fixtures."""
    # 1. Valid positive fixture (both flexible and standard groups)
    valid_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {
            "endpoint_url": "http://192.0.2.10:9000",
            "bucket": "boot-images",
        },
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/rootfs.squashfs",
                    },
                    {
                        "functional_group": "fg_database_rhel_10_2_x86_64",
                        "kernel": "boot-images/fg_database_rhel_10_2_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_database_rhel_10_2_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_database_rhel_10_2_x86_64/rootfs.squashfs",
                    },
                    {
                        "functional_group": "slurm_control_node_rhel_10_0_x86_64",
                        "kernel": (
                            "boot-images/slurm_control_node_rhel_10_0_x86_64/vmlinuz-6.11.0"
                        ),
                        "initrd": (
                            "boot-images/slurm_control_node_rhel_10_0_x86_64/"
                            "initramfs-6.11.0.img"
                        ),
                        "image": (
                            "boot-images/slurm_control_node_rhel_10_0_x86_64/rootfs.squashfs"
                        ),
                    },
                    {
                        "functional_group": "service_kube_control_plane_rhel_10_0_x86_64",
                        "kernel": (
                            "boot-images/service_kube_control_plane_rhel_10_0_x86_64/"
                            "vmlinuz-6.11.0"
                        ),
                        "initrd": (
                            "boot-images/service_kube_control_plane_rhel_10_0_x86_64/"
                            "initramfs-6.11.0.img"
                        ),
                        "image": (
                            "boot-images/service_kube_control_plane_rhel_10_0_x86_64/"
                            "rootfs.squashfs"
                        ),
                    },
                    {
                        "functional_group": "os_rhel_10_2_x86_64",
                        "kernel": "boot-images/os_rhel_10_2_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/os_rhel_10_2_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/os_rhel_10_2_x86_64/rootfs.squashfs",
                    },
                ]
            },
            {
                "aarch64": [
                    {
                        "functional_group": "fg_ai_worker_rhel_10_2_aarch64",
                        "kernel": "boot-images/fg_ai_worker_rhel_10_2_aarch64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_ai_worker_rhel_10_2_aarch64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_ai_worker_rhel_10_2_aarch64/rootfs.squashfs",
                    },
                    {
                        "functional_group": "slurm_node_rhel_10_0_aarch64",
                        "kernel": "boot-images/slurm_node_rhel_10_0_aarch64/vmlinuz-6.11.0",
                        "initrd": "boot-images/slurm_node_rhel_10_0_aarch64/initramfs-6.11.0.img",
                        "image": "boot-images/slurm_node_rhel_10_0_aarch64/rootfs.squashfs",
                    },
                ]
            },
        ],
    }
    _write_yaml("valid_flexible_build_status.yml", valid_data)

    # 2. Missing kernel
    missing_kernel_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/rootfs.squashfs",
                    }
                ]
            }
        ],
    }
    _write_yaml("missing_kernel_build_status.yml", missing_kernel_data)

    # 3. Missing initrd
    missing_initrd_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/vmlinuz-6.11.0",
                        "initrd": "",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/rootfs.squashfs",
                    }
                ]
            }
        ],
    }
    _write_yaml("missing_initrd_build_status.yml", missing_initrd_data)

    # 4. Missing rootfs (image)
    missing_rootfs_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/initramfs-6.11.0.img",
                        "image": "",
                    }
                ]
            }
        ],
    }
    _write_yaml("missing_rootfs_build_status.yml", missing_rootfs_data)

    # 5. Stale / failed status
    stale_failed_data = {
        "overall_status": "failed",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/rootfs.squashfs",
                    }
                ]
            }
        ],
    }
    _write_yaml("stale_failed_build_status.yml", stale_failed_data)

    # 6. Architecture mismatch (x86_64 group defined under aarch64 only)
    arch_mismatch_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "aarch64": [
                    {
                        # Intentionally place x86_64 identity inside aarch64 block
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/vmlinuz-6.11.0",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/initramfs-6.11.0.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/rootfs.squashfs",
                    }
                ]
            }
        ],
    }
    _write_yaml("arch_mismatch_build_status.yml", arch_mismatch_data)

    # 7. Ambiguous (duplicate conflicting entries for same group/arch)
    ambiguous_data = {
        "overall_status": "success",
        "image_build_type": "image-thrillhouse",
        "s3_configurations": {"endpoint_url": "http://192.0.2.10:9000", "bucket": "boot-images"},
        "functional_group_images": [
            {
                "x86_64": [
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/v1/vmlinuz",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/v1/initramfs.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/v1/rootfs.squashfs",
                    },
                    {
                        "functional_group": "fg_webserver_rhel_10_0_x86_64",
                        "kernel": "boot-images/fg_webserver_rhel_10_0_x86_64/v2/vmlinuz",
                        "initrd": "boot-images/fg_webserver_rhel_10_0_x86_64/v2/initramfs.img",
                        "image": "boot-images/fg_webserver_rhel_10_0_x86_64/v2/rootfs.squashfs",
                    },
                ]
            }
        ],
    }
    _write_yaml("ambiguous_build_status.yml", ambiguous_data)


def _write_yaml(filename: str, data: dict):
    path = FIXTURES_DIR / filename
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    print(f"Generated {path}")


if __name__ == "__main__":
    generate_all_fixtures()
