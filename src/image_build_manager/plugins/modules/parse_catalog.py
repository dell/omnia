#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Parse catalog JSON and resolve RPM packages by architecture."""

import json

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: parse_catalog
short_description: Parse catalog JSON and resolve packages by architecture
version_added: "3.0.0"
description:
  - Reads a catalog JSON file produced by repo_manager.
  - Resolves functional layers matching the target architecture.
  - Walks the three-level hierarchy
    C(functionallayer) -> C(groups) -> C(packages).
  - Filters packages by C(packagetype) and C(sources[].architecture).
  - Separates base OS packages from compute group packages.
  - Extracts OS type and version from base_os groups for multi-version builds.
  - Layer classification uses the B(layer name), not component membership.
    Layers whose name starts with the baseos prefix (e.g. C(baseos_rhel_10_0_x86_64))
    are base OS layers; all others are compute layers.
  - Compute layers that reference base OS components only extract the
    C(os_version) from them; base OS packages are skipped to avoid
    duplication with the base image.
options:
  catalog_file:
    description: Absolute path to the catalog JSON file.
    required: true
    type: str
  build_arch:
    description:
      - Target architecture to filter packages for.
      - Functional layers whose name ends with C(_{build_arch}) are selected.
    required: true
    type: str
    choices:
      - x86_64
      - aarch64
  package_type:
    description: Package type filter applied to catalog packages.
    required: false
    type: str
    default: rpm
  baseos_prefix:
    description:
      - Component name prefix used to identify base OS groups within a layer.
      - The layer-level prefix is derived by stripping C(_group) from this value
        (e.g. C(baseos_group) -> C(baseos)). Layers whose name starts with
        the derived prefix are classified as base OS layers.
      - Within compute layers, components matching this prefix are skipped
        (their packages are already in the base image).
    required: false
    type: str
    default: baseos_group
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Resolve RPM packages from catalog for x86_64
  omnia.image_build.parse_catalog:
    catalog_file: /opt/omnia/catalog/catalog_rhel.json
    build_arch: x86_64
  register: catalog_result

- name: Display resolved packages
  ansible.builtin.debug:
    msg: >-
      {{ catalog_result.layer_count }} layers,
      {{ catalog_result.base_image_packages | length }} base pkgs,
      {{ catalog_result.compute_images_dict | length }} compute groups,
      os_type={{ catalog_result.cluster_os_type }},
      os_versions={{ catalog_result.cluster_os_versions }}

- name: Resolve aarch64 packages with custom baseos prefix
  omnia.image_build.parse_catalog:
    catalog_file: /opt/omnia/catalog/catalog_rhel.json
    build_arch: aarch64
    baseos_prefix: baseos_group
  register: arm_result
'''

RETURN = r'''
catalog_identifier:
  description: Catalog identifier string from catalog JSON.
  returned: always
  type: str
cluster_os_version:
  description:
    - Primary OS version extracted from the first base_os group.
    - Derived from C(os_version) field in groups with C(type=base_os).
    - Empty string if no base_os group declares an os_version.
  returned: always
  type: str
cluster_os_type:
  description:
    - OS type extracted from the first base_os group's C(os) field.
    - E.g. C(rhel), C(ubuntu). Empty string if not declared.
  returned: always
  type: str
cluster_os_versions:
  description:
    - List of all unique OS versions found across base_os groups.
    - Supports multi-version image builds.
  returned: always
  type: list
  elements: str
base_image_packages:
  description:
    - Deduplicated list of RPM package names from base OS layers.
    - These are installed in every image.
  returned: always
  type: list
  elements: str
compute_images_dict:
  description:
    - Dict keyed by functional layer name.
    - Each value contains C(functional_group) (str) and C(packages) (list).
    - Only non-baseos layers are included.
  returned: always
  type: dict
layer_count:
  description: Number of functional layers matching build_arch.
  returned: always
  type: int
'''


def _load_catalog(catalog_file: str) -> dict:
    """Load and validate catalog JSON file.

    Args:
        catalog_file: Path to catalog JSON.

    Returns:
        Parsed catalog dict (the 'catalog' key from the JSON root).

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If JSON is malformed or missing 'catalog' key.
    """
    with open(catalog_file, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if "catalog" not in raw:
        raise ValueError(
            f"Catalog JSON missing 'catalog' root key in {catalog_file}"
        )
    return raw["catalog"]


def _filter_layers_by_arch(
    layers: list, build_arch: str
) -> list:
    """Return layers whose name ends with _{build_arch}.

    Args:
        layers: List of functional layer dicts from catalog.
        build_arch: Target architecture suffix.

    Returns:
        Filtered list of layer dicts.
    """
    suffix = f"_{build_arch}"
    return [
        layer for layer in layers
        if layer.get("name", "").endswith(suffix)
    ]


def _is_baseos_component(
    comp_name: str, group: dict, baseos_prefix: str
) -> bool:
    """Check if a component belongs to the base OS layer.

    Args:
        comp_name: Component name from the layer.
        group: Group definition from catalog.
        baseos_prefix: Prefix for base OS group detection.

    Returns:
        True if this is a base OS component.
    """
    return (
        group.get("type") == "base_os"
        or comp_name.startswith(baseos_prefix)
    )


def _resolve_layer_packages(
    layer: dict,
    groups: dict,
    packages: dict,
    build_arch: str,
    package_type: str,
    baseos_prefix: str,
) -> dict:
    """Resolve RPM packages for a single functional layer.

    Layer classification uses the **layer name**: layers whose name starts
    with the baseos_prefix are base OS layers.  All others are compute
    layers.  For compute layers only non-baseos component packages are
    collected (the base image already contains baseos packages).

    Args:
        layer: Functional layer dict with 'name' and 'components'.
        groups: Catalog groups dict.
        packages: Catalog packages dict.
        build_arch: Target architecture for source filtering.
        package_type: Package type to include (e.g., 'rpm').
        baseos_prefix: Prefix to identify base OS groups.

    Returns:
        Dict with keys: functional_group, packages, is_baseos, os_versions.
    """
    layer_name = layer.get("name", "")
    # Derive layer-level prefix from component-level baseos_prefix.
    # "baseos_group" → "baseos" — matches layer names like
    # "baseos_rhel_10_0_x86_64" while baseos_prefix matches
    # component names like "baseos_group_10.0".
    _layer_prefix = baseos_prefix.split("_group")[0]
    is_baseos_layer = layer_name.startswith(_layer_prefix)

    layer_pkgs: list[str] = []
    os_versions: list[str] = []
    os_type: str = ""

    for comp_name in layer.get("components", []):
        group = groups.get(comp_name, {})
        comp_is_baseos = _is_baseos_component(
            comp_name, group, baseos_prefix
        )

        if comp_is_baseos:
            os_ver = group.get("os_version", "")
            if os_ver and os_ver not in os_versions:
                os_versions.append(os_ver)
            os_type = group.get("os", "")
            if not is_baseos_layer:
                continue

        for pkg_key in group.get("components", []):
            pkg = packages.get(pkg_key, {})
            if pkg.get("packagetype", "") != package_type:
                continue

            arch_match = any(
                src.get("architecture") == build_arch
                for src in pkg.get("sources", [])
            )
            if arch_match and pkg.get("name"):
                layer_pkgs.append(pkg["name"])

    return {
        "functional_group": layer_name,
        "packages": layer_pkgs,
        "is_baseos": is_baseos_layer,
        "os_versions": os_versions,
        "os_type": os_type,
    }



def _extract_baseos_packages(
    groups: dict,
    packages: dict,
    build_arch: str,
    package_type: str,
) -> tuple[list[str], list[str], str]:
    """Extract base OS packages by scanning groups with type=base_os directly.

    This handles catalogs that have no standalone baseos functional layer
    but embed baseos groups as components within compute layers.

    Args:
        groups: Catalog groups dict.
        packages: Catalog packages dict.
        build_arch: Target architecture for source filtering.
        package_type: Package type to include (e.g., 'rpm').

    Returns:
        Tuple of (base_packages, os_versions, os_type).
    """
    base_pkgs: list[str] = []
    os_versions: list[str] = []
    os_type: str = ""

    for group_name, group_data in groups.items():
        if group_data.get("type") != "base_os":
            continue

        os_ver = group_data.get("os_version", "")
        if os_ver and os_ver not in os_versions:
            os_versions.append(os_ver)
        if not os_type and group_data.get("os"):
            os_type = group_data["os"]

        for pkg_key in group_data.get("components", []):
            pkg = packages.get(pkg_key, {})
            if pkg.get("packagetype", "") != package_type:
                continue
            arch_match = any(
                src.get("architecture") == build_arch
                for src in pkg.get("sources", [])
            )
            if arch_match and pkg.get("name"):
                base_pkgs.append(pkg["name"])

    return base_pkgs, os_versions, os_type


def _deduplicate(items: list) -> list:
    """Deduplicate list while preserving order.

    Args:
        items: List of items.

    Returns:
        Deduplicated list.
    """
    seen: set = set()
    result: list = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def resolve_catalog(
    catalog_file: str,
    build_arch: str,
    package_type: str = "rpm",
    baseos_prefix: str = "baseos_group",
) -> dict:
    """Main entry point: parse catalog and resolve packages.

    Args:
        catalog_file: Path to catalog JSON file.
        build_arch: Target architecture (x86_64 or aarch64).
        package_type: Package type filter (default: rpm).
        baseos_prefix: Prefix for base OS group detection.

    Returns:
        Dict with catalog_identifier, base_image_packages,
        compute_images_dict, cluster_os_version(s), layer_count.
    """
    catalog = _load_catalog(catalog_file)
    identifier = catalog.get("identifier", "")

    arch_layers = _filter_layers_by_arch(
        catalog.get("functionallayer", []), build_arch
    )

    groups = catalog.get("groups", {})
    packages = catalog.get("packages", {})

    resolved: dict = {}
    for layer in arch_layers:
        data = _resolve_layer_packages(
            layer, groups, packages,
            build_arch, package_type, baseos_prefix,
        )
        resolved[layer["name"]] = data

    base_packages: list[str] = []
    compute_dict: dict = {}
    all_os_versions: list[str] = []
    os_type: str = ""
    for name, data in resolved.items():
        if data["is_baseos"]:
            base_packages.extend(data["packages"])
        else:
            layer_ver = data["os_versions"][0] if data.get("os_versions") else ""
            compute_dict[name] = {
                "functional_group": name,
                "packages": data["packages"],
                "os_version": layer_ver,
            }
        for ver in data.get("os_versions", []):
            if ver and ver not in all_os_versions:
                all_os_versions.append(ver)
        if not os_type and data.get("os_type"):
            os_type = data["os_type"]

    # Fallback: if no baseos functional layer produced base packages,
    # scan groups with type=base_os directly.  This handles catalogs
    # where baseos groups are only referenced as components within
    # compute layers (no standalone baseos_*_{arch} layer exists).
    if not base_packages:
        direct_pkgs, direct_vers, direct_os = _extract_baseos_packages(
            groups, packages, build_arch, package_type,
        )
        base_packages = direct_pkgs
        for ver in direct_vers:
            if ver and ver not in all_os_versions:
                all_os_versions.append(ver)
        if not os_type and direct_os:
            os_type = direct_os

    base_packages = _deduplicate(base_packages)

    return {
        "catalog_identifier": identifier,
        "cluster_os_type": os_type,
        "cluster_os_version": all_os_versions[0] if all_os_versions else "",
        "cluster_os_versions": all_os_versions,
        "base_image_packages": base_packages,
        "compute_images_dict": compute_dict,
        "layer_count": len(arch_layers),
    }


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            catalog_file=dict(type="str", required=True),
            build_arch=dict(
                type="str", required=True,
                choices=["x86_64", "aarch64"],
            ),
            package_type=dict(type="str", default="rpm"),
            baseos_prefix=dict(type="str", default="baseos_group"),
        ),
        supports_check_mode=True,
    )

    try:
        result = resolve_catalog(
            catalog_file=module.params["catalog_file"],
            build_arch=module.params["build_arch"],
            package_type=module.params["package_type"],
            baseos_prefix=module.params["baseos_prefix"],
        )
        module.exit_json(changed=False, **result)
    except FileNotFoundError as exc:
        module.fail_json(
            msg=f"Catalog file not found: {exc}"
        )
    except (json.JSONDecodeError, ValueError) as exc:
        module.fail_json(
            msg=f"Failed to parse catalog JSON: {exc}"
        )
    except Exception as exc:  # pylint: disable=broad-except
        module.fail_json(
            msg=f"Catalog resolution failed: {exc}"
        )


if __name__ == "__main__":
    main()
