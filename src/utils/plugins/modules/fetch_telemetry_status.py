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

DOCUMENTATION = r'''
---
module: fetch_telemetry_status

short_description: Fetch enabled telemetry sources from telemetry configuration

version_added: "2.2.0"

description:
    - This module reads the telemetry_config.yml file and determines which telemetry sources are enabled.
    - It returns a list of enabled telemetry components for use in other playbook tasks.
    - Supports UFM metrics/logs and VAST metrics/logs.

options:
    input_path:
        description:
            - Path to the directory containing the telemetry_config.yml file.
            - The module will look for telemetry_config.yml in this directory.
        required: true
        type: path

author:
    - Dell Technologies Omnia Team

requirements:
    - python >= 3.12
    - PyYAML
    - Access to telemetry_config.yml file
'''

EXAMPLES = r'''
# Fetch telemetry status from default input directory
- name: Get enabled telemetry sources
  fetch_telemetry_status:
    input_path: "/opt/omnia/input/project_default"
  register: telemetry_status

# Use the returned telemetry status list
- name: Display enabled telemetry sources
  ansible.builtin.debug:
    msg: "Enabled telemetry: {{ telemetry_status.telemetry_status_list }}"

# Conditionally run tasks based on telemetry status
- name: Configure UFM telemetry
  include_tasks: configure_ufm.yml
  when: "'ufm_telemetry' in telemetry_status.telemetry_status_list"
'''

RETURN = r'''
telemetry_status_list:
    description: List of enabled telemetry components
    type: list
    elements: str
    returned: always
    sample: ["ufm_telemetry", "ufm_logs", "vast_telemetry"]

changed:
    description: Whether the module made any changes (always false for this read-only module)
    type: bool
    returned: always
    sample: false

failed:
    description: Whether the module failed to execute
    type: bool
    returned: failure
    sample: false
'''

"""Ansible module to fetch telemetry status."""
import os
from typing import Dict, Any, List
import yaml
from ansible.module_utils.basic import AnsibleModule

TELEMETRY_CONFIG_FILE_NAME = "telemetry_config.yml"

def load_yaml(path: str) -> Dict[str, Any]:
    """
    Load YAML from a given file path.

    Args:
        path: The path to the YAML file.

    Returns:
        The loaded YAML data.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is invalid.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def main() -> None:
    """
    Main entry point of the Ansible module.
    
    Loads the telemetry configuration from a YAML file,
    checks the status of various telemetry components,
    and returns the enabled components as a list.
    """
    module_args = {
        "input_path": {
            "type": "path", "required": True
        }
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    input_dir_path = module.params["input_path"]
    telemetry_config_path = os.path.join(input_dir_path, TELEMETRY_CONFIG_FILE_NAME)
    
    try:
        telemetry_config_data = load_yaml(telemetry_config_path)
    except (FileNotFoundError, yaml.YAMLError, PermissionError) as e:
        module.fail_json(msg=f"Failed to load telemetry config: {e}")

    telemetry_status_list: List[str] = []

    telemetry_sources = telemetry_config_data.get("telemetry_sources", {})

    # Check UFM telemetry
    ufm_config = telemetry_sources.get("ufm", {})
    if ufm_config.get("metrics_enabled", False):
        telemetry_status_list.append("ufm_telemetry")
    if ufm_config.get("logs_enabled", False):
        telemetry_status_list.append("ufm_logs")

    # Check VAST telemetry
    vast_config = telemetry_sources.get("vast", {})
    if vast_config.get("metrics_enabled", False):
        telemetry_status_list.append("vast_telemetry")
    if vast_config.get("logs_enabled", False):
        telemetry_status_list.append("vast_logs")

    module.exit_json(
        changed=False,
        telemetry_status_list=telemetry_status_list
    )


if __name__ == "__main__":
    main()
