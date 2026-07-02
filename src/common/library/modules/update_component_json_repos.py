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

# pylint: disable=import-error,no-name-in-module
#!/usr/bin/python

"""Ansible module to update component JSON files with version-specific repo names."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.upgrade import upgrade_hop_calculator_lib


def run_module():
    """
    Run the Ansible module.

    Updates component JSON files with version-specific repo names for components
    that support versioned repositories.
    """
    module_args = dict(
        input_dir=dict(type="str", required=True),
        calculated_hop_chains=dict(type="list", required=True),
        architectures=dict(type="list", required=True),
        versioned_repo_components=dict(type="dict", required=True),
    )

    result = dict(
        changed=False,
        success=True,
        updated_files=[],
        messages=[]
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    input_dir = module.params["input_dir"]
    calculated_hop_chains = module.params["calculated_hop_chains"]
    architectures = module.params["architectures"]
    versioned_repo_components = module.params["versioned_repo_components"]

    # Update component JSON files using the library
    update_result = upgrade_hop_calculator_lib.update_component_json_repos(
        input_dir,
        calculated_hop_chains,
        architectures,
        versioned_repo_components
    )

    result["changed"] = len(update_result["updated_files"]) > 0
    result["success"] = update_result["success"]
    result["updated_files"] = update_result["updated_files"]
    result["messages"] = update_result["messages"]

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
