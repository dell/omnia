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

"""Ansible module to calculate upgrade hop chains from upgrade_manifest.yml for multi-hop upgrades."""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.upgrade import upgrade_hop_calculator_lib


def run_module():
    """
    Run the Ansible module.

    Calculates upgrade hop chains from upgrade_manifest.yml and returns
    the calculated hop chains for all enabled components.
    """
    module_args = dict(
        upgrade_config=dict(type="dict", required=True),
        current_software_config=dict(type="dict", required=True),
        current_omnia_version=dict(type="str", required=True),
        target_omnia_version=dict(type="str", required=True),
    )

    result = dict(
        changed=False,
        hop_chains=[],
        total_hops=0,
        upgrade_mode='single_hop',
        warnings=[]
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    upgrade_config = module.params["upgrade_config"]
    current_software_config = module.params["current_software_config"]
    current_omnia_version = module.params["current_omnia_version"]
    target_omnia_version = module.params["target_omnia_version"]

    # Calculate hop chains using the library
    hop_result = upgrade_hop_calculator_lib.calculate_all_hop_chains(
        upgrade_config,
        current_software_config,
        current_omnia_version,
        target_omnia_version
    )

    result["hop_chains"] = hop_result["hop_chains"]
    result["total_hops"] = hop_result["total_hops"]
    result["upgrade_mode"] = hop_result["upgrade_mode"]
    result["warnings"] = hop_result["warnings"]

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
