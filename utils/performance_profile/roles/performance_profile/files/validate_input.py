# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import yaml
import json
import sys, os

def load_performance_config(file_path):
    """
    Loads and validates the tuned configuration from a YAML file.

    Args:
        file_path (str): Path to the YAML configuration file.

    Returns:
        dict: Parsed and validated tuned configuration.

    Raises:
        SystemExit: If any validation fails, exits the program with an error message.
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    intel_gpu = data.get('intel_gpu', {})

    if not intel_gpu:
        sys.exit("intel_gpu not found")

    performance_profile_name = intel_gpu.get('performance_profile', {})

    if not performance_profile_name:
        sys.exit("performance_profie is empty.")

    performance_profile_plugin = intel_gpu.get('performance_profile_plugin', {})

    if not performance_profile_plugin:
        print("performance_profile_plugin is empty. Setting profile values to default.")
        return

    if not isinstance(performance_profile_plugin, dict):
        sys.exit("Invalid format for performance_profile_plugin")

    if not all(isinstance(value, list) for value in performance_profile_plugin.values()):
        sys.exit("Invalid format for performance_profile_plugin")

    if not all(isinstance(item, dict) for value in performance_profile_plugin.values() for item in value if item is not None):
        sys.exit("Invalid format for performance_profile_plugin")

    for key, value in performance_profile_plugin.items():
        if not value:
            sys.exit(f"Missing values for {key}")

        for item in value:
            if not item:
                sys.exit(f"Missing key-value pairs in {key}")

            for key, value in item.items():
                if value is None:
                    sys.exit(f"Missing values  for {key}")

                print(f"{key} = {value}")

    if 'reboot_required' not in intel_gpu:
        sys.exit("reboot_required is missing")

    if not isinstance(intel_gpu['reboot_required'], bool):
        sys.exit("reboot_required must be either 'true' or 'false'")

    return intel_gpu

def main():
    file_path = os.path.abspath(sys.argv[1])

    try:
        result = load_performance_config(file_path)
        print("All validations passed")
        print(result)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
