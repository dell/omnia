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
Upgrade Input Management Module

This module provides functionality for managing upgrade input configurations:
- Calculate upgrade hop chains from upgrade_manifest.yml
- Update software_config.json with target versions
- Update component JSON files with version-specific repo names

Production Design (upgrade_manifest.yml):
  omnia_upgrade_paths (top-level): defines the Omnia version upgrade sequence.
    Each entry specifies the software versions for the NEXT Omnia version.

  components: defines each software component and its valid version sequence.
    supported_versions: ordered list used for automatic intermediate hop
    generation when a K8s version gap is detected.

Automatic intermediate hop detection:
  When the target K8s version skips one or more entries in supported_versions,
  the system auto-generates one K8s hop per intermediate version.

  Example: Omnia 2.1.0.0 (K8s 1.34.1) -> Omnia 2.3.0.0 (K8s 1.37.1)
    Omnia path : 2.1.0.0 -> 2.2.0.0 -> 2.3.0.0
    K8s hops   : 1.34.1 -> 1.35.1  (Omnia 2.1->2.2, direct)
                 1.35.1 -> 1.36.1  (auto-generated, within 2.2->2.3)
                 1.36.1 -> 1.37.1  (Omnia 2.2->2.3, final)
    Total hops : 3
"""

import json
import os
from typing import Dict, List, Any


def find_hop_chain(
    component_name: str,
    component_config: Dict[str, Any],
    omnia_upgrade_paths: Dict[str, Any],
    current_omnia_version: str,
    target_omnia_version: str,
    current_software_version: str
) -> List[Dict[str, str]]:
    """
    Calculate hop chain for a component from current to target Omnia version.

    Traverses the top-level omnia_upgrade_paths and, for each Omnia hop,
    checks whether the K8s version transition requires intermediate steps
    based on the component's supported_versions list.

    Args:
        component_name: Component name (e.g., 'service_k8s')
        component_config: Component config from upgrade_manifest.yml
        omnia_upgrade_paths: Top-level omnia_upgrade_paths from upgrade_manifest.yml
        current_omnia_version: Current Omnia version (from oim_metadata.yml)
        target_omnia_version: Target Omnia version (from oim_metadata.yml)
        current_software_version: Current software version (from software_config.json)

    Returns:
        List of hop dicts, each containing:
            hop_id, software, from_omnia_version, to_omnia_version,
            from_version, to_version, json_file, omnia_version, auto_generated
    """
    supported_versions = component_config.get('supported_versions', [])

    hops = []
    current_omnia = current_omnia_version
    current_sw_ver = current_software_version
    hop_id = 1

    while current_omnia != target_omnia_version:
        if current_omnia not in omnia_upgrade_paths:
            break
        if hop_id > 20:
            break

        path_info = omnia_upgrade_paths[current_omnia]
        next_omnia = path_info.get('next_omnia_version')
        software_versions = path_info.get('software_versions', {})
        target_sw_ver = software_versions.get(component_name)

        if not next_omnia or not target_sw_ver:
            break

        # Detect whether intermediate K8s hops are needed
        if (supported_versions
                and current_sw_ver in supported_versions
                and target_sw_ver in supported_versions):

            current_idx = supported_versions.index(current_sw_ver)
            target_idx = supported_versions.index(target_sw_ver)

            if target_idx > current_idx + 1:
                # Gap detected: auto-generate one hop per intermediate version
                for i in range(current_idx, target_idx):
                    from_ver = supported_versions[i]
                    to_ver = supported_versions[i + 1]
                    is_final = (i == target_idx - 1)

                    hops.append({
                        'hop_id': f"hop_{hop_id}",
                        'software': component_name,
                        'from_omnia_version': current_omnia,
                        'to_omnia_version': next_omnia if is_final else current_omnia,
                        'from_version': from_ver,
                        'to_version': to_ver,
                        'json_file': f"{component_name}_v{to_ver}.json",
                        'omnia_version': next_omnia,
                        'auto_generated': not is_final
                    })
                    hop_id += 1
            else:
                # Direct K8s hop — no gap in supported_versions
                hops.append({
                    'hop_id': f"hop_{hop_id}",
                    'software': component_name,
                    'from_omnia_version': current_omnia,
                    'to_omnia_version': next_omnia,
                    'from_version': current_sw_ver,
                    'to_version': target_sw_ver,
                    'json_file': f"{component_name}_v{target_sw_ver}.json",
                    'omnia_version': next_omnia,
                    'auto_generated': False
                })
                hop_id += 1
        else:
            # No supported_versions defined or version not in list: direct hop
            hops.append({
                'hop_id': f"hop_{hop_id}",
                'software': component_name,
                'from_omnia_version': current_omnia,
                'to_omnia_version': next_omnia,
                'from_version': current_sw_ver,
                'to_version': target_sw_ver,
                'json_file': f"{component_name}_v{target_sw_ver}.json",
                'omnia_version': next_omnia,
                'auto_generated': False
            })
            hop_id += 1

        current_omnia = next_omnia
        current_sw_ver = target_sw_ver

    return hops


def calculate_all_hop_chains(
    upgrade_config: Dict[str, Any],
    current_software_config: Dict[str, Any],
    current_omnia_version: str,
    target_omnia_version: str
) -> Dict[str, Any]:
    """
    Calculate hop chains for all enabled components.

    Reads the top-level omnia_upgrade_paths from upgrade_config and, for each
    enabled component, calls find_hop_chain which automatically generates
    intermediate K8s hops when version gaps are detected in supported_versions.

    Args:
        upgrade_config: Full upgrade configuration from upgrade_manifest.yml
        current_software_config: Current software_config.json content
        current_omnia_version: Current Omnia version from oim_metadata.yml
        target_omnia_version: Target Omnia version from oim_metadata.yml

    Returns:
        Dictionary containing:
            - hop_chains: List of all hop dictionaries
            - total_hops: Total number of hops
            - upgrade_mode: 'multi_hop' if total_hops > 1, else 'single_hop'
            - warnings: List of warning messages
    """
    all_hop_chains = []
    warnings = []

    components = upgrade_config.get('components', {})
    omnia_upgrade_paths = upgrade_config.get('omnia_upgrade_paths', {})

    if not omnia_upgrade_paths:
        warnings.append("No omnia_upgrade_paths defined in upgrade_manifest.yml")
        return {
            'hop_chains': [],
            'total_hops': 0,
            'upgrade_mode': 'single_hop',
            'warnings': warnings
        }

    # Build current software version map from software_config.json
    current_software_versions = {}
    for sw in current_software_config.get('softwares', []):
        if sw.get('name') and sw.get('version'):
            current_software_versions[sw['name']] = sw['version']

    for component_name, component_config in components.items():
        if not component_config.get('enabled', False):
            continue

        current_software_version = current_software_versions.get(component_name)
        if not current_software_version:
            warnings.append(
                f"Current version not found for {component_name} in software_config.json"
            )
            continue

        hops = find_hop_chain(
            component_name,
            component_config,
            omnia_upgrade_paths,
            current_omnia_version,
            target_omnia_version,
            current_software_version
        )

        all_hop_chains.extend(hops)

    return {
        'hop_chains': all_hop_chains,
        'total_hops': len(all_hop_chains),
        'upgrade_mode': 'multi_hop' if len(all_hop_chains) > 1 else 'single_hop',
        'warnings': warnings
    }


def update_software_config(
    input_file: str,
    hop_chains: List[Dict[str, str]],
    upgrade_mode: str
) -> Dict[str, Any]:
    """
    Update software_config.json with target versions from hop chains.

    Args:
        input_file: Path to software_config.json
        hop_chains: List of hop dictionaries from calculate_all_hop_chains
        upgrade_mode: 'multi_hop' or 'single_hop'

    Returns:
        Dictionary containing:
            - updated: List of updated software entries
            - mode: Upgrade mode
            - total_hops: Total number of hops
    """
    # Load current config
    with open(input_file) as f:
        config = json.load(f)

    # Find final version for each software (last hop in chain)
    updated = []
    software_final_versions = {}

    if upgrade_mode == 'multi_hop':
        # Group hops by software and find final version
        software_hops = {}
        for hop in hop_chains:
            software = hop['software']
            if software not in software_hops:
                software_hops[software] = []
            software_hops[software].append(hop)

        # Find final version for each software
        # Use integer sort on hop number to avoid string comparison issues (e.g. "hop_10" < "hop_2")
        for software, hops in software_hops.items():
            final_hop = max(hops, key=lambda h: int(h['hop_id'].split('_')[1]))
            software_final_versions[software] = final_hop['to_version']
    else:
        # Single hop - use the target version directly
        for hop in hop_chains:
            software_final_versions[hop['software']] = hop['to_version']

    # Update versions to final targets
    for sw in config.get('softwares', []):
        sw_name = sw.get('name')
        if sw_name in software_final_versions:
            old_version = sw.get('version', 'none')
            new_version = software_final_versions[sw_name]
            sw['version'] = new_version
            updated.append({
                'name': sw_name,
                'from': old_version,
                'to': new_version
            })

    # Write updated config
    with open(input_file, 'w') as f:
        json.dump(config, f, indent=4)

    # Output result
    result = {
        'updated': updated,
        'mode': upgrade_mode,
        'total_hops': len(hop_chains)
    }

    return result


def update_component_json_repos(
    input_dir: str,
    calculated_hop_chains: List[Dict[str, str]],
    architectures: List[str],
    versioned_repo_components: Dict[str, str]
) -> Dict[str, Any]:
    """
    Update component JSON files with version-specific repo names.

    Args:
        input_dir: Path to input project directory
        calculated_hop_chains: List of hop dictionaries
        architectures: List of architectures (e.g., ['x86_64', 'aarch64'])
        versioned_repo_components: Mapping of component to base repo name
            (e.g., {'slurm_custom': 'slurm_custom'})

    Returns:
        Dictionary containing:
            - success: Boolean indicating overall success
            - updated_files: List of updated file paths
            - messages: List of status messages
    """
    messages = []
    updated_files = []
    success = True

    print("=== Updating Component JSON Files with Version-Specific repo_names ===")

    # Process each calculated hop
    for hop in calculated_hop_chains:
        component_name = hop['software']
        target_version = hop['to_version']
        json_filename = hop['json_file']

        # Skip if component doesn't support versioned repositories
        if component_name not in versioned_repo_components:
            msg = f"Skipping {component_name} - no versioned repo support"
            messages.append(msg)
            print(msg)
            continue

        repo_base_name = versioned_repo_components[component_name]
        versioned_repo_name = f"{repo_base_name}-v{target_version}"

        msg = f"\nProcessing: {component_name} v{target_version}"
        messages.append(msg)
        print(msg)
        msg = f"  JSON file: {json_filename}"
        messages.append(msg)
        print(msg)
        msg = f"  Repo name: {repo_base_name} -> {versioned_repo_name}"
        messages.append(msg)
        print(msg)

        # Process each architecture
        for arch in architectures:
            json_path = os.path.join(input_dir, 'config', arch, 'rhel', '10.0', json_filename)

            if not os.path.exists(json_path):
                msg = f"  Warning: JSON file not found: {json_path}"
                messages.append(msg)
                print(msg)
                continue

            # Read JSON file
            try:
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
            except Exception as e:
                msg = f"  Error reading {json_path}: {e}"
                messages.append(msg)
                print(msg)
                success = False
                continue

            # Update repo_name entries
            updated = False
            for section_name, section_data in json_data.items():
                if isinstance(section_data, dict) and 'cluster' in section_data:
                    for package in section_data['cluster']:
                        if package.get('repo_name') == repo_base_name:
                            package['repo_name'] = versioned_repo_name
                            updated = True
                            msg = f"    Updated: {package.get('package')} -> {versioned_repo_name}"
                            messages.append(msg)
                            print(msg)

            # Write updated JSON file
            if updated:
                try:
                    with open(json_path, 'w') as f:
                        json.dump(json_data, f, indent=4)
                    msg = f"  Success: Updated {json_path}"
                    messages.append(msg)
                    print(msg)
                    updated_files.append(json_path)
                except Exception as e:
                    msg = f"  Error writing {json_path}: {e}"
                    messages.append(msg)
                    print(msg)
                    success = False
            else:
                msg = f"  No updates needed for {json_path}"
                messages.append(msg)
                print(msg)

    msg = "\n=== JSON repo_name Update Complete ==="
    messages.append(msg)
    print(msg)

    return {
        'success': success,
        'updated_files': updated_files,
        'messages': messages
    }


def main():
    """
    Main function for command-line usage.

    This allows the module to be used directly from Ansible playbooks
    via the ansible.builtin.shell or ansible.builtin.script modules.
    """
    import sys

    # Read input from stdin (expected JSON format)
    input_data = json.loads(sys.stdin.read())

    upgrade_config = input_data.get('upgrade_config', {})
    current_software_config = input_data.get('current_software_config', {})
    current_omnia_version = input_data.get('current_omnia_version')
    target_omnia_version = input_data.get('target_omnia_version')

    # Calculate hop chains
    result = calculate_all_hop_chains(
        upgrade_config,
        current_software_config,
        current_omnia_version,
        target_omnia_version
    )

    # Output result as JSON
    print(json.dumps(result))


if __name__ == '__main__':
    main()
