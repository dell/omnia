#!/usr/bin/env python3
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

"""
Merge PowerScale CSI driver values.yaml from v2.15 to v2.16.
Preserves critical user settings from v2.1 while using v2.16 structure.
"""

import sys
import yaml


def merge_values(v21_file_path, v216_file_path, output_file_path):
    """
    Merge v2.1 PowerScale values into v2.16 template.

    Args:
        v21_file_path: Path to v2.1 values.yaml (source settings)
        v216_file_path: Path to v2.16 values.yaml (target structure)
        output_file_path: Path to write merged values.yaml
    """
    # Load v2.1 values (source of user settings)
    with open(v21_file_path, 'r', encoding='utf-8') as file_handle:
        v21_values = yaml.safe_load(file_handle)

    # Load v2.16 values (target structure with new defaults)
    with open(v216_file_path, 'r', encoding='utf-8') as file_handle:
        v216_values = yaml.safe_load(file_handle)

    # Parameters to preserve from v2.1
    preserve_params = [
        'isiPath',
        'isiAccessZone',
        'logLevel',
        'arrayConnectivityPollRate',
    ]

    # Preserve top-level parameters
    for param in preserve_params:
        if param in v21_values:
            v216_values[param] = v21_values[param]
            print(f"Preserved {param}: {v21_values[param]}",
                  file=sys.stderr)

    # Preserve feature flags if enabled in v2.1
    feature_flags = [
        'storageCapacity',
        'podmon',
        'authorization',
        'replication',
        'observability',
    ]

    for feature in feature_flags:
        if feature in v21_values and isinstance(v21_values[feature], dict):
            if 'enabled' in v21_values[feature]:
                if feature not in v216_values:
                    v216_values[feature] = {}
                v216_values[feature]['enabled'] = \
                    v21_values[feature]['enabled']
                print(f"Preserved {feature}.enabled: "
                      f"{v21_values[feature]['enabled']}",
                      file=sys.stderr)

    # Preserve controller settings
    if 'controller' in v21_values and \
       isinstance(v21_values['controller'], dict):
        if 'controller' not in v216_values:
            v216_values['controller'] = {}

        controller_params = ['nodeSelector', 'tolerations', 'controllerCount']
        for param in controller_params:
            if param in v21_values['controller']:
                v216_values['controller'][param] = \
                    v21_values['controller'][param]
                print(f"Preserved controller.{param}: {v21_values['controller'][param]}", file=sys.stderr)

    # Preserve node settings
    if 'node' in v21_values and isinstance(v21_values['node'], dict):
        if 'node' not in v216_values:
            v216_values['node'] = {}

        node_params = ['nodeSelector', 'tolerations']
        for param in node_params:
            if param in v21_values['node']:
                v216_values['node'][param] = v21_values['node'][param]
                print(f"Preserved node.{param}", file=sys.stderr)

    # Write merged values to output file
    with open(output_file_path, 'w', encoding='utf-8') as file_handle:
        yaml.dump(v216_values, file_handle,
                  default_flow_style=False, sort_keys=False)

    print("Successfully merged v2.1 settings into v2.16 values.yaml",
          file=sys.stderr)
    print(f"Output written to: {output_file_path}", file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: merge_powerscale_values.py <v21_values.yaml> "
              "<v216_values.yaml> <output.yaml>", file=sys.stderr)
        sys.exit(1)

    v21_input = sys.argv[1]
    v216_input = sys.argv[2]
    output_path = sys.argv[3]

    try:
        merge_values(v21_input, v216_input, output_path)
    except (IOError, yaml.YAMLError) as error:
        print(f"ERROR: Failed to merge PowerScale values.yaml: {error}",
              file=sys.stderr)
        sys.exit(1)
