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
Catalog Transformer - Transform Schema 1.0 catalogs to Schema 2.0.

This module provides functions to:
- Detect catalog schema version
- Transform 1.0 format (PascalCase "Catalog" root key) to 2.0 format (lowercase "catalog")
- Slugify package keys according to transformation rules
- Extract registry from image names
- Generate unique keys for packages
- Transform source arrays
- Write keymap sidecar files
"""

import re
import json
from datetime import datetime
from typing import Tuple, List, Set, Optional


def detect_schema_version(catalog_data: dict) -> str:
    """
    Detect the schema version of a catalog.

    Args:
        catalog_data: The catalog dictionary

    Returns:
        '1.0' if root key is 'Catalog' (PascalCase)
        '2.0' if root key is 'catalog' (lowercase)

    Raises:
        ValueError: If neither key is found
    """
    if 'Catalog' in catalog_data:
        return '1.0'
    if 'catalog' in catalog_data:
        return '2.0'
    raise ValueError("Unrecognized catalog format - expected root key 'Catalog' or 'catalog'")


def slugify(text: str) -> str:
    """
    Core slugification function.

    Rules:
    1. Lowercase the entire string
    2. Replace all `-`, `.`, `/`, `@`, `:` with `_`
    3. Collapse consecutive `_` into a single `_`
    4. Strip leading and trailing `_`

    Special cases:
    - 'gcc-c++' -> 'gcc_cpp'
    - Handle + by replacing with 'p' or removing

    Args:
        text: String to slugify

    Returns:
        Slugified string
    """
    if not text:
        return text

    # Lowercase
    result = text.lower()

    # Special handling for C++
    result = result.replace('c++', 'cpp')
    result = result.replace('++', 'pp')
    result = result.replace('+', 'p')

    # Replace special characters with underscore
    result = re.sub(r'[-./\@:]', '_', result)

    # Collapse consecutive underscores
    result = re.sub(r'_+', '_', result)

    # Strip leading/trailing underscores
    result = result.strip('_')

    return result


def extract_registry(image_name: str) -> str:
    """
    Extract registry domain from image path.

    Examples:
        "docker.io/calico/cni" -> "docker.io"
        "registry.k8s.io/etcd" -> "registry.k8s.io"
        "nvcr.io/nvidia/hpc-benchmarks" -> "nvcr.io"
        "quay.io/strimzi/kafka" -> "quay.io"
        "simple-image" -> "docker.io" (default)

    Args:
        image_name: Full image name/path

    Returns:
        Registry domain or "docker.io" as default
    """
    parts = image_name.split('/')

    # Check if first part looks like a registry (contains . or :)
    if len(parts) >= 2 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0]

    # Default to Docker Hub
    return "docker.io"


def generate_unique_key(old_key: str, pkg_type: str, tag: Optional[str],
                        existing_keys: Set[str]) -> str:
    """
    Generate a unique slugified key for a package.

    Rules by package type:
    - rpm, rpm_repo, tarball, pip_module, git, manifest: slugify(old_key)
    - image: slugify(last_path_segment + "_" + tag)

    If collision occurs, append _1, _2, etc.

    Args:
        old_key: Original package key from 1.0 catalog
        pkg_type: Package type (rpm, image, tarball, etc.)
        tag: Image tag (only for image types)
        existing_keys: Set of already generated keys for collision detection

    Returns:
        Unique slugified key
    """
    if pkg_type == "image":
        # Extract last segment from image path
        last_segment = old_key.split('/')[-1]
        tag_slug = slugify(tag) if tag else "notag"
        slug_base = slugify(last_segment) + "_" + tag_slug
    else:
        slug_base = slugify(old_key)

    # Handle collisions
    candidate = slug_base
    counter = 1

    while candidate in existing_keys:
        candidate = f"{slug_base}_{counter}"
        counter += 1

    existing_keys.add(candidate)
    return candidate


def transform_sources(old_pkg: dict, pkg_type: str,
                      warnings: List[str]) -> List[dict]:  # pylint: disable=too-many-branches,too-many-statements
    """
    Transform 1.0 Sources array to 2.0 sources array.

    Args:
        old_pkg: Original package dictionary
        pkg_type: Package type
        warnings: List to append warnings to

    Returns:
        List of transformed source dictionaries
    """
    old_key = old_pkg.get('Name', 'unknown')

    # Extract OS info from SupportedOS
    supported_os = old_pkg.get('SupportedOS', [])
    if supported_os:
        os_name = supported_os[0]['Name'].lower()
        os_versions = list(set(entry['Version'] for entry in supported_os))
    else:
        os_name = "rhel"
        os_versions = ["10.0"]
        warnings.append(f"Package '{old_key}' has no SupportedOS - using defaults")

    old_sources = old_pkg.get('Sources', [])
    new_sources = []

    if pkg_type in ["rpm", "rpm_repo"]:
        if old_sources:
            for src in old_sources:
                new_sources.append({
                    "architecture": src['Architecture'].lower(),
                    "reponame": src['RepoName'],
                    "name": os_name,
                    "version": os_versions
                })
        else:
            # Synthesize from Architecture array
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })
                warnings.append(f"No Sources[] for {pkg_type} package "
                                f"'{old_key}' - synthesized")

    elif pkg_type == "tarball":
        if old_sources:
            for src in old_sources:
                entry = {
                    "architecture": src['Architecture'].lower(),
                    "name": os_name,
                    "version": os_versions,
                    "url": src['Uri']
                }
                new_sources.append(entry)
        else:
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })
                warnings.append(f"No Sources[] for tarball '{old_key}' - "
                                "synthesized without URL")

    elif pkg_type == "git":
        if old_sources:
            for src in old_sources:
                new_sources.append({
                    "architecture": src['Architecture'].lower(),
                    "url": src['Uri'],
                    "name": os_name,
                    "version": os_versions
                })
        else:
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })
                warnings.append(f"No Sources[] for git package '{old_key}' - synthesized")

    elif pkg_type == "manifest":
        if old_sources:
            for src in old_sources:
                entry = {
                    "architecture": src['Architecture'].lower(),
                    "name": os_name,
                    "version": os_versions
                }
                if 'Uri' in src:
                    entry['url'] = src['Uri']
                new_sources.append(entry)
        else:
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })
                warnings.append(f"No Sources[] for manifest '{old_key}' - synthesized")

    elif pkg_type == "image":
        registry = extract_registry(old_pkg['Name'])

        if old_sources:
            for src in old_sources:
                entry = {
                    "architecture": src['Architecture'].lower(),
                    "registry": src.get('Registry', registry)
                }
                if supported_os:
                    entry['name'] = os_name
                    entry['version'] = os_versions
                new_sources.append(entry)
        else:
            # Many image packages have NO Sources[] at all
            for arch in old_pkg.get('Architecture', ['x86_64']):
                entry = {
                    "architecture": arch.lower(),
                    "registry": registry
                }
                if supported_os:
                    entry['name'] = os_name
                    entry['version'] = os_versions
                new_sources.append(entry)
                warnings.append(f"No Sources[] for image '{old_key}' - "
                                "synthesized from Architecture + SupportedOS")

    elif pkg_type == "pip_module":
        if old_sources:
            for src in old_sources:
                new_sources.append({
                    "architecture": src['Architecture'].lower(),
                    "name": os_name,
                    "version": os_versions
                })
        else:
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })

    else:
        warnings.append(f"Unknown package type '{pkg_type}' for '{old_key}' - "
                        "treated as tarball")
        # Handle same as tarball
        if old_sources:
            for src in old_sources:
                entry = {
                    "architecture": src['Architecture'].lower(),
                    "name": os_name,
                    "version": os_versions
                }
                if 'Uri' in src:
                    entry['url'] = src['Uri']
                new_sources.append(entry)
        else:
            for arch in old_pkg.get('Architecture', ['x86_64']):
                new_sources.append({
                    "architecture": arch.lower(),
                    "name": os_name,
                    "version": os_versions
                })

    return new_sources


def deduplicate_preserve_order(items: List[str]) -> List[str]:
    """
    Remove duplicates from list while preserving first-occurrence order.

    Args:
        items: List of strings

    Returns:
        Deduplicated list
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def transform(old_catalog: dict) -> Tuple[dict, dict, List[str]]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """
    Transform a 1.0 catalog to 2.0 format.

    Args:
        old_catalog: The "Catalog" section from 1.0 format

    Returns:
        Tuple of (new_catalog_dict, key_map_dict, warnings_list)
    """
    warnings = []

    # Extract catalog metadata
    catalog_name = old_catalog.get('Name', '')
    catalog_version = old_catalog.get('Version', '1.0')
    catalog_identifier = old_catalog.get('Identifier', slugify(catalog_name))

    base_os_list = old_catalog.get('BaseOS', [])
    layers = old_catalog.get('FunctionalLayer', [])
    infrastructure = old_catalog.get('Infrastructure', [])

    # Merge all package dictionaries from different sections
    # In 1.0 catalogs, packages can be in Packages, FunctionalPackages, OSPackages,
    # DriverPackages, or InfrastructurePackages
    old_packages = {}
    pkg_keys = ['Packages', 'FunctionalPackages', 'OSPackages',
                'DriverPackages', 'InfrastructurePackages']
    for pkg_key in pkg_keys:
        pkg_dict = old_catalog.get(pkg_key, {})
        if pkg_dict:
            old_packages.update(pkg_dict)

    # Phase 1: Transform all packages
    new_packages = {}
    key_map = {}
    all_new_keys = set()
    type_counters = {}

    for old_key, old_pkg in old_packages.items():
        pkg_type = old_pkg.get('Type', 'rpm').lower()
        tag = old_pkg.get('Tag', None)

        # Generate new key
        new_key = generate_unique_key(old_key, pkg_type, tag, all_new_keys)
        key_map[old_key] = new_key

        # Build new package dict
        new_pkg = {
            "name": old_pkg.get('Name', old_key),
            "packagetype": pkg_type
        }

        # Preserve version if present and non-empty
        if 'Version' in old_pkg and old_pkg['Version']:
            new_pkg['version'] = old_pkg['Version']

        # Preserve tag for images
        if tag:
            new_pkg['tag'] = tag

        # Preserve supported_functions (git/CSI packages)
        if 'SupportedFunctions' in old_pkg and old_pkg['SupportedFunctions']:
            new_pkg['supported_functions'] = [
                sf['Name'] for sf in old_pkg['SupportedFunctions']
            ]

        # Transform sources
        new_pkg['sources'] = transform_sources(old_pkg, pkg_type, warnings)

        new_packages[new_key] = new_pkg

        # Track type counters
        type_counters[pkg_type] = type_counters.get(pkg_type, 0) + 1

    # Phase 2: Build BaseOS groups
    new_groups = {}
    baseos_group_keys = []

    for base_os_entry in base_os_list:
        os_name = base_os_entry['Name'].lower()
        os_version = base_os_entry['Version']
        os_packages = base_os_entry.get('osPackages', [])

        group_key = f"baseos_{os_name}_{os_version}"

        # Slugify each BaseOS package name to match its new key in new_packages
        components = []
        for old_pkg_name in os_packages:
            if old_pkg_name in key_map:
                components.append(key_map[old_pkg_name])
            else:
                # Package exists in BaseOS list but not in Packages{} - warn
                slug = slugify(old_pkg_name)
                components.append(slug)
                warnings.append(f"BaseOS package '{old_pkg_name}' not found in "
                                f"Packages - added as '{slug}'")

        desc = (f"Base OS packages for {base_os_entry['Name']} {os_version} - "
                "auto-generated from BaseOS")
        new_groups[group_key] = {
            "name": group_key,
            "type": "base_os",
            "os": os_name,
            "os_version": os_version,
            "description": desc,
            "components": deduplicate_preserve_order(components)
        }

        baseos_group_keys.append(group_key)

    # Phase 3: Build Functional Layer groups
    new_functionallayers = []

    for layer in layers:
        layer_name = layer['Name']
        old_pkg_refs = layer.get('FunctionalPackages', [])

        # Create a group for this layer
        group_key = slugify(layer_name) + "_group"

        # Remap old package names -> new keys
        group_components = []
        for old_pkg_name in old_pkg_refs:
            if old_pkg_name in key_map:
                group_components.append(key_map[old_pkg_name])
            else:
                slug = slugify(old_pkg_name)
                group_components.append(slug)
                warnings.append(f"FunctionalLayer '{layer_name}' references unknown "
                                f"package '{old_pkg_name}' - mapped to '{slug}'")

        new_groups[group_key] = {
            "name": group_key,
            "type": "group",
            "description": f"Auto-generated from FunctionalLayer: {layer_name}",
            "components": deduplicate_preserve_order(group_components)
        }

        # Create functionallayer entry
        # Each functionallayer includes ALL baseos groups FIRST, then its own group
        fl_components = baseos_group_keys.copy()
        fl_components.append(group_key)

        new_functionallayers.append({
            "name": layer_name,
            "components": fl_components
        })

    # Phase 4: Build Infrastructure groups (groups only - NO functionallayer entry)
    for infra in infrastructure:
        infra_name = infra['Name']
        old_pkg_refs = infra.get('InfrastructurePackages', [])

        group_key = slugify(infra_name) + "_group"

        group_components = []
        for old_pkg_name in old_pkg_refs:
            if old_pkg_name in key_map:
                group_components.append(key_map[old_pkg_name])
            else:
                slug = slugify(old_pkg_name)
                group_components.append(slug)
                warnings.append(f"Infrastructure '{infra_name}' references unknown "
                                f"package '{old_pkg_name}' - mapped to '{slug}'")

        new_groups[group_key] = {
            "name": group_key,
            "type": "group",
            "description": f"Auto-generated from Infrastructure: {infra_name}",
            "components": deduplicate_preserve_order(group_components)
        }

    # Phase 5: Assemble 2.0 catalog
    new_catalog = {
        "catalog": {
            "name": catalog_name,
            "version": catalog_version,
            "identifier": catalog_identifier,
            "description": "Transformed from Schema 1.0 by catalog_transform",
            "functionallayer": new_functionallayers,
            "groups": new_groups,
            "packages": new_packages
        }
    }

    return new_catalog, key_map, warnings


def write_keymap(key_map: dict, source_path: str, target_path: str,
                 output_path: str, total_groups: int,
                 total_layers: int) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    Write the sidecar keymap JSON file.

    Args:
        key_map: Dictionary mapping old keys to new keys
        source_path: Input file path
        target_path: Output file path
        output_path: Keymap file path
        total_groups: Total groups created
        total_layers: Total functional layers
    """
    keymap_data = {
        "_meta": {
            "source": source_path,
            "target": target_path,
            "transformed_at": datetime.utcnow().isoformat() + "Z",
            "total_package_mappings": len(key_map),
            "total_groups_created": total_groups,
            "total_layers": total_layers
        },
        "packages": key_map
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(keymap_data, f, indent=2, ensure_ascii=False)
