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

"""Ansible module to create staging directory with modified configs for upgrade."""

from ansible.module_utils.basic import AnsibleModule
import json
import yaml
import os
import shutil


def create_staging(
    staging_dir,
    input_dir,
    repos_file,
    enabled_components,
    current_sw_config,
    architectures,
    target_omnia_version,
    calculated_hop_chains
):
    """
    Create staging directory with modified configs for upgrade.

    Args:
        staging_dir: Path to staging directory
        input_dir: Path to input project directory
        repos_file: Path to repos.yml file
        enabled_components: List of enabled components
        current_sw_config: Current software_config.json content
        architectures: List of architectures to process
        target_omnia_version: Target Omnia version
        calculated_hop_chains: List of calculated hop chains

    Returns:
        Dictionary containing staging summary
    """
    # --- 1. Create software_config.json with all hop versions for multi-hop support ---
    sw_config = current_sw_config.copy()
    
    # For multi-hop upgrades, add all hop versions to software_config.json
    # This ensures local_repo downloads packages for all intermediate versions
    # Only include upgrade components and essential shared components
    essential_components = {'default_packages', 'additional_packages', 'admin_debug_packages'}
    
    if calculated_hop_chains:
        print(f"Multi-hop upgrade detected with {len(calculated_hop_chains)} hops")
        
        # Collect unique component versions from all hops
        component_versions = {}
        for hop in calculated_hop_chains:
            component_name = hop.get('software')
            to_version = hop.get('to_version')
            if component_name and to_version:
                if component_name not in component_versions:
                    component_versions[component_name] = set()
                component_versions[component_name].add(to_version)
        
        # Update software_config.json to include only upgrade components + essentials
        updated_softwares = []
        for sw in sw_config.get('softwares', []):
            component_name = sw.get('name')
            
            # Check if this component is in hop chains OR is essential
            if component_name in component_versions:
                # Add entries for all versions of this component
                for version in component_versions[component_name]:
                    new_entry = sw.copy()
                    new_entry['version'] = version
                    updated_softwares.append(new_entry)
                    print(f"Added {component_name} version {version} to software_config.json")
            elif component_name in essential_components:
                # Keep essential components (may have dependencies)
                updated_softwares.append(sw)
                print(f"Kept essential component: {component_name}")
            else:
                # Skip non-essential, non-upgrade components
                print(f"Skipped non-essential component: {component_name}")
        
        sw_config['softwares'] = updated_softwares
    else:
        # Single-hop: use target version (already updated by manage_upgrade_inputs)
        # Still filter to only include upgrade components + essentials
        print("Single-hop upgrade: using target version from software_config.json")
        
        # Get upgrade components from hop chains (single hop)
        upgrade_components = set()
        if calculated_hop_chains and len(calculated_hop_chains) > 0:
            for hop in calculated_hop_chains:
                upgrade_components.add(hop.get('software'))
        
        # Filter software_config.json
        updated_softwares = []
        for sw in sw_config.get('softwares', []):
            component_name = sw.get('name')
            
            # Keep upgrade components and essential components
            if component_name in upgrade_components or component_name in essential_components:
                updated_softwares.append(sw)
                print(f"Kept component: {component_name}")
            else:
                print(f"Skipped non-essential component: {component_name}")
        
        sw_config['softwares'] = updated_softwares
    
    # Write software_config.json to staging
    with open(os.path.join(staging_dir, 'software_config.json'), 'w') as f:
        json.dump(sw_config, f, indent=4)
    
    # --- 2. Create local_repo_config.yml with only repos from repos.yml ---
    # Base repos (docker-ce, epel, doca, cuda) are already synced from initial
    # installation and are not included to avoid unnecessary re-syncing.
    # Staging only contains upgrade-specific repos from repos.yml.
    
    # Initialize empty lists (no base config merge)
    merged_x86 = []
    merged_aarch64 = []
    seen_x86 = set()
    seen_aarch64 = set()
    base_config = {}  # Empty base config - only repos from repos.yml will be added
    
    # Load repos from repos.yml (upgrade-specific repos only)
    if os.path.exists(repos_file):
        with open(repos_file) as f:
            repos = yaml.safe_load(f) or {}
        
        print(f"Target Omnia version: {target_omnia_version}")
        
        # Check for new Omnia version-specific structure
        if 'omnia_versions' in repos:
            print("Using Omnia version-specific repository structure (upgrade-specific repos only)")
            
            # For multi-hop upgrades, collect Omnia versions from all hops
            omnia_versions_to_merge = set()
            if calculated_hop_chains:
                for hop in calculated_hop_chains:
                    hop_omnia_version = hop.get('omnia_version')
                    if hop_omnia_version:
                        omnia_versions_to_merge.add(hop_omnia_version)
                        print(f"Adding repositories for Omnia version: {hop_omnia_version}")
            else:
                # Single-hop: use target version only
                omnia_versions_to_merge.add(target_omnia_version)
            
            # Process ALL repository sections for each Omnia version
            for omnia_version in omnia_versions_to_merge:
                target_repos = repos['omnia_versions'].get(omnia_version, {})
                
                for repo_section_name, repo_entries in target_repos.items():
                    if isinstance(repo_entries, list):
                        # Determine architecture based on section name
                        if 'x86_64' in repo_section_name.lower():
                            # Process x86_64 repositories
                            for entry in repo_entries:
                                if entry.get('name', '') not in seen_x86:
                                    seen_x86.add(entry.get('name', ''))
                                    merged_x86.append(entry)
                                    print(f"Added x86_64 repo from {repo_section_name} for Omnia {omnia_version}: {entry.get('name', '')}")
                        elif 'aarch64' in repo_section_name.lower():
                            # Process aarch64 repositories
                            for entry in repo_entries:
                                if entry.get('name', '') not in seen_aarch64:
                                    seen_aarch64.add(entry.get('name', ''))
                                    merged_aarch64.append(entry)
                                    print(f"Added aarch64 repo from {repo_section_name} for Omnia {omnia_version}: {entry.get('name', '')}")
        
        else:
            # Fallback to legacy flat structure for backward compatibility
            print("Using legacy flat repository structure (upgrade-specific repos only)")
            
            for entry in (repos.get('omnia_repo_url_rhel_x86_64') or []):
                if entry.get('name', '') not in seen_x86:
                    seen_x86.add(entry.get('name', ''))
                    merged_x86.append(entry)
                    print(f"Added x86_64 repo (legacy): {entry.get('name', '')}")
            
            for entry in (repos.get('omnia_repo_url_rhel_aarch64') or []):
                if entry.get('name', '') not in seen_aarch64:
                    seen_aarch64.add(entry.get('name', ''))
                    merged_aarch64.append(entry)
                    print(f"Added aarch64 repo (legacy): {entry.get('name', '')}")
    
    base_config['omnia_repo_url_rhel_x86_64'] = merged_x86
    base_config['omnia_repo_url_rhel_aarch64'] = merged_aarch64
    
    # Write merged local_repo_config.yml to staging
    with open(os.path.join(staging_dir, 'local_repo_config.yml'), 'w') as f:
        yaml.dump(base_config, f, default_flow_style=False, sort_keys=False)
    
    # --- 2.5. Copy vault credentials files if they exist ---
    vault_key_file = os.path.join(input_dir, '.omnia_config_credentials_key')
    vault_creds_file = os.path.join(input_dir, 'omnia_config_credentials.yml')
    
    # Copy vault key file
    if os.path.exists(vault_key_file):
        staging_vault_key = os.path.join(staging_dir, '.omnia_config_credentials_key')
        shutil.copy2(vault_key_file, staging_vault_key)
        print(f"Copied vault credentials key: .omnia_config_credentials_key")
    else:
        print("No vault credentials key found in input directory")
    
    # Copy vault credentials file (encrypted)
    if os.path.exists(vault_creds_file):
        staging_vault_creds = os.path.join(staging_dir, 'omnia_config_credentials.yml')
        shutil.copy2(vault_creds_file, staging_vault_creds)
        print(f"Copied vault credentials file: omnia_config_credentials.yml")
    else:
        print("No vault credentials file found in input directory")
    
    # --- 3. Copy JSON files from input directory for enabled upgrades ---
    os_type = sw_config.get('cluster_os_type', 'rhel')
    os_version = sw_config.get('cluster_os_version', '10.0')
    
    json_files_copied = []
    available_architectures = []
    
    for arch in architectures:
        src_config_dir = os.path.join(input_dir, 'config', arch, os_type, os_version)
        dst_config_dir = os.path.join(staging_dir, 'config', arch, os_type, os_version)
        
        if not os.path.exists(src_config_dir):
            print(f"Skipping architecture {arch}: source config dir not found: {src_config_dir}")
            continue
        
        os.makedirs(dst_config_dir, exist_ok=True)
        available_architectures.append(arch)
        
        # Copy ALL JSON files from source config directory to staging
        # This ensures all component JSON files (including default_packages, admin_debug_packages, etc.)
        # are available for the local_repo sync
        if os.path.exists(src_config_dir):
            for json_file in os.listdir(src_config_dir):
                if json_file.endswith('.json'):
                    src_json = os.path.join(src_config_dir, json_file)
                    dst_json = os.path.join(dst_config_dir, json_file)
                    
                    if os.path.exists(src_json) and not os.path.exists(dst_json):
                        shutil.copy2(src_json, dst_json)
                        json_files_copied.append(f"{arch}/{os_type}/{os_version}/{json_file}")
                        print(f"Copied: {json_file} ({arch})")
    
    # Keep original software_config.json intact - don't filter architectures
    
    # Check if vault credentials were copied
    vault_key_copied = os.path.exists(os.path.join(staging_dir, '.omnia_config_credentials_key'))
    vault_creds_copied = os.path.exists(os.path.join(staging_dir, 'omnia_config_credentials.yml'))
    
    # Output summary
    result = {
        'staging_dir': staging_dir,
        'software_config_updated': True,
        'repos_merged': len(merged_x86) + len(merged_aarch64),
        'json_files_copied': json_files_copied,
        'vault_key_copied': vault_key_copied,
        'vault_credentials_copied': vault_creds_copied,
        'enabled_components': [c.get('key') for c in enabled_components]
    }
    
    return result


def run_module():
    """
    Run the Ansible module.

    Creates a staging directory with modified configs for upgrade.
    """
    module_args = dict(
        staging_dir=dict(type="str", required=True),
        input_dir=dict(type="str", required=True),
        repos_file=dict(type="str", required=True),
        enabled_components=dict(type="list", required=True),
        current_software_config=dict(type="dict", required=True),
        architectures=dict(type="list", required=True),
        target_omnia_version=dict(type="str", required=True),
        calculated_hop_chains=dict(type="list", required=False, default=[]),
    )

    result = dict(
        changed=False,
        staging_dir='',
        software_config_updated=False,
        repos_merged=0,
        json_files_copied=[],
        vault_key_copied=False,
        vault_credentials_copied=False,
        enabled_components=[]
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    staging_dir = module.params["staging_dir"]
    input_dir = module.params["input_dir"]
    repos_file = module.params["repos_file"]
    enabled_components = module.params["enabled_components"]
    current_software_config = module.params["current_software_config"]
    architectures = module.params["architectures"]
    target_omnia_version = module.params["target_omnia_version"]
    calculated_hop_chains = module.params["calculated_hop_chains"]

    # Create staging using the library function
    staging_result = create_staging(
        staging_dir,
        input_dir,
        repos_file,
        enabled_components,
        current_software_config,
        architectures,
        target_omnia_version,
        calculated_hop_chains
    )

    result["changed"] = True
    result["staging_dir"] = staging_result["staging_dir"]
    result["software_config_updated"] = staging_result["software_config_updated"]
    result["repos_merged"] = staging_result["repos_merged"]
    result["json_files_copied"] = staging_result["json_files_copied"]
    result["vault_key_copied"] = staging_result["vault_key_copied"]
    result["vault_credentials_copied"] = staging_result["vault_credentials_copied"]
    result["enabled_components"] = staging_result["enabled_components"]

    module.exit_json(**result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
