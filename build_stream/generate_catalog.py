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


#!/usr/bin/env python3
"""Generate updated catalog_rhel.json from input/config directory."""

import csv
import json
import os
import re
import argparse
from collections import defaultdict
from pathlib import Path


_FUNCTIONAL_BUNDLES = {
    "service_k8s",
    "slurm_custom",
}


_INFRA_BUNDLES = {
    "csi_driver_powerscale",
}

def load_json(filepath):
    """Load and return JSON from the given file path."""
    with open(filepath, 'r', encoding='utf-8') as json_file:
        return json.load(json_file)


def _is_infra_package_name(pkg_name: str) -> bool:
    """Return True if a package name should be considered infrastructure (CSI-related)."""
    name = (pkg_name or "").lower()
    has_csi_token = re.search(r'(^|[^a-z0-9])csi([^a-z0-9]|$)', name) is not None
    has_csi_prefix = name.startswith('csi-') or '/csi-' in name or name.endswith('/csi')
    return (
        has_csi_token
        or has_csi_prefix
        or 'powerscale' in name
        or 'snapshotter' in name
        or 'helm-charts' in name
    )

def load_software_config(config_path):
    """Load software_config.json.

    Returns:
      - allowed_by_arch: {arch -> set(bundle_name)}
      - bundle_roles: {bundle_name -> list(role_name)}
    """
    config = load_json(config_path)

    allowed_by_arch = {
        'x86_64': set(),
        'aarch64': set(),
    }

    for software in config.get('softwares', []):
        name = software.get('name')
        arches = software.get('arch', []) or []
        if not name:
            continue
        for arch in arches:
            if arch in allowed_by_arch:
                allowed_by_arch[arch].add(name)

    # bundle_roles is defined by top-level keys like "slurm_custom", "service_k8s", etc.
    # Each is a list of objects with {"name": "<role>"}.
    bundle_roles = {}
    for bundle_name, roles in config.items():
        if bundle_name in ['cluster_os_type', 'cluster_os_version', 'repo_config', 'softwares']:
            continue
        if not isinstance(roles, list):
            continue
        role_names = []
        for r in roles:
            if isinstance(r, dict) and r.get('name'):
                role_names.append(r['name'])
        if role_names:
            bundle_roles[bundle_name] = role_names

    return allowed_by_arch, bundle_roles


def _extract_arch_from_pxe_group(pxe_group: str):
    """Extract architecture suffix from PXE functional group name."""
    if pxe_group.endswith('_x86_64'):
        return 'x86_64'
    if pxe_group.endswith('_aarch64'):
        return 'aarch64'
    return None

def load_pxe_functional_groups(pxe_file):
    """Load PXE mapping file and extract unique functional group names."""
    functional_groups = set()

    with open(pxe_file, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            group_name = row.get('FUNCTIONAL_GROUP_NAME', '').strip()
            if group_name:
                functional_groups.add(group_name)

    return sorted(functional_groups)

def collect_packages_from_config(config_dir, allowed_bundles_by_arch):
    """Collect all packages from config JSON files, filtered by allowed bundles per arch."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
    packages = defaultdict(lambda: {
        'name': None,
        'type': None,
        'architectures': set(),
        'sources': [],
        'tag': None,
        'url': None,
        'version': None,
        'bundles': set(),
    })

    for root, _dirs, files in os.walk(config_dir):
        for file in files:
            if not file.endswith('.json'):
                continue

            # Extract bundle name from filename (e.g., 'service_k8s.json' -> 'service_k8s')
            bundle_name = file.replace('.json', '')

            filepath = os.path.join(root, file)
            # Extract arch from path (e.g., x86_64 or aarch64)
            path_parts = Path(filepath).parts
            arch = None
            for part in path_parts:
                if part in ['x86_64', 'aarch64']:
                    arch = part
                    break

            if not arch:
                continue

            # Skip if this bundle is not allowed for this architecture
            if bundle_name not in allowed_bundles_by_arch.get(arch, set()):
                print(f"  Skipping {file} for arch {arch} (not in software_config.json)")
                continue

            data = load_json(filepath)

            # Process each section in the JSON
            for _section_name, section_data in data.items():
                if not isinstance(section_data, dict) or 'cluster' not in section_data:
                    continue

                for pkg in section_data['cluster']:
                    pkg_name = pkg['package']
                    pkg_type = pkg['type']

                    # Create unique key
                    key = f"{pkg_name}_{pkg_type}"

                    packages[key]['name'] = pkg_name
                    packages[key]['type'] = pkg_type
                    packages[key]['architectures'].add(arch)
                    packages[key]['bundles'].add(bundle_name)

                    # Handle different package types
                    if pkg_type == 'rpm':
                        repo_name = pkg.get('repo_name', '')
                        if repo_name:
                            packages[key]['sources'].append({
                                'Architecture': arch,
                                'RepoName': repo_name
                            })
                    elif pkg_type in ['tarball', 'manifest', 'iso']:
                        url = pkg.get('url', '')
                        if url and '{{' not in url:  # Skip templated URLs for now
                            packages[key]['sources'].append({
                                'Architecture': arch,
                                'Uri': url
                            })
                        packages[key]['url'] = url
                    elif pkg_type == 'image':
                        tag = pkg.get('tag', '')
                        packages[key]['tag'] = tag
                        packages[key]['version'] = tag

    return packages

def generate_catalog(input_dir, software_config_path, pxe_mapping_file):
    """Generate complete catalog structure."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks

    # Load allowed software bundles from software_config.json
    allowed_bundles_by_arch, bundle_roles = load_software_config(software_config_path)
    print("Allowed software bundles by arch: x86_64={}, aarch64={}".format(
        sorted(allowed_bundles_by_arch.get('x86_64', set())),
        sorted(allowed_bundles_by_arch.get('aarch64', set()))
    ))

    # Load PXE functional groups
    pxe_groups = load_pxe_functional_groups(pxe_mapping_file)
    print("PXE functional groups: {}".format(pxe_groups))

    packages = collect_packages_from_config(input_dir, allowed_bundles_by_arch)

    # Convert sets to lists for JSON serialization
    for pkg_data in packages.values():
        pkg_data['architectures'] = sorted(list(pkg_data['architectures']))

    # Map packages to roles
    allowed_bundles = set().union(*allowed_bundles_by_arch.values())
    role_package_map, package_id_map = map_packages_to_roles(
        packages, input_dir, allowed_bundles, bundle_roles
    )
    print("Role to package mapping: {}".format(dict(role_package_map)))

    # Build catalog structure
    catalog = {
        "Catalog": {
            "Name": "Catalog",
            "Version": "1.0",
            "Identifier": "image-build",
            "FunctionalLayer": [],
            "BaseOS": [],
            "Infrastructure": [],
            "Drivers": [],
            "DriverPackages": {},
            "FunctionalPackages": {},
            "OSPackages": {},
            "InfrastructurePackages": {}
        }
    }

    # Categorize packages using the package_id_map
    os_packages = {}
    functional_packages = {}
    infra_packages = {}

    os_pkg_id_counter = 1
    infra_pkg_id_counter = 1

    for key, pkg_data in packages.items():
        pkg_name = pkg_data['name']
        bundles = set(pkg_data.get('bundles') or [])

        # Determine classification using bundle membership.
        # - Functional: only service_k8s and slurm_custom
        # - Infrastructure: csi_driver_powerscale (plus name-based fallback)
        # - BaseOS: everything else
        is_functional = bool(bundles & _FUNCTIONAL_BUNDLES)
        is_infra = bool(bundles & _INFRA_BUNDLES) or _is_infra_package_name(pkg_name)

        if is_infra:
            pkg_id = f"infrastructure_package_id_{infra_pkg_id_counter}"
            infra_pkg_id_counter += 1
            infra_packages[pkg_id] = create_infra_package_entry(pkg_data)
            continue

        if is_functional:
            # Use the package_id from package_id_map
            if key in package_id_map:
                pkg_id = package_id_map[key]
                functional_packages[pkg_id] = create_package_entry(pkg_data)
            continue

        pkg_id = f"os_package_id_{os_pkg_id_counter}"
        os_pkg_id_counter += 1
        os_packages[pkg_id] = create_package_entry(pkg_data)

    catalog["Catalog"]["FunctionalPackages"] = functional_packages
    catalog["Catalog"]["OSPackages"] = os_packages
    catalog["Catalog"]["InfrastructurePackages"] = infra_packages

    # Add BaseOS section
    catalog["Catalog"]["BaseOS"] = [{
        "Name": "RHEL",
        "Version": "10.0",
        "osPackages": sorted(os_packages.keys())
    }]

    # Add Infrastructure section
    if infra_packages:
        catalog["Catalog"]["Infrastructure"] = [{
            "Name": "csi",
            "InfrastructurePackages": sorted(infra_packages.keys())
        }]

    # Build Functional Layers based on PXE mapping
    catalog["Catalog"]["FunctionalLayer"] = build_functional_layers(
        functional_packages, pxe_groups, role_package_map
    )

    return catalog

def build_functional_layers(functional_packages, pxe_groups, role_package_map):
    """Build FunctionalLayer based on PXE functional groups and package mappings."""
    functional_layers = []

    # Map PXE functional groups to package roles
    for pxe_group in pxe_groups:
        # Extract role name from PXE group
        # (e.g., 'slurm_control_node_x86_64' -> 'slurm_control_node')
        # Remove architecture suffix
        role_name = pxe_group.replace('_x86_64', '').replace('_aarch64', '')

        # Find packages for this role
        package_ids = []
        if role_name in role_package_map:
            package_ids = role_package_map[role_name]

        # Filter package IDs by architecture encoded in PXE group name.
        pxe_arch = _extract_arch_from_pxe_group(pxe_group)
        if pxe_arch:
            package_ids = [
                pkg_id
                for pkg_id in package_ids
                if pkg_id in functional_packages
                and pxe_arch in functional_packages[pkg_id].get('Architecture', [])
            ]

        functional_layers.append({
            "Name": pxe_group,
            "FunctionalPackages": package_ids
        })

    return functional_layers

def map_packages_to_roles(packages, config_dir, allowed_bundles, bundle_roles):
    """Map packages to their roles based on which config section they appear in."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
    role_package_map = defaultdict(list)
    package_id_map = {}

    pkg_id_counter = 1

    # First pass: assign package IDs (only for functional bundles)
    for key, pkg_data in packages.items():
        pkg_name = pkg_data['name']
        bundles = set(pkg_data.get('bundles') or [])
        is_functional = bool(bundles & _FUNCTIONAL_BUNDLES)
        is_infra = bool(bundles & _INFRA_BUNDLES) or _is_infra_package_name(pkg_name)

        if is_functional and not is_infra:
            pkg_id = f"package_id_{pkg_id_counter}"
            pkg_id_counter += 1
            package_id_map[key] = pkg_id

    # Second pass: map packages to roles by scanning config files
    for root, _dirs, files in os.walk(config_dir):
        for file in files:
            if not file.endswith('.json'):
                continue

            bundle_name = file.replace('.json', '')
            if bundle_name not in allowed_bundles:
                continue

            # Only functional bundles should contribute to role-package mappings.
            if bundle_name not in _FUNCTIONAL_BUNDLES:
                continue

            filepath = os.path.join(root, file)
            data = load_json(filepath)

            # Process each section in the JSON
            for section_name, section_data in data.items():
                if not isinstance(section_data, dict) or 'cluster' not in section_data:
                    continue

                for pkg in section_data['cluster']:
                    pkg_name = pkg['package']
                    pkg_type = pkg['type']
                    key = f"{pkg_name}_{pkg_type}"

                    if key in package_id_map:
                        pkg_id = package_id_map[key]
                        # Map to role(s)
                        # 1) If the section name is a role (e.g., slurm_node), map directly.
                        # 2) If the section name is the bundle itself (bundle_name) or "cluster",
                        #    treat these as common packages and map to all roles declared for
                        #    that bundle in software_config.json.
                        if section_name not in ['cluster', bundle_name]:
                            role_package_map[section_name].append(pkg_id)
                        else:
                            for role in bundle_roles.get(bundle_name, []):
                                role_package_map[role].append(pkg_id)

    # Remove duplicates
    for role in role_package_map:
        role_package_map[role] = sorted(list(set(role_package_map[role])))

    return role_package_map, package_id_map

def create_package_entry(pkg_data):
    """Create a package entry for FunctionalPackages or OSPackages."""
    entry = {
        "Name": pkg_data['name'],
        "SupportedOS": [{"Name": "RHEL", "Version": "10.0"}],
        "Architecture": pkg_data['architectures'],
        "Type": pkg_data['type']
    }

    if pkg_data['tag']:
        entry["Tag"] = pkg_data['tag']
        entry["Version"] = pkg_data['tag']

    if pkg_data['sources']:
        entry["Sources"] = pkg_data['sources']

    return entry

def create_infra_package_entry(pkg_data):
    """Create an infrastructure package entry."""
    entry = {
        "Name": pkg_data['name'],
        "Type": pkg_data['type'],
        "Version": pkg_data.get('version', '1.0.0'),
        "SupportedFunctions": [{"Name": "csi"}]
    }

    if pkg_data['architectures']:
        entry["Architecture"] = pkg_data['architectures']

    if pkg_data['tag']:
        entry["Tag"] = pkg_data['tag']

    return entry

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate catalog_rhel.json from input/config')
    parser.add_argument(
        '--base-dir',
        default='/opt/omnia/input/project_default/',
        help='Project base directory containing input/ and build_stream/ folders',
    )
    args = parser.parse_args()

    base_dir = args.base_dir
    if not os.path.exists(base_dir):
        repo_root = Path(__file__).resolve().parents[1]
        base_dir = str(repo_root)

    # Support base_dir as either repo root (contains input/ and build_stream/)
    # or the input directory itself.
    base_dir_path = Path(base_dir).resolve()
    is_input_dir = (base_dir_path / 'software_config.json').exists() and (base_dir_path / 'config').exists()

    if is_input_dir:
        input_dir = str(base_dir_path)
        repo_root = Path(__file__).resolve().parents[1]
    else:
        input_dir = str(base_dir_path / 'input')
        repo_root = base_dir_path

    input_config_dir = os.path.join(input_dir, 'config')
    software_config_file = os.path.join(input_dir, 'software_config.json')
    pxe_mapping_csv = os.path.join(input_dir, 'pxe_mapping_file.csv')
    output_file = os.path.join(
        str(repo_root),
        'build_stream',
        'core',
        'catalog',
        'test_fixtures',
        'catalog_rhel.json',
    )

    print("Generating catalog from input/config...")
    print(f"Using software config: {software_config_file}")
    print(f"Using PXE mapping: {pxe_mapping_csv}")
    generated_catalog = generate_catalog(input_config_dir, software_config_file, pxe_mapping_csv)

    print(f"\nWriting to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as out_file:
        json.dump(generated_catalog, out_file, indent=2)

    print("Done!")
    print("\nGenerated catalog with:")
    print(f"  - {len(generated_catalog['Catalog']['FunctionalPackages'])} functional packages")
    print(f"  - {len(generated_catalog['Catalog']['OSPackages'])} OS packages")
    print(
        f"  - {len(generated_catalog['Catalog']['InfrastructurePackages'])} infrastructure packages"
    )
    print(f"  - {len(generated_catalog['Catalog']['FunctionalLayer'])} functional layers")
