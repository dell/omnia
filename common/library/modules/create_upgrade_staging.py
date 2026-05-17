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
    Create staging directory with delta-updated configs for upgrade.

    Reads software_config.json and local_repo_config.yml from input_dir as the
    base and applies only the changes required by the hop chain. All original
    content is preserved; only the fields that need updating are changed.
    Files in input_dir are never modified.

    Args:
        staging_dir: Path to staging directory
        input_dir: Path to input project directory (/opt/omnia/input/project_default)
        repos_file: Path to repos.yml file
        enabled_components: List of enabled components
        current_sw_config: Current software_config.json content (base, read-only)
        architectures: List of architectures to process
        target_omnia_version: Target Omnia version
        calculated_hop_chains: List of calculated hop chains

    Returns:
        Dictionary containing staging summary
    """
    # --- 1. Determine final target version per component from hop chains ---
    # For multi-hop chains each component may appear multiple times;
    # we want the to_version of the last hop (highest hop_id) per component.
    component_final_versions = {}
    if calculated_hop_chains:
        component_hops = {}
        for hop in calculated_hop_chains:
            cname = hop.get('software')
            if cname:
                component_hops.setdefault(cname, []).append(hop)

        for cname, hops in component_hops.items():
            final_hop = max(
                hops,
                key=lambda h: int(h.get('hop_id', 'hop_0').split('_')[1])
            )
            component_final_versions[cname] = final_hop.get('to_version')
            print(f"Final target for {cname}: {component_final_versions[cname]}")

    # --- 2. Create staging software_config.json (base + delta version updates) ---
    # Deep-copy the base config so input_dir is never touched.
    sw_config = json.loads(json.dumps(current_sw_config))

    sw_delta_count = 0
    for sw in sw_config.get('softwares', []):
        name = sw.get('name')
        if name in component_final_versions:
            target_ver = component_final_versions[name]
            current_ver = sw.get('version', '')
            if current_ver != target_ver:
                sw['version'] = target_ver
                sw_delta_count += 1
                print(f"Delta update: {name} {current_ver} -> {target_ver}")
            else:
                print(f"Already at target version: {name} {target_ver} (no change needed)")
        else:
            print(f"Preserved unchanged: {name}")

    with open(os.path.join(staging_dir, 'software_config.json'), 'w') as f:
        json.dump(sw_config, f, indent=4)
    print(f"software_config.json written to staging ({sw_delta_count} version(s) updated)")

    # --- 3. Create staging local_repo_config.yml (base + delta repo additions) ---
    # Load base from input_dir; keep all existing repos intact.
    local_repo_config_path = os.path.join(input_dir, 'local_repo_config.yml')
    base_config = {}
    if os.path.exists(local_repo_config_path):
        with open(local_repo_config_path) as f:
            base_config = yaml.safe_load(f) or {}
        print(f"Loaded base local_repo_config.yml from {local_repo_config_path}")
    else:
        print(f"Warning: local_repo_config.yml not found at {local_repo_config_path}, starting with empty config")

    # Build deduplication sets from existing repos in the base config.
    seen_x86 = {
        entry.get('name', '')
        for entry in base_config.get('omnia_repo_url_rhel_x86_64', [])
        if entry.get('name')
    }
    seen_aarch64 = {
        entry.get('name', '')
        for entry in base_config.get('omnia_repo_url_rhel_aarch64', [])
        if entry.get('name')
    }

    repos_added = 0

    if os.path.exists(repos_file):
        with open(repos_file) as f:
            repos = yaml.safe_load(f) or {}

        # Collect Omnia versions whose repos need to be merged.
        omnia_versions_to_merge = set()
        if calculated_hop_chains:
            for hop in calculated_hop_chains:
                hop_omnia_version = hop.get('omnia_version')
                if hop_omnia_version:
                    omnia_versions_to_merge.add(hop_omnia_version)
                    print(f"Will merge repos for Omnia version: {hop_omnia_version}")
        else:
            omnia_versions_to_merge.add(target_omnia_version)

        if 'omnia_versions' in repos:
            print("Using Omnia version-specific repository structure")
            for omnia_version in omnia_versions_to_merge:
                target_repos = repos['omnia_versions'].get(omnia_version, {})
                for repo_section_name, repo_entries in target_repos.items():
                    if not isinstance(repo_entries, list):
                        continue
                    if 'x86_64' in repo_section_name.lower():
                        for entry in repo_entries:
                            rname = entry.get('name', '')
                            if rname and rname not in seen_x86:
                                seen_x86.add(rname)
                                base_config.setdefault('omnia_repo_url_rhel_x86_64', []).append(entry)
                                repos_added += 1
                                print(f"Added x86_64 repo: {rname} (Omnia {omnia_version})")
                            elif rname:
                                print(f"Skipped duplicate x86_64 repo: {rname}")
                    elif 'aarch64' in repo_section_name.lower():
                        for entry in repo_entries:
                            rname = entry.get('name', '')
                            if rname and rname not in seen_aarch64:
                                seen_aarch64.add(rname)
                                base_config.setdefault('omnia_repo_url_rhel_aarch64', []).append(entry)
                                repos_added += 1
                                print(f"Added aarch64 repo: {rname} (Omnia {omnia_version})")
                            elif rname:
                                print(f"Skipped duplicate aarch64 repo: {rname}")
        else:
            # Fallback to legacy flat structure for backward compatibility
            print("Using legacy flat repository structure")
            for entry in (repos.get('omnia_repo_url_rhel_x86_64') or []):
                rname = entry.get('name', '')
                if rname and rname not in seen_x86:
                    seen_x86.add(rname)
                    base_config.setdefault('omnia_repo_url_rhel_x86_64', []).append(entry)
                    repos_added += 1
                    print(f"Added x86_64 repo (legacy): {rname}")
            for entry in (repos.get('omnia_repo_url_rhel_aarch64') or []):
                rname = entry.get('name', '')
                if rname and rname not in seen_aarch64:
                    seen_aarch64.add(rname)
                    base_config.setdefault('omnia_repo_url_rhel_aarch64', []).append(entry)
                    repos_added += 1
                    print(f"Added aarch64 repo (legacy): {rname}")
    else:
        print(f"Warning: repos.yml not found at {repos_file}, no upgrade repos added to base config")

    print(f"local_repo_config.yml: {repos_added} repo(s) added from repos.yml to base config")

    with open(os.path.join(staging_dir, 'local_repo_config.yml'), 'w') as f:
        yaml.dump(base_config, f, default_flow_style=False, sort_keys=False)

    # --- 4. Copy vault credentials files if they exist ---
    vault_key_file = os.path.join(input_dir, '.omnia_config_credentials_key')
    vault_creds_file = os.path.join(input_dir, 'omnia_config_credentials.yml')

    if os.path.exists(vault_key_file):
        shutil.copy2(vault_key_file, os.path.join(staging_dir, '.omnia_config_credentials_key'))
        print("Copied vault credentials key: .omnia_config_credentials_key")
    else:
        print("No vault credentials key found in input directory")

    if os.path.exists(vault_creds_file):
        shutil.copy2(vault_creds_file, os.path.join(staging_dir, 'omnia_config_credentials.yml'))
        print("Copied vault credentials file: omnia_config_credentials.yml")
    else:
        print("No vault credentials file found in input directory")

    # --- 5. Copy JSON config files from input_dir to staging ---
    os_type = sw_config.get('cluster_os_type', 'rhel')
    os_version = sw_config.get('cluster_os_version', '10.0')

    json_files_copied = []

    for arch in architectures:
        src_config_dir = os.path.join(input_dir, 'config', arch, os_type, os_version)
        dst_config_dir = os.path.join(staging_dir, 'config', arch, os_type, os_version)

        if not os.path.exists(src_config_dir):
            print(f"Skipping architecture {arch}: source config dir not found: {src_config_dir}")
            continue

        os.makedirs(dst_config_dir, exist_ok=True)

        for json_file in os.listdir(src_config_dir):
            if json_file.endswith('.json'):
                src_json = os.path.join(src_config_dir, json_file)
                dst_json = os.path.join(dst_config_dir, json_file)

                if not os.path.exists(dst_json):
                    shutil.copy2(src_json, dst_json)
                    json_files_copied.append(f"{arch}/{os_type}/{os_version}/{json_file}")
                    print(f"Copied: {json_file} ({arch})")

    vault_key_copied = os.path.exists(os.path.join(staging_dir, '.omnia_config_credentials_key'))
    vault_creds_copied = os.path.exists(os.path.join(staging_dir, 'omnia_config_credentials.yml'))

    return {
        'staging_dir': staging_dir,
        'software_config_updated': sw_delta_count > 0,
        'repos_merged': repos_added,
        'json_files_copied': json_files_copied,
        'vault_key_copied': vault_key_copied,
        'vault_credentials_copied': vault_creds_copied,
        'enabled_components': [c.get('key') for c in enabled_components]
    }


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
