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

import json
import sys

backup_file = sys.argv[1]
target_file = sys.argv[2]

# Hardcoded version map for Omnia 2.1 → 2.2 upgrade
# These are the target versions for software entries that should be updated
TARGET_VERSIONS = {
    "service_k8s": "1.35.1",
    "csi_driver_powerscale": "v2.16.0"
}

with open(backup_file, 'r') as f:
    backup = json.load(f)

# Start with a copy of the backup (preserves user's configuration exactly)
result = json.loads(json.dumps(backup))

# Update version fields in existing softwares entries from backup
# If backup has service_k8s with version 1.34.1, update it to 1.35.1
for sw in result.get('softwares', []):
    name = sw.get('name', '')
    if name in TARGET_VERSIONS:
        old_ver = sw.get('version', '')
        new_ver = TARGET_VERSIONS[name]
        if old_ver != new_ver:
            sw['version'] = new_ver
            print(f"Updated softwares['{name}'] version: {old_ver} -> {new_ver}", file=sys.stderr)
        elif not old_ver and new_ver:
            # If backup entry doesn't have version but target does, add it
            sw['version'] = new_ver
            print(f"Added version {new_ver} to softwares['{name}']", file=sys.stderr)

# If additional_packages exists as a TOP-LEVEL key in backup, append "os" if not present
# This is the array like: "additional_packages": [{"name": "..."}, ...]
if 'additional_packages' in result and isinstance(result['additional_packages'], list):
    existing_names = {item.get('name') for item in result['additional_packages'] if isinstance(item, dict) and 'name' in item}
    if 'os' not in existing_names:
        result['additional_packages'].append({"name": "os"})
        print("Added {'name': 'os'} to additional_packages array", file=sys.stderr)

# Write the result with compact formatting (no extra whitespace in arrays)
with open(target_file, 'w') as f:
    json.dump(result, f, indent=4, separators=(',', ': '))
    f.write('\n')

print("software_config.json transformation complete")
