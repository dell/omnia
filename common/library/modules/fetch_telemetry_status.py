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

"""Ansible module to fetch telemetry status."""
import os
import yaml
from ansible.module_utils.basic import AnsibleModule

TELEMETRY_CONFIG_PATH_DEFAULT = "/opt/omnia/input/project_default/telemetry_config.yml"

def load_yaml(path):
    """
    Load YAML from a given file path.

    Args:
        path (str): The path to the YAML file.

    Returns:
        dict: The loaded YAML data.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding = "utf-8") as file:
        return yaml.safe_load(file)

def main():
    """
    This function is the main entry point of the Ansible module.
    It takes telemetry config file path as a parameter.

    This function loads the telemetry configuration from a YAML file,
        checks the status of various telemetry components,
        and returns the status as a list.

    Parameters:
       telemetry_config_path: path to telemetry_config.yml

    Returns:
        A list containing the telemetry status.

    Raises:
        None
    """
    module_args = {
        "telemetry_config_path": {
            "type": "str", "required": False, "default": TELEMETRY_CONFIG_PATH_DEFAULT
        }
    }
    module = AnsibleModule(argument_spec=module_args)
    telemetry_config_path = module.params["telemetry_config_path"]
    telemetry_config_data = load_yaml(telemetry_config_path)

    telemetry_status_list = []

    if telemetry_config_data["idrac_telemetry_support"]:
        telemetry_status_list.append("idrac_telemetry")
    if telemetry_config_data["visualization_support"]:
        telemetry_status_list.append("visualization")

    module.exit_json(
            changed=False,
            telemetry_status_list=telemetry_status_list
    )


if __name__ == "__main__":
    main()
