#!/usr/bin/python
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

"""Select the boot set (kernel, initramfs, modules) from a flattened OCI root filesystem."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.oci_rootfs import BootSetError, UnsafeLayerError, select_boot_set

DOCUMENTATION = r"""
---
module: oci_select_boot_set
short_description: Select the kernel and initramfs from a flattened OCI root filesystem
description:
  - Candidates are vmlinuz-<version> files in /boot with a matching initramfs-<version>.img and a /lib/modules/<version>/ directory.
  - Rescue (*rescue*) and debug (*+debug) kernels are excluded.
  - There is no default choice. One complete boot set is used; several require kernel_version.
options:
  rootfs_dir:
    description: Flattened root filesystem directory.
    type: path
    required: true
  kernel_version:
    description: Exact kernel version to use; required when more than one complete boot set exists.
    type: str
    default: ""
"""


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"rootfs_dir": {"type": "path", "required": True},
                       "kernel_version": {"type": "str", "default": ""}},
        supports_check_mode=True,
    )
    try:
        result = select_boot_set(module.params["rootfs_dir"], module.params["kernel_version"])
    except (BootSetError, UnsafeLayerError) as exc:
        module.fail_json(msg=f"boot artifact extraction failed (phase: extraction): {exc}")
    module.exit_json(changed=False, **result)


if __name__ == "__main__":
    main()
