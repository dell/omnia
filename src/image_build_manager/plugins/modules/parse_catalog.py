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
  - Extracts C(service_k8s_version) from kubeadm RPM or kube_apiserver
    image tag.
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
      - Component name prefix used to identify base OS groups.
      - Groups whose name starts with this prefix contribute to
        C(base_image_packages) instead of C(compute_images_dict).
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
      k8s={{ catalog_result.service_k8s_version }}

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
service_k8s_version:
  description:
    - Kubernetes version extracted from kubeadm RPM package name
      or kube_apiserver image tag.
    - Empty string if no Kubernetes packages found.
  returned: always
  type: str
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


def _resolve_layer_packages(
    layer: dict,
    groups: dict,
    packages: dict,
    build_arch: str,
    package_type: str,
    baseos_prefix: str,
) -> dict:
    """Resolve RPM packages for a single functional layer.

    Args:
        layer: Functional layer dict with 'name' and 'components'.
        groups: Catalog groups dict.
        packages: Catalog packages dict.
        build_arch: Target architecture for source filtering.
        package_type: Package type to include (e.g., 'rpm').
        baseos_prefix: Prefix to identify base OS groups.

    Returns:
        Dict with keys: functional_group, packages, is_baseos.
    """
    layer_pkgs: list[str] = []
    is_baseos = False

    for comp_name in layer.get("components", []):
        if comp_name.startswith(baseos_prefix):
            is_baseos = True

        group = groups.get(comp_name, {})
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
        "functional_group": layer["name"],
        "packages": layer_pkgs,
        "is_baseos": is_baseos,
    }


def _extract_k8s_version(packages: dict) -> str:
    """Extract Kubernetes version from catalog packages.

    Tries kubeadm RPM first (name format: kubeadm-X.Y.Z),
    then falls back to kube_apiserver image tag.

    Args:
        packages: Catalog packages dict.

    Returns:
        Version string or empty string.
    """
    for key, pkg in packages.items():
        if (
            key.startswith("kubeadm_")
            and pkg.get("packagetype") == "rpm"
        ):
            parts = pkg.get("name", "").split("-")
            if len(parts) > 1:
                return parts[-1]

    for key, pkg in packages.items():
        if (
            key == "kube_apiserver"
            and pkg.get("packagetype") == "image"
        ):
            return pkg.get("tag", "")

    return ""


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
        compute_images_dict, service_k8s_version, layer_count.
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
    for name, data in resolved.items():
        if data["is_baseos"]:
            base_packages.extend(data["packages"])
        else:
            compute_dict[name] = {
                "functional_group": name,
                "packages": data["packages"],
            }

    base_packages = _deduplicate(base_packages)
    k8s_version = _extract_k8s_version(packages)

    return {
        "catalog_identifier": identifier,
        "base_image_packages": base_packages,
        "compute_images_dict": compute_dict,
        "service_k8s_version": k8s_version,
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
