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

"""Catalog parser adapter.

Transforms generated feature-list JSONs into omnia configuration JSONs.
"""

import json
import os
from collections import Counter
from typing import Dict, Iterable, List, Tuple, Optional
import argparse
import logging
import sys
from jsonschema import ValidationError

from .parser import ParseCatalog
from .models import Catalog
from .generator import (
    FeatureList,
    Feature,
    Package,
    generate_functional_layer_json,
    generate_infrastructure_json,
    generate_base_os_json,
    generate_miscellaneous_json,
    _filter_featurelist_for_arch,
    _discover_arch_os_version_from_catalog,
    _package_common_dict,
    _validate_catalog_and_schema_paths,
)
from .utils import _configure_logging

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_SCHEMA_PATH = os.path.join(_BASE_DIR, "resources", "CatalogSchema.json")

ERROR_CODE_INPUT_NOT_FOUND = 2
ERROR_CODE_PROCESSING_ERROR = 3


def _snake_case(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _package_key(pkg: Package) -> Tuple[str, str, str]:
    """Key used to detect common packages across features.

    Uses (package, type, repo_name) to distinguish identical names in different repos/types.
    """
    return (pkg.package, pkg.type, pkg.repo_name)


def _package_to_dict(pkg: Package) -> Dict[str, str]:
    # Adapter-specific wrapper over the shared helper; note that the
    # adapter JSONs intentionally do not include architecture.
    return _package_common_dict(pkg)  # type: ignore[return-value]


# -------------------------- Base OS / default packages --------------------------


def build_default_packages_config(base_os: FeatureList) -> Dict:
    """Build default_packages.json-style structure from Base OS FeatureList.

    Expected FeatureList has a feature named "Base OS".
    """
    feature: Feature | None = base_os.features.get("Base OS")
    if feature is None:
        raise ValueError("Base OS feature not found in base_os FeatureList")

    cluster = [_package_to_dict(pkg) for pkg in feature.packages]
    logger.info("Built default_packages config with %d package(s)", len(cluster))
    return {"default_packages": {"cluster": cluster}}


def _build_subconfig_from_base_os(
    base_os: FeatureList, name: str, substrings: Iterable[str]
) -> Dict | None:
    """Generic helper to build nfs/openldap/openmpi-style configs.

    Selects packages from Base OS whose package name contains any of the substrings.
    Returns None if no packages match.
    """
    feature: Feature | None = base_os.features.get("Base OS")
    if feature is None:
        return None

    lowered = [s.lower() for s in substrings]
    selected = [
        pkg
        for pkg in feature.packages
        if any(sub in pkg.package.lower() for sub in lowered)
    ]
    if not selected:
        logger.info("No %s packages found in Base OS for substrings %s", name, list(substrings))
        return None

    cluster = [_package_to_dict(pkg) for pkg in selected]
    logger.info("Built %s config with %d package(s)", name, len(cluster))
    return {name: {"cluster": cluster}}


def build_nfs_config(base_os: FeatureList) -> Dict | None:
    """Build nfs config from Base OS FeatureList."""
    return _build_subconfig_from_base_os(base_os, "nfs", ["nfs"])


def build_openldap_config(base_os: FeatureList) -> Dict | None:
    """Build openldap config from Base OS FeatureList."""
    return _build_subconfig_from_base_os(base_os, "openldap", ["ldap"])


def build_openmpi_config(base_os: FeatureList) -> Dict | None:
    """Build openmpi config from Base OS FeatureList."""
    return _build_subconfig_from_base_os(base_os, "openmpi", ["openmpi"])


# -------------------------- K8s services from functional layer --------------------------


def build_service_k8s_config(functional: FeatureList) -> Dict:
    """Build service_k8s.json-like structure from functional FeatureList.

    Uses feature names "K8S Controller" and "K8S Worker" if present.
    Common packages (intersection) go into service_k8s; they are removed from the
    controller/worker clusters.
    """
    controller: Feature | None = functional.features.get("K8S Controller")
    worker: Feature | None = functional.features.get("K8S Worker")

    if controller is None or worker is None:
        raise ValueError("K8S Controller or K8S Worker feature not found in functional layer")

    ctrl_pkgs = controller.packages
    node_pkgs = worker.packages

    ctrl_keys = {_package_key(p) for p in ctrl_pkgs}
    node_keys = {_package_key(p) for p in node_pkgs}
    common_keys = ctrl_keys & node_keys

    def _filter(pkgs: List[Package], exclude: set[Tuple[str, str, str]]) -> List[Package]:
        return [p for p in pkgs if _package_key(p) not in exclude]

    # Keep order, but only one instance of each common key
    seen_common: set[Tuple[str, str, str]] = set()
    common_pkgs: List[Package] = []
    for pkg in ctrl_pkgs + node_pkgs:
        k = _package_key(pkg)
        if k in common_keys and k not in seen_common:
            seen_common.add(k)
            common_pkgs.append(pkg)

    logger.info(
        "Built service_k8s config: %d controller pkg(s), %d worker pkg(s), %d common pkg(s)",
        len(ctrl_pkgs),
        len(node_pkgs),
        len(common_pkgs),
    )

    return {
        "service_kube_control_plane": {
            "cluster": [_package_to_dict(p) for p in _filter(ctrl_pkgs, common_keys)]
        },
        "service_kube_node": {
            "cluster": [_package_to_dict(p) for p in _filter(node_pkgs, common_keys)]
        },
        "service_k8s": {"cluster": [_package_to_dict(p) for p in common_pkgs]},
    }


# -------------------------- Slurm custom from functional layer --------------------------


def build_slurm_custom_config(functional: FeatureList) -> Dict:
    """Build slurm_custom.json-style structure from functional FeatureList.

    Nodes used:
      - "Login Node"
      - "Compiler"
      - "Slurm Controller"
      - "Slurm Worker"

    Common packages are those that appear in any 2 or more of these nodes. They
    are removed from the individual node clusters and placed into slurm_custom.
    """
    login = functional.features.get("Login Node")
    compiler = functional.features.get("Compiler")
    slurm_ctrl = functional.features.get("Slurm Controller")
    slurm_worker = functional.features.get("Slurm Worker")

    if not all([login, compiler, slurm_ctrl, slurm_worker]):
        raise ValueError("One or more required Slurm-related features not found in functional layer")

    node_features: Dict[str, Feature] = {
        "login_node": login,
        "login_compiler_node": compiler,
        "slurm_control_node": slurm_ctrl,
        "slurm_node": slurm_worker,
    }

    # Count how many nodes each package appears in
    key_counts: Counter[Tuple[str, str, str]] = Counter()
    key_to_pkg: Dict[Tuple[str, str, str], Package] = {}

    for feature in node_features.values():
        seen_in_this_node: set[Tuple[str, str, str]] = set()
        for pkg in feature.packages:
            k = _package_key(pkg)
            key_to_pkg.setdefault(k, pkg)
            if k not in seen_in_this_node:
                seen_in_this_node.add(k)
                key_counts[k] += 1

    common_keys = {k for k, count in key_counts.items() if count >= 2}

    # Build node clusters without common packages
    output: Dict[str, Dict] = {}
    for node_name, feature in node_features.items():
        filtered_pkgs = [
            _package_to_dict(pkg)
            for pkg in feature.packages
            if _package_key(pkg) not in common_keys
        ]
        output[node_name] = {"cluster": filtered_pkgs}

    # Build slurm_custom cluster from common packages (dedup, keep deterministic order)
    common_pkg_dicts: List[Dict[str, str]] = []
    for k, pkg in key_to_pkg.items():
        if k in common_keys:
            common_pkg_dicts.append(_package_to_dict(pkg))

    output["slurm_custom"] = {"cluster": common_pkg_dicts}

    logger.info(
        "Built slurm_custom config with %d node cluster(s) and %d common package(s)",
        len(node_features),
        len(common_pkg_dicts),
    )

    return output


# -------------------------- Infrastructure splitting --------------------------


def build_infra_configs(infra: FeatureList) -> Dict[str, Dict]:
    """Split infrastructure FeatureList into separate config-style JSON structures.

    Returns a mapping of filename -> JSON dict. Filenames and top-level keys are
    derived from the feature names, with a special case for CSI to match the
    existing csi_driver_powerscale.json pattern.
    """
    configs: Dict[str, Dict] = {}

    for feature_name, feature in infra.features.items():
        name_snake = _snake_case(feature_name)

        if feature_name.lower() == "csi":
            file_name = "csi_driver_powerscale.json"
            top_key = "csi_driver_powerscale"
        else:
            file_name = f"{name_snake}.json"
            top_key = name_snake

        cluster = [_package_to_dict(pkg) for pkg in feature.packages]
        configs[file_name] = {top_key: {"cluster": cluster}}

    logger.info("Built %d infrastructure config file(s)", len(configs))

    return configs


# -------------------------- Utility: write configs to disk --------------------------


def write_config_files(configs: Dict[str, Dict], output_dir: str) -> None:
    """Write multiple config JSONs into an output directory.

    - configs: mapping of filename -> JSON-serializable dict
    - output_dir: directory under which files will be written
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Writing %d config file(s) to %s", len(configs), output_dir)
    for filename, data in configs.items():
        path = os.path.join(output_dir, filename)
        logger.debug("Writing config file %s", path)
        with open(path, "w", encoding="utf-8") as out_file:
            # Expect shape: { top_key: { "cluster": [pkg_dicts...] } }
            out_file.write("{\n")

            items = list(data.items())
            for i, (top_key, body) in enumerate(items):
                out_file.write(f"  {json.dumps(top_key)}: {{\n")
                out_file.write("    \"cluster\": [\n")

                pkgs = body.get("cluster", [])
                for j, pkg in enumerate(pkgs):
                    line = "      " + json.dumps(pkg, separators=(", ", ": "))
                    if j < len(pkgs) - 1:
                        line += ","
                    out_file.write(line + "\n")

                out_file.write("    ]\n")
                out_file.write("  }")
                if i < len(items) - 1:
                    out_file.write(",\n")
                else:
                    out_file.write("\n")

            out_file.write("}\n")


def generate_all_configs(
    functional: FeatureList,
    infra: FeatureList,
    base_os: FeatureList,
    misc: FeatureList,
    catalog: Catalog,
    output_root: str,
) -> None:
    """Driver that builds and writes all config-style JSONs.

    For each (arch, os_name, version) combination present in the Catalog's
    FunctionalPackages/OSPackages, this writes a full set of config-style
    JSONs under:

        output_root/<arch>/<os_name>/<version>

    Files written (if data available):
      - default_packages.json
      - nfs.json
      - openldap.json
      - openmpi.json
      - service_k8s.json
      - slurm_custom.json
      - one file per infrastructure feature (e.g. csi_driver_powerscale.json)
    """

    combos = _discover_arch_os_version_from_catalog(catalog)
    logger.info("Generating adapter configs for %d combination(s)", len(combos))
    for arch, os_name, version in combos:
        functional_arch = _filter_featurelist_for_arch(functional, arch)
        base_os_arch = _filter_featurelist_for_arch(base_os, arch)
        infra_arch = _filter_featurelist_for_arch(infra, arch)
        misc_arch = _filter_featurelist_for_arch(misc, arch)

        logger.info(
            "Building configs for arch=%s os=%s version=%s", arch, os_name, version
        )

        configs: Dict[str, Dict] = {}

        configs["default_packages.json"] = build_default_packages_config(base_os_arch)

        for filename, builder in (
            ("nfs.json", build_nfs_config),
            ("openldap.json", build_openldap_config),
            ("openmpi.json", build_openmpi_config),
        ):
            cfg = builder(base_os_arch)
            if cfg:
                configs[filename] = cfg

        configs["service_k8s.json"] = build_service_k8s_config(functional_arch)
        configs["slurm_custom.json"] = build_slurm_custom_config(functional_arch)

        misc_feature: Feature | None = misc_arch.features.get("Miscellaneous")
        if misc_feature is not None and misc_feature.packages:
            configs["miscellaneous.json"] = {
                "miscellaneous": {
                    "cluster": [_package_to_dict(p) for p in misc_feature.packages]
                }
            }

        infra_configs = build_infra_configs(infra_arch)
        configs.update(infra_configs)

        output_dir = os.path.join(output_root, arch, os_name, version)
        write_config_files(configs, output_dir)


def generate_omnia_json_from_catalog(
    catalog_path: str,
    schema_path: str = _DEFAULT_SCHEMA_PATH,
    output_root: str = "out/adapter/input/config",
    *,
    log_file: Optional[str] = None,
    configure_logging: bool = False,
    log_level: int = logging.INFO,
) -> None:
    """Generate adapter configuration JSONs for a catalog file.

    - If configure_logging is True, logging is configured using _configure_logging,
      optionally writing to log_file.
    - On missing files, FileNotFoundError is raised after logging an error.
    - No sys.exit is called; callers are expected to handle exceptions.
    """

    if configure_logging:
        _configure_logging(log_file=log_file, log_level=log_level)

    _validate_catalog_and_schema_paths(catalog_path, schema_path)

    catalog = ParseCatalog(catalog_path, schema_path)

    functional_layer_json = generate_functional_layer_json(catalog)
    infrastructure_json = generate_infrastructure_json(catalog)
    base_os_json = generate_base_os_json(catalog)
    miscellaneous_json = generate_miscellaneous_json(catalog)

    generate_all_configs(
        functional=functional_layer_json,
        infra=infrastructure_json,
        base_os=base_os_json,
        misc=miscellaneous_json,
        catalog=catalog,
        output_root=output_root,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate adapter configs')
    parser.add_argument('--catalog', required=True, help='Path to input catalog JSON file')
    parser.add_argument('--schema', required=False, default=_DEFAULT_SCHEMA_PATH,
                        help='Path to catalog schema JSON file')
    parser.add_argument('--log-file', required=False, default=None, help='Path to log file; if not set, logs go to stderr')
    args = parser.parse_args()

    _configure_logging(log_file=args.log_file, log_level=logging.INFO)

    logger.info("Adapter config generation started for %s", args.catalog)

    try:
        generate_omnia_json_from_catalog(
            catalog_path=args.catalog,
            schema_path=args.schema,
            output_root="out/adapter/input/config",
        )

        logger.info("Adapter config generation completed for %s", args.catalog)
    except FileNotFoundError:
        logger.error("File not found during processing")
        sys.exit(ERROR_CODE_INPUT_NOT_FOUND)
    except ValidationError:
        sys.exit(ERROR_CODE_PROCESSING_ERROR)
    except Exception:
        logger.exception("Unexpected error while generating adapter configs")
        sys.exit(ERROR_CODE_PROCESSING_ERROR)
