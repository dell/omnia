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

"""Ansible module to update software_config.json with target versions from hop chains."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.upgrade import upgrade_hop_calculator_lib


def run_module():
    """
    Run the Ansible module.

    Updates software_config.json with target versions from calculated hop chains.
    """
    module_args = dict(
        input_file=dict(type="str", required=True),
        hop_chains=dict(type="list", required=True),
        upgrade_mode=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        updated=[],
        mode='',
        total_hops=0
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    input_file = module.params["input_file"]
    hop_chains = module.params["hop_chains"]
    upgrade_mode = module.params["upgrade_mode"]

    # Update software_config.json using the library
    update_result = upgrade_hop_calculator_lib.update_software_config(
        input_file,
        hop_chains,
        upgrade_mode
    )

    result["changed"] = len(update_result["updated"]) > 0
    result["updated"] = update_result["updated"]
    result["mode"] = update_result["mode"]
    result["total_hops"] = update_result["total_hops"]

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
