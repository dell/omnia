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

"""Flatten an exported OCI image archive into a root filesystem tree."""

from __future__ import annotations

import os
import shutil
import subprocess

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.oci_rootfs import UnsafeLayerError, flatten_layers, read_layers

DOCUMENTATION = r"""
---
module: oci_flatten_image
short_description: Flatten an exported OCI image archive with whiteout handling
description:
  - Reads manifest.json from a regctl image export archive and applies the layers in manifest order.
  - Applies OCI whiteouts (.wh.* and .wh..wh..opq) and rejects absolute, escaping or symlink-traversing entries.
  - Preserves numeric ownership, permissions, links, device nodes, xattrs (including security.selinux) and ACLs through tar.
  - Must run as root so ownership and attributes are preserved.
options:
  image_tar:
    description: Path to the regctl image export archive.
    type: path
    required: true
  rootfs_dir:
    description: Output directory for the flattened filesystem.
    type: path
    required: true
  scratch_dir:
    description: Directory for extracted layer blobs; removed on completion.
    type: path
    required: true
"""


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"image_tar": {"type": "path", "required": True},
                       "rootfs_dir": {"type": "path", "required": True},
                       "scratch_dir": {"type": "path", "required": True}},
    )
    params = module.params
    if os.geteuid() != 0:
        module.fail_json(msg="oci_flatten_image must run as root to preserve ownership "
                             "and attributes")
    if not os.path.isfile(params["image_tar"]):
        module.fail_json(msg=f"image archive not found: {params['image_tar']}")
    if os.path.exists(params["rootfs_dir"]):
        shutil.rmtree(params["rootfs_dir"])
    try:
        layers = read_layers(params["image_tar"], params["scratch_dir"])
        result = flatten_layers(layers, params["rootfs_dir"])
    except UnsafeLayerError as exc:
        shutil.rmtree(params["rootfs_dir"], ignore_errors=True)
        module.fail_json(msg=f"layer extraction rejected (phase: extraction): {exc}")
    except (subprocess.CalledProcessError, OSError) as exc:
        shutil.rmtree(params["rootfs_dir"], ignore_errors=True)
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            detail = exc.stderr.decode(errors="replace").strip()
        module.fail_json(msg=f"layer extraction failed (phase: extraction): {detail}")
    finally:
        shutil.rmtree(params["scratch_dir"], ignore_errors=True)
    module.exit_json(changed=True, **result)


if __name__ == "__main__":
    main()
