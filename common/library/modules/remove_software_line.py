# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

#!/usr/bin/python

# Custom module to remove software lines from software.csv
# based on metadata version check (for k8s, service_k8s, etc.)

import os
from ansible.module_utils.basic import AnsibleModule
import yaml


def run_module():
    module_args = {
        "software_csv": {"type": "path", "required": True},
        "metadata_file": {"type": "path", "required": True},
        "current_version": {"type": "str", "required": True},
        "software_name": {"type": "str", "required": True},  # e.g., "k8s" or "service_k8s"
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    software_csv = module.params["software_csv"]
    metadata_file = module.params["metadata_file"]
    current_version = module.params["current_version"]
    software_name = module.params["software_name"]

    changed = False

    if not os.path.isfile(metadata_file) or not os.path.isfile(software_csv):
        module.exit_json(
            changed=False,
            msg=f"One or both files do not exist: {metadata_file}, {software_csv}"
        )

    try:
        with open(metadata_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f)
    except yaml.YAMLError as err:
        module.fail_json(msg=f"Failed to parse metadata file: {err}")
    except OSError as err:
        module.fail_json(msg=f"Failed to read metadata file: {err}")

    version_key = f"{software_name}_local_repo_versions"
    known_versions = metadata.get(version_key, [])

    if current_version in known_versions:
        module.exit_json(
            changed=False,
            msg=f"{software_name} version {current_version} already present in metadata."
        )

    try:
        with open(software_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as err:
        module.fail_json(msg=f"Failed to read software.csv: {err}")

    # Remove lines starting with software_name (e.g., 'k8s', 'service_k8s')
    new_lines = [line for line in lines if not line.strip().startswith(software_name)]

    if len(new_lines) != len(lines):
        changed = True
        try:
            with open(software_csv, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except OSError as err:
            module.fail_json(msg=f"Failed to write software.csv: {err}")

    module.exit_json(
        changed=changed,
        msg=f"{software_name} lines removed from software.csv" if changed else f"No {software_name} lines found to remove"
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
