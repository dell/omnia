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


def merge_values(vold_file_path, vnew_file_path, output_file_path):
    """
    Merge old PowerScale values into new template.

    Args:
        vold_file_path: Path to old values.yaml (source settings)
        vnew_file_path: Path to new values.yaml (target structure)
        output_file_path: Path to write merged values.yaml
    """
    # Load old values (source of user settings)
    with open(vold_file_path, 'r', encoding='utf-8') as file_handle:
        vold_values = yaml.safe_load(file_handle)

    # Load new values (target structure with new defaults)
    with open(vnew_file_path, 'r', encoding='utf-8') as file_handle:
        vnew_values = yaml.safe_load(file_handle)

    # Parameters to preserve from old version
    preserve_params = [
        'isiPath',
        'isiAccessZone',
        'logLevel',
        'arrayConnectivityPollRate',
    ]

    # Preserve top-level parameters
    for param in preserve_params:
        if param in vold_values:
            vnew_values[param] = vold_values[param]
            print(f"Preserved {param}: {vold_values[param]}",
                  file=sys.stderr)

    # Preserve feature flags if enabled in old version
    feature_flags = [
        'storageCapacity',
        'podmon',
        'authorization',
        'replication',
        'observability',
    ]

    for feature in feature_flags:
        if feature in vold_values and isinstance(vold_values[feature], dict):
            if 'enabled' in vold_values[feature]:
                if feature not in vnew_values:
                    vnew_values[feature] = {}
                vnew_values[feature]['enabled'] = \
                    vold_values[feature]['enabled']
                print(f"Preserved {feature}.enabled: "
                      f"{vold_values[feature]['enabled']}",
                      file=sys.stderr)

    # Preserve healthMonitor with both enabled and interval
    if 'healthMonitor' in vold_values and isinstance(vold_values['healthMonitor'], dict):
        if 'healthMonitor' not in vnew_values:
            vnew_values['healthMonitor'] = {}
        for param in ['enabled', 'interval']:
            if param in vold_values['healthMonitor']:
                vnew_values['healthMonitor'][param] = vold_values['healthMonitor'][param]
                print(f"Preserved healthMonitor.{param}: {vold_values['healthMonitor'][param]}", file=sys.stderr)

    # Preserve controller settings
    if 'controller' in vold_values and \
       isinstance(vold_values['controller'], dict):
        if 'controller' not in vnew_values:
            vnew_values['controller'] = {}

        controller_params = ['nodeSelector', 'tolerations', 'controllerCount']
        for param in controller_params:
            if param in vold_values['controller']:
                vnew_values['controller'][param] = \
                    vold_values['controller'][param]
                print(f"Preserved controller.{param}: {vold_values['controller'][param]}", file=sys.stderr)

        # Preserve controller-level healthMonitor
        if 'healthMonitor' in vold_values['controller'] and isinstance(vold_values['controller']['healthMonitor'], dict):
            if 'healthMonitor' not in vnew_values['controller']:
                vnew_values['controller']['healthMonitor'] = {}
            for param in ['enabled', 'interval']:
                if param in vold_values['controller']['healthMonitor']:
                    vnew_values['controller']['healthMonitor'][param] = vold_values['controller']['healthMonitor'][param]
                    print(f"Preserved controller.healthMonitor.{param}: {vold_values['controller']['healthMonitor'][param]}", file=sys.stderr)

    # Preserve node settings
    if 'node' in vold_values and isinstance(vold_values['node'], dict):
        if 'node' not in vnew_values:
            vnew_values['node'] = {}

        node_params = ['nodeSelector', 'tolerations']
        for param in node_params:
            if param in vold_values['node']:
                vnew_values['node'][param] = vold_values['node'][param]
                print(f"Preserved node.{param}", file=sys.stderr)

        # Preserve node-level healthMonitor
        if 'healthMonitor' in vold_values['node'] and isinstance(vold_values['node']['healthMonitor'], dict):
            if 'healthMonitor' not in vnew_values['node']:
                vnew_values['node']['healthMonitor'] = {}
            if 'enabled' in vold_values['node']['healthMonitor']:
                vnew_values['node']['healthMonitor']['enabled'] = vold_values['node']['healthMonitor']['enabled']
                print(f"Preserved node.healthMonitor.enabled: {vold_values['node']['healthMonitor']['enabled']}", file=sys.stderr)

    # Write merged values to output file
    with open(output_file_path, 'w', encoding='utf-8') as file_handle:
        yaml.dump(vnew_values, file_handle,
                  default_flow_style=False, sort_keys=False)

    print("Successfully merged old settings into new values.yaml",
          file=sys.stderr)
    print(f"Output written to: {output_file_path}", file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: merge_powerscale_values.py <old_values.yaml> "
              "<new_values.yaml> <output.yaml>", file=sys.stderr)
        sys.exit(1)

    vold_input = sys.argv[1]
    vnew_input = sys.argv[2]
    output_path = sys.argv[3]

    try:
        merge_values(vold_input, vnew_input, output_path)
    except (IOError, yaml.YAMLError) as error:
        print(f"ERROR: Failed to merge PowerScale values.yaml: {error}",
              file=sys.stderr)
        sys.exit(1)
