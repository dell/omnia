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
    "additional_packages",
}

_MISC_BUNDLE = "additional_packages"


_INFRA_BUNDLES = {
    "csi_driver_powerscale",
}

# All known bundle names that may carry a version suffix in the filename.
_KNOWN_BUNDLES = _FUNCTIONAL_BUNDLES | _INFRA_BUNDLES | {
    "default_packages", "admin_debug_packages", "openldap",
    "openmpi", "ucx", "ldms", "nfs",
}


def _extract_bundle_name(filename_stem: str) -> str:
    """Strip version suffix from a config filename stem.

    Examples:
        service_k8s_v1.35.1  -> service_k8s
        service_k8s_1.35.1   -> service_k8s
        service_k8s-1.35.1   -> service_k8s
        slurm_custom         -> slurm_custom
    """
    # Try matching a known bundle prefix
    for name in sorted(_KNOWN_BUNDLES, key=len, reverse=True):
        if filename_stem == name:
            return name
        # version suffixed with _v, _, or -
        if filename_stem.startswith(name) and len(filename_stem) > len(name):
            sep = filename_stem[len(name)]
            if sep in ('_', '-'):
                remainder = filename_stem[len(name) + 1:]
                # strip optional leading 'v'
                if remainder.startswith('v'):
                    remainder = remainder[1:]
                # check looks like a version (digits and dots)
                if remainder and re.match(r'^[\d]+(\.[\d]+)*$', remainder):
                    return name
    # Fallback: try generic regex stripping
    stripped = re.sub(r'[-_]v?\d+(\.\d+)*$', '', filename_stem)
    return stripped

def load_json(filepath):
    """Load and return JSON from the given file path."""
    with open(filepath, 'r', encoding='utf-8') as json_file:
        return json.load(json_file)


# Bundle that should be included in os_* functional layers when those roles exist
# ldms packages will populate os_x86_64 and os_aarch64 functional layers
_OS_LAYER_BUNDLE = "ldms"

def load_software_config(config_path):
    """Load software_config.json.

    Returns:
      - allowed_by_arch: {arch -> set(bundle_name)}
      - bundle_roles: {bundle_name -> list(role_name)}
      - versions_by_name: {bundle_name -> version_string}
    """
    config = load_json(config_path)

    allowed_by_arch = {
        'x86_64': set(),
        'aarch64': set(),
    }

    versions_by_name = {}

    for software in config.get('softwares', []):
        name = software.get('name')
        arches = software.get('arch', []) or []
        if not name:
            continue
        for arch in arches:
            if arch in allowed_by_arch:
                allowed_by_arch[arch].add(name)
        if software.get('version'):
            versions_by_name[name] = software.get('version')

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

    return allowed_by_arch, bundle_roles, versions_by_name


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


def _append_unique_source(pkg_sources, source):
    """Append source only if an identical entry does not already exist."""
    if source not in pkg_sources:
        pkg_sources.append(source)

def _render_templated_url(template: str, bundle_name: str, versions_by_name: dict) -> str:
    """Render very simple Jinja-like templates used in config URLs.

    Supports patterns:
      - {{ <bundle>_version }}
      - {{ <bundle>_version.split('.')[:2] | join('.') }}
    """
    if not template or '{{' not in template:
        return template

    version = versions_by_name.get(bundle_name)
    if not version:
        return ''

    major_minor = '.'.join(version.split('.')[:2])

    # Replace the split/join pattern first
    pattern_mm = re.compile(r"\{\{\s*" + re.escape(bundle_name) + r"_version\.split\(\s*'\.'\s*\)\s*\[:2\]\s*\|\s*join\(\s*'\.'\s*\)\s*\}\}")
    rendered = pattern_mm.sub(major_minor, template)

    # Replace plain version token
    pattern_v = re.compile(r"\{\{\s*" + re.escape(bundle_name) + r"_version\s*\}\}")
    rendered = pattern_v.sub(version, rendered)

    # If anything templated remains, return empty to signal unresolved
    return '' if '{{' in rendered else rendered

def collect_packages_from_config(config_dir, allowed_bundles_by_arch, versions_by_name):
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

            # Extract bundle name from filename (e.g., 'service_k8s_1.35.1.json' -> 'service_k8s')
            bundle_name = _extract_bundle_name(file.replace('.json', ''))

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
                    if pkg_type in ['rpm', 'rpm_repo']:
                        repo_name = pkg.get('repo_name', '')
                        if repo_name:
                            _append_unique_source(
                                packages[key]['sources'],
                                {
                                    'Architecture': arch,
                                    'RepoName': repo_name
                                }
                            )
                    elif pkg_type in ['tarball', 'manifest', 'iso']:
                        url = pkg.get('url', '')
                        # Try to resolve templated URLs using versions from software_config
                        resolved_url = url
                        if url and '{{' in url:
                            resolved_url = _render_templated_url(url, bundle_name, versions_by_name)

                        if resolved_url:
                            _append_unique_source(
                                packages[key]['sources'],
                                {
                                    'Architecture': arch,
                                    'Uri': resolved_url
                                }
                            )
                        packages[key]['url'] = resolved_url or url
                        # Populate package version:
                        # - tarball: only for ucx/openmpi from software_config
                        # - iso: restore previous behavior to include Version from software_config when present
                        if pkg_type == 'tarball':
                            if (
                                pkg_name in ('ucx', 'openmpi')
                                and versions_by_name.get(bundle_name)
                            ):
                                packages[key]['version'] = versions_by_name[bundle_name]
                        elif pkg_type == 'iso':
                            if versions_by_name.get(bundle_name):
                                packages[key]['version'] = versions_by_name[bundle_name]
                    elif pkg_type == 'git':
                        url = pkg.get('url', '')
                        version = pkg.get('version', '')
                        # Use version-aware key for git packages to
                        # avoid collisions when the same repo is
                        # referenced with different versions/branches
                        # across bundles (e.g. helm-charts in
                        # service_k8s vs csi_driver_powerscale).
                        if version:
                            git_key = f"{pkg_name}_{pkg_type}_{version}"
                            if git_key != key:
                                # Migrate any data already stored
                                # under the short key if this is the
                                # first version we encounter.
                                if key in packages and git_key not in packages:
                                    packages[git_key] = packages.pop(key)
                                key = git_key
                                packages[key]['name'] = pkg_name
                                packages[key]['type'] = pkg_type
                                packages[key]['architectures'].add(arch)
                                packages[key]['bundles'].add(bundle_name)
                        packages[key]['url'] = url
                        packages[key]['version'] = version
                        if url:
                            _append_unique_source(
                                packages[key]['sources'],
                                {
                                    'Architecture': arch,
                                    'Uri': url
                                }
                            )
                    elif pkg_type == 'image':
                        tag = pkg.get('tag', '')
                        packages[key]['tag'] = tag
                        packages[key]['version'] = tag

    return packages

def generate_catalog(input_dir, software_config_path, pxe_mapping_file):
    """Generate complete catalog structure."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks

    # Load allowed software bundles from software_config.json
    allowed_bundles_by_arch, bundle_roles, versions_by_name = load_software_config(software_config_path)
    print("Allowed software bundles by arch: x86_64={}, aarch64={}".format(
        sorted(allowed_bundles_by_arch.get('x86_64', set())),
        sorted(allowed_bundles_by_arch.get('aarch64', set()))
    ))

    # Load PXE functional groups
    pxe_groups = load_pxe_functional_groups(pxe_mapping_file)
    print("PXE functional groups: {}".format(pxe_groups))

    packages = collect_packages_from_config(input_dir, allowed_bundles_by_arch, versions_by_name)

    # Convert sets to lists for JSON serialization
    for pkg_data in packages.values():
        pkg_data['architectures'] = sorted(list(pkg_data['architectures']))

    # Map packages to roles
    allowed_bundles = set().union(*allowed_bundles_by_arch.values())
    role_package_map, package_id_map = map_packages_to_roles(
        packages, input_dir, allowed_bundles, bundle_roles, pxe_groups
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
            "Miscellaneous": [],
            "InfrastructurePackages": {}
        }
    }

    # Categorize packages using the package_id_map
    os_packages = {}
    functional_packages = {}
    infra_packages = {}
    misc_package_ids = []

    os_pkg_id_counter = 1
    infra_pkg_id_counter = 1

    # Precompute OS-role flags
    has_os_x86_64 = 'os_x86_64' in (pxe_groups or [])
    has_os_aarch64 = 'os_aarch64' in (pxe_groups or [])
    has_os_roles = has_os_x86_64 or has_os_aarch64

    # Bundles whose packages are routed to OSPackages (BaseOS) even though
    # they are not functional or infrastructure bundles.
    _BASE_OS_BUNDLES = _KNOWN_BUNDLES - _FUNCTIONAL_BUNDLES - _INFRA_BUNDLES

    for key, pkg_data in packages.items():
        bundles = set(pkg_data.get('bundles') or [])

        # Classification uses bundle membership exclusively:
        #   Functional  = service_k8s | slurm_custom | additional_packages
        #   Infra       = csi_driver_powerscale
        #   OS (BaseOS) = everything that belongs to any non-functional,
        #                 non-infra bundle (admin_debug_packages, default_packages, ...)
        #   ldms        = both Functional (os_* layers) AND OS (adapter generates ldms.json)
        is_functional = bool(bundles & _FUNCTIONAL_BUNDLES)
        is_infra = bool(bundles & _INFRA_BUNDLES)
        is_misc = _MISC_BUNDLE in bundles
        is_os_layer_bundle = _OS_LAYER_BUNDLE in bundles
        has_base_os_bundle = bool(bundles & _BASE_OS_BUNDLES)

        # --- Infrastructure ---
        if is_infra:
            pkg_id = f"infrastructure_package_id_{infra_pkg_id_counter}"
            infra_pkg_id_counter += 1
            infra_packages[pkg_id] = create_infra_package_entry(pkg_data)
            # Infra packages are exclusive; skip other sections
            continue

        # --- Functional ---
        if is_functional and key in package_id_map:
            pkg_id = package_id_map[key]
            functional_packages[pkg_id] = create_package_entry(pkg_data)
            if is_misc:
                misc_package_ids.append(pkg_id)

        # --- ldms → Functional + OS when os_* roles exist ---
        if is_os_layer_bundle and has_os_roles and key in package_id_map:
            func_pkg_id = package_id_map[key]
            functional_packages[func_pkg_id] = create_package_entry(pkg_data)
            # Also add to OS so adapter_policy can generate ldms.json from base_os.json
            os_pkg_id = f"os_package_id_{os_pkg_id_counter}"
            os_pkg_id_counter += 1
            os_packages[os_pkg_id] = create_package_entry(pkg_data)
            continue

        # --- OS (BaseOS) ---
        # A package goes to BaseOS if:
        #   (a) it belongs to at least one non-functional, non-infra bundle, OR
        #   (b) it does not belong to any functional or infra bundle at all
        if has_base_os_bundle or (not is_functional and not is_infra):
            os_pkg_id = f"os_package_id_{os_pkg_id_counter}"
            os_pkg_id_counter += 1
            os_packages[os_pkg_id] = create_package_entry(pkg_data)

    catalog["Catalog"]["FunctionalPackages"] = functional_packages
    catalog["Catalog"]["OSPackages"] = os_packages
    catalog["Catalog"]["Miscellaneous"] = sorted(list(set(misc_package_ids)))
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
    """Build FunctionalLayer from PXE groups **and** inferred role+arch combos.

    PXE groups control os_* layers directly.  For every other role that
    has mapped packages we generate ``<role>_<arch>`` layers for each
    architecture that has at least one matching package.  This ensures
    the adapter policy can always find the functional layers it expects
    (e.g. ``slurm_node_x86_64``) even when the PXE mapping only lists
    one architecture for that role.
    """
    functional_layers = []
    generated: set = set()   # track names already emitted

    # ── 1. PXE-driven layers (os_* and any explicit PXE entries) ──
    for pxe_group in pxe_groups:
        role_name = pxe_group.replace('_x86_64', '').replace('_aarch64', '')
        pxe_arch = _extract_arch_from_pxe_group(pxe_group)

        package_ids = list(role_package_map.get(role_name, []))
        first_role = role_name + "_first"
        if first_role in role_package_map:
            package_ids = sorted(set(package_ids) | set(role_package_map[first_role]))

        if pxe_arch:
            package_ids = [
                pid for pid in package_ids
                if pid in functional_packages
                and pxe_arch in functional_packages[pid].get('Architecture', [])
            ]

        if package_ids:
            functional_layers.append({
                "Name": pxe_group,
                "FunctionalPackages": package_ids
            })
        generated.add(pxe_group)

    # ── 2. Infer missing role+arch layers from role_package_map ──
    # For each role that has packages, ensure a layer exists for every
    # architecture that has at least one package in that role.
    _ARCHES = ('x86_64', 'aarch64')
    for role_name, pkg_ids in role_package_map.items():
        if role_name == 'os':
            continue  # os layers are PXE-only
        for arch in _ARCHES:
            layer_name = f"{role_name}_{arch}"
            if layer_name in generated:
                continue

            filtered = [
                pid for pid in pkg_ids
                if pid in functional_packages
                and arch in functional_packages[pid].get('Architecture', [])
            ]
            # Also merge _first packages
            first_role = role_name + "_first"
            if first_role in role_package_map:
                for pid in role_package_map[first_role]:
                    if (
                        pid in functional_packages
                        and arch in functional_packages[pid].get('Architecture', [])
                        and pid not in filtered
                    ):
                        filtered.append(pid)
                filtered.sort()

            if filtered:
                functional_layers.append({
                    "Name": layer_name,
                    "FunctionalPackages": filtered,
                })
            generated.add(layer_name)

    return functional_layers

def map_packages_to_roles(packages, config_dir, allowed_bundles, bundle_roles, pxe_groups=None):
    """Map packages to their roles based on which config section they appear in."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
    role_package_map = defaultdict(list)
    package_id_map = {}

    pkg_id_counter = 1

    # Check if os_x86_64 or os_aarch64 exist in PXE groups
    has_os_roles = any(g in (pxe_groups or []) for g in ['os_x86_64', 'os_aarch64'])
    
    # First pass: assign package IDs (functional bundles + infra if os_* roles exist)
    for key, pkg_data in packages.items():
        pkg_name = pkg_data['name']
        bundles = set(pkg_data.get('bundles') or [])
        is_functional = bool(bundles & _FUNCTIONAL_BUNDLES)
        is_infra = bool(bundles & _INFRA_BUNDLES)

        # Include ldms packages in package_id_map when os_* roles exist
        is_os_layer_bundle = _OS_LAYER_BUNDLE in bundles
        
        if is_functional and not is_infra:
            pkg_id = f"package_id_{pkg_id_counter}"
            pkg_id_counter += 1
            package_id_map[key] = pkg_id
        elif is_os_layer_bundle and has_os_roles:
            # ldms packages should be added to functional packages for os_* layers
            pkg_id = f"package_id_{pkg_id_counter}"
            pkg_id_counter += 1
            package_id_map[key] = pkg_id

    # Second pass: map packages to roles by scanning config files
    for root, _dirs, files in os.walk(config_dir):
        for file in files:
            if not file.endswith('.json'):
                continue

            bundle_name = _extract_bundle_name(file.replace('.json', ''))
            if bundle_name not in allowed_bundles:
                continue

            # Functional bundles + ldms bundle (if os_* roles exist) contribute to role mappings
            is_infra_bundle = bundle_name in _INFRA_BUNDLES
            is_os_layer_bundle = bundle_name == _OS_LAYER_BUNDLE
            if bundle_name not in _FUNCTIONAL_BUNDLES and not (is_os_layer_bundle and has_os_roles):
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

                    # For git packages, use version-aware key (must
                    # match the key used in collect_packages_from_config)
                    if pkg_type == 'git' and pkg.get('version'):
                        git_key = f"{pkg_name}_{pkg_type}_{pkg['version']}"
                        if git_key in package_id_map:
                            key = git_key

                    if key in package_id_map:
                        pkg_id = package_id_map[key]
                        # Map to role(s)
                        # 1) If the section name is a role (e.g., slurm_node), map directly.
                        # 2) If the section name is the bundle itself (bundle_name) or "cluster",
                        #    treat these as common packages and map to all roles declared for
                        #    that bundle in software_config.json.
                        # 3) For ldms bundle when os_* roles exist, map to 'os' role
                        if section_name not in ['cluster', bundle_name]:
                            role_package_map[section_name].append(pkg_id)
                        elif is_os_layer_bundle and has_os_roles:
                            # Map ldms packages to 'os' role
                            role_package_map['os'].append(pkg_id)
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

    # For non-image packages, include a Version when known
    if pkg_data.get('version') and 'Version' not in entry and pkg_data['type'] != 'manifest':
        entry["Version"] = pkg_data['version']

    if pkg_data['sources']:
        entry["Sources"] = pkg_data['sources']

    return entry

def create_infra_package_entry(pkg_data):
    """Create an infrastructure package entry."""
    entry = {
        "Name": pkg_data['name'],
        "Type": pkg_data['type'],
        "Version": pkg_data.get('version'),
        "SupportedFunctions": [{"Name": "csi"}]
    }

    if pkg_data['architectures']:
        entry["Architecture"] = pkg_data['architectures']

    if pkg_data['tag']:
        entry["Tag"] = pkg_data['tag']

    # For git type packages, create Sources array with Uri
    if pkg_data['type'] == 'git' and pkg_data.get('url'):
        sources = []
        for arch in pkg_data['architectures']:
            sources.append({
                "Architecture": arch,
                "Uri": pkg_data['url']
            })
        entry["Sources"] = sources

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
