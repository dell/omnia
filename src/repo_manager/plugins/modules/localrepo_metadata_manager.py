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

"""Generate, compare, and update local repository metadata."""

# pylint: disable=import-error,no-name-in-module

import shutil
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.process_metadata import (
    handle_generate_metadata,
    handle_compare_data,
    handle_update_data
)
from ansible.module_utils.repo_manager.config import ( metadata_rerun_file_path )

DOCUMENTATION = r"""
---
module: localrepo_metadata_manager
short_description: Manage local repository metadata
description:
  - This module manages metadata for local repositories.
  - It tracks repository sync status and configuration changes.
version_added: "1.0.0"
options:
    action:
      description: Action to perform (read/write/update)
      required: true
      type: str
    metadata_path:
      description: Path to metadata file
      required: true
      type: str
    data:
      description: Data to write/update
      required: false
      type: dict

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Read repository metadata
  localrepo_metadata_manager:
    action: read
    metadata_path: "{{ omnia_base }}/.data/repo_metadata.yml"
  register: metadata
"""

RETURN = r"""
metadata:
  description: Repository metadata
  type: dict
  returned: success
changed:
  description: Whether metadata was modified
  type: bool
  returned: always
"""
def main():
    """Execute the requested local repository metadata operation."""

    argument_spec = {
        "software_config_path": {"type": "str", "required": False, "default": ""},
        "localrepo_config_path": {"type": "str", "required": True},
        "output_file": {"type": "str", "required": True},
        "update_metadata": {"type": "bool", "default": False},
        "ignore_keys": {"type": "list", "elements": "str", "default": ["lastrun_timestamp"]},
        "sub_urls": {
            "type": "dict",
            "required": False,
            "default": {},
            "no_log": True,
        },
        "cluster_os_version": {"type": "str", "required": True},
        "architectures": {
            "type": "list", "elements": "str", "required": True
        }
    }
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    sw_config = module.params["software_config_path"]
    repo_data = module.params["localrepo_config_path"]
    output_file = module.params["output_file"]
    ignore_keys = module.params['ignore_keys']
    update_flag = module.params["update_metadata"]
    sub_urls = module.params["sub_urls"] or None
    cluster_os_version = module.params["cluster_os_version"]
    architectures = module.params["architectures"]

    try:
        if not output_file or not Path(output_file).exists():
            policy_result = handle_generate_metadata(
                sw_config, repo_data, output_file,
                cluster_os_version, architectures, sub_urls
            )
            module.exit_json(changed=True, policy=policy_result, msg="Metadata generated")
        else:
            if not update_flag:
                shutil.copy2(output_file, metadata_rerun_file_path)
                policy_result = handle_generate_metadata(
                    sw_config,
                    repo_data,
                    metadata_rerun_file_path,
                    cluster_os_version,
                    architectures,
                    sub_urls
                )

                compare_output = handle_compare_data(
                    output_file,
                    metadata_rerun_file_path,
                    ignore_keys
                )
                same = compare_output.get('identical', False)
                module.exit_json(changed=not same, identical=same, msg="Compared metadata")
            else:
                update_result = handle_update_data(output_file, metadata_rerun_file_path, ignore_keys)
                module.exit_json(changed=update_result["changed"], diff=update_result["diff"])

    except Exception:
        module.fail_json(msg="Failed to process local repository metadata.")


if __name__ == '__main__':
    main()
