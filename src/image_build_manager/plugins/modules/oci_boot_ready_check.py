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

"""Check that a local OCI image holds a complete boot set."""

import json
import subprocess
import tarfile
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.oci_boot_ready import evaluate_boot_set

DOCUMENTATION = r"""
---
module: oci_boot_ready_check
short_description: Verify a local OCI image is boot-complete
version_added: "2.3.0"
description:
  - Lists the entry names of every layer of an OCI image with C(regctl).
  - Applies whiteout and opaque-directory rules in memory. No layer content is extracted.
  - Fails when no complete kernel, initramfs and modules set is present.
options:
  image_repo:
    description: Repository of the local OCI image, for example C(registry:5000/name).
    required: true
    type: str
  image_ref:
    description: Full local reference of the image, repository and tag.
    required: true
    type: str
  regctl_bin:
    description: Path to the regctl binary.
    required: true
    type: str
  timeout_seconds:
    description: Timeout in seconds for each regctl operation.
    required: false
    type: int
    default: 300
author:
  - Omnia Team
"""

EXAMPLES = r"""
- name: Verify the boot set of the local OCI image
  omnia.image_build.oci_boot_ready_check:
    image_repo: "registry:5000/rhel-slurm"
    image_ref: "registry:5000/rhel-slurm:10.0"
    regctl_bin: "/usr/local/bin/regctl"
    timeout_seconds: 300
"""

RETURN = r"""
complete_versions:
  description: Kernel versions with a complete boot set, sorted.
  returned: success
  type: list
  elements: str
layer_count:
  description: Number of layers listed.
  returned: success
  type: int
"""

MISSING_PATH_MSG = "Boot-ready check failed: missing {path} in the OCI image."
NO_LAYERS_MSG = "Boot-ready check failed: the OCI image manifest lists no layers."
TIMEOUT_MSG = "Boot-ready check failed: regctl exceeded the {timeout} second timeout."
REGCTL_FAILED_MSG = "Boot-ready check failed: regctl could not read the OCI image (rc={rc})."


def _run_regctl(module, args, timeout):
    """Run one regctl command and return its stdout.

    Args:
        module: The running AnsibleModule, used for failure reporting.
        args: regctl arguments, passed as an argument vector without a shell.
        timeout: Timeout in seconds for the command.

    Returns:
        The stdout text of the command.
    """
    try:
        proc = subprocess.run(
            [module.params["regctl_bin"], *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return module.fail_json(msg=TIMEOUT_MSG.format(timeout=timeout))
    if proc.returncode != 0:
        return module.fail_json(msg=REGCTL_FAILED_MSG.format(rc=proc.returncode))
    return proc.stdout


def _layer_entries(module, timeout):
    """List the entry names of each layer in manifest order.

    Args:
        module: The running AnsibleModule.
        timeout: Timeout in seconds for each regctl operation.

    Returns:
        A list with one list of entry names per layer, lowest layer first.
    """
    manifest = json.loads(
        _run_regctl(
            module,
            ["manifest", "get", module.params["image_ref"], "--format", "raw-body"],
            timeout,
        )
    )
    digests = [layer["digest"] for layer in manifest.get("layers", [])]
    if not digests:
        module.fail_json(msg=NO_LAYERS_MSG)
    layers = []
    for digest in digests:
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [module.params["regctl_bin"], "blob", "get", module.params["image_repo"], digest],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + timeout
        names = []
        with tarfile.open(fileobj=proc.stdout, mode="r|*") as archive:
            for member in archive:
                if time.monotonic() > deadline:
                    proc.kill()
                    module.fail_json(msg=TIMEOUT_MSG.format(timeout=timeout))
                names.append(member.name)
        proc.stdout.read()
        if proc.wait(timeout=timeout) != 0:
            module.fail_json(msg=REGCTL_FAILED_MSG.format(rc=proc.returncode))
        layers.append(names)
    return layers


def main():
    """Run the boot-ready check and report the complete boot sets."""
    module = AnsibleModule(
        argument_spec={
            "image_repo": {"type": "str", "required": True},
            "image_ref": {"type": "str", "required": True},
            "regctl_bin": {"type": "str", "required": True},
            "timeout_seconds": {"type": "int", "default": 300},
        },
        supports_check_mode=True,
    )
    layers = _layer_entries(module, module.params["timeout_seconds"])
    result = evaluate_boot_set(layers)
    if not result["complete_versions"]:
        module.fail_json(msg=MISSING_PATH_MSG.format(path=result["missing_path"]))
    module.exit_json(
        changed=False,
        complete_versions=result["complete_versions"],
        layer_count=len(layers),
    )


if __name__ == "__main__":
    main()
