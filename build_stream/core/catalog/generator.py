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

"""Catalog parser generator.

Provides programmatic APIs and a CLI to generate feature-list JSON files from a
catalog, and to load/validate feature-list JSONs.
"""

import argparse
from dataclasses import dataclass
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

from jsonschema import ValidationError, validate

from .models import Catalog
from .parser import ParseCatalog
from .utils import _configure_logging, load_json_file

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_SCHEMA_PATH = os.path.join(_BASE_DIR, "resources", "CatalogSchema.json")
_ROOT_LEVEL_SCHEMA_PATH = os.path.join(_BASE_DIR, "resources", "RootLevelSchema.json")

ERROR_CODE_INPUT_NOT_FOUND = 2
ERROR_CODE_PROCESSING_ERROR = 3

# This code generates JSON files
# i.e baseos.json, infrastructure.json, functional_layer.json, miscellaneous.json
# for a given catalog

def _validate_catalog_and_schema_paths(catalog_path: str, schema_path: str) -> None:
    """Validate that the catalog and schema paths exist.

    Raises FileNotFoundError if either path does not exist.
    """

    if not os.path.isfile(catalog_path):
        logger.error("Catalog file not found: %s", catalog_path)
        raise FileNotFoundError(catalog_path)
    if not os.path.isfile(schema_path):
        logger.error("Schema file not found: %s", schema_path)
        raise FileNotFoundError(schema_path)


def _arch_suffix(architecture) -> str:
    """Return a single-arch suffix from a catalog Package.architecture field.

    Handles both legacy string values and new List[str] values.
    """
    if isinstance(architecture, list):
        if not architecture:
            return ""
        arch = architecture[0]
    else:
        arch = architecture
    return str(arch)


@dataclass
class Package:
    """Represents a package entry inside a generated FeatureList JSON."""

    package: str
    type: str
    repo_name: str
    architecture: List[str]
    uri: Optional[str] = None
    tag: Optional[str] = None
    sources: Optional[List[dict]] = None


@dataclass
class Feature:
    """Represents a single feature/role entry containing a list of packages."""

    feature_name: str
    packages: List[Package]


@dataclass
class FeatureList:
    """Collection of features keyed by feature/role name."""

    features: Dict[str, Feature]


def _filter_featurelist_for_arch(feature_list: FeatureList, arch: str) -> FeatureList:
    """Return a FeatureList containing only packages for the given arch.

    Arch is taken from the Package.architecture list.
    """
    filtered_features: Dict[str, Feature] = {}
    for name, feature in feature_list.features.items():
        narrowed_pkgs: List[Package] = []
        for p in feature.packages:
            if arch in getattr(p, "architecture", []):
                # Derive repo_name and uri from the catalog Sources metadata, if
                # present, for this specific architecture.
                repo_name = ""
                uri = getattr(p, "uri", None)
                if getattr(p, "sources", None):
                    for src in p.sources:
                        if src.get("Architecture") == arch:
                            if "RepoName" in src:
                                repo_name = src["RepoName"]
                            if "Uri" in src:
                                uri = src["Uri"]
                            break

                narrowed_pkgs.append(
                    Package(
                        package=p.package,
                        type=p.type,
                        repo_name=repo_name,
                        architecture=[arch],
                        uri=uri,
                        tag=p.tag,
                        sources=p.sources,
                    )
                )
        filtered_features[name] = Feature(feature_name=name, packages=narrowed_pkgs)
    return FeatureList(features=filtered_features)


def _discover_arch_os_version_from_catalog(catalog: Catalog) -> List[Tuple[str, str, str]]:
    """Discover distinct (arch, os_name, version) combinations in the Catalog.

    os_name is returned in lowercase (e.g. "rhel"), version as-is.
    """

    combos: set[Tuple[str, str, str]] = set()

    def _add_from_packages(packages):
        for pkg in packages:
            for os_entry in pkg.supported_os:
                parts = os_entry.split(" ", 1)
                if len(parts) == 2:
                    os_name_raw, os_ver = parts
                else:
                    os_name_raw, os_ver = os_entry, ""
                os_name = os_name_raw.lower()

                for arch in pkg.architecture:
                    combos.add((arch, os_name, os_ver))

    _add_from_packages(catalog.functional_packages)
    _add_from_packages(catalog.os_packages)

    combos_sorted = sorted(combos)
    logger.debug(
        "Discovered %d (arch, os, version) combinations in catalog %s",
        len(combos_sorted),
        getattr(catalog, "name", "<unknown>"),
    )
    return combos_sorted


def generate_functional_layer_json(catalog: Catalog) -> FeatureList:
    """
    Generates a JSON file containing the functional layer from a given catalog object.

    Args:
    - catalog (Catalog): The catalog object to generate the functional layer from.

    Returns:
    - FeatureList: The generated JSON data
    """
    output_json = FeatureList(features={})

    for layer in catalog.functional_layer:
        feature_json = Feature(
            feature_name=layer["Name"],
            packages=[],
        )

        for pkg_id in layer["FunctionalPackages"]:
            pkg = next((pkg for pkg in catalog.functional_packages if pkg.id == pkg_id), None)
            if pkg:
                feature_json.packages.append(
                    Package(
                        package=pkg.name,
                        type=pkg.type,
                        repo_name="",
                        architecture=pkg.architecture,
                        uri=None,
                        tag=getattr(pkg, "tag", None),
                        sources=pkg.sources,
                    )
                )

        output_json.features[feature_json.feature_name] = feature_json

    return output_json


def generate_infrastructure_json(catalog: Catalog) -> FeatureList:
    """
    Generates a JSON file containing the infrastructure from a given catalog object.

    Args:
    - catalog (Catalog): The catalog object to generate the infrastructure from.

    Returns:
    - FeatureList: The generated JSON data
    """
    output_json = FeatureList(features={})

    for infra in catalog.infrastructure:
        feature_json = Feature(
            feature_name=infra["Name"],
            packages=[],
        )

        for pkg_id in infra["InfrastructurePackages"]:
            pkg = next((pkg for pkg in catalog.infrastructure_packages if pkg.id == pkg_id), None)
            if pkg:
                feature_json.packages.append(
                    Package(
                        package=pkg.name,
                        type=pkg.type,
                        repo_name="",
                        architecture=pkg.architecture,
                        uri=None,
                        tag=getattr(pkg, "tag", None),
                        sources=pkg.sources,
                    )
                )

        output_json.features[feature_json.feature_name] = feature_json

    return output_json


def generate_drivers_json(catalog: Catalog) -> FeatureList:
    """
    Generates a JSON file containing the drivers from a given catalog object.

    Args:
    - catalog (Catalog): The catalog object to generate the drivers from.

    Returns:
    - FeatureList: The generated JSON data
    """
    output_json = FeatureList(features={})

    # Map driver package IDs -> Driver objects parsed from DriverPackages.
    drivers_by_id: Dict[str, any] = {drv.id: drv for drv in catalog.drivers}

    # If no grouping is present (backward compatibility), fall back to a single
    # "Drivers" feature containing all drivers.
    if not getattr(catalog, "drivers_layer", []):
        feature_json = Feature(
            feature_name="Drivers",
            packages=[]
        )
        for driver in catalog.drivers:
            feature_json.packages.append(
                Package(
                    package=driver.name,
                    type=driver.type,
                    repo_name="",
                    architecture=driver.architecture,
                    uri=None,
                    tag=None,
                    sources=None,
                )
            )
        output_json.features[feature_json.feature_name] = feature_json
        return output_json

    # Respect grouping similar to FunctionalLayer: one Feature per driver group.
    for group in catalog.drivers_layer:
        group_name = group.get("Name")
        driver_ids = group.get("DriverPackages", [])
        if not group_name or not driver_ids:
            continue

        feature_json = Feature(
            feature_name=group_name,
            packages=[]
        )

        for driver_id in driver_ids:
            driver = drivers_by_id.get(driver_id)
            if not driver:
                continue

            feature_json.packages.append(
                Package(
                    package=driver.name,
                    type=driver.type,
                    repo_name="",
                    architecture=driver.architecture,
                    uri=None,
                    tag=None,
                    sources=None,
                )
            )

        output_json.features[feature_json.feature_name] = feature_json

    return output_json


def generate_base_os_json(catalog: Catalog) -> FeatureList:
    """
    Generates a JSON file containing the base OS from a given catalog object.

    Args:
    - catalog (Catalog): The catalog object to generate the base OS from.

    Returns:
    - FeatureList: The generated JSON data
    """
    output_json = FeatureList(features={})

    feature_json = Feature(
        feature_name="Base OS",
        packages=[]
    )

    for entry in catalog.base_os:
        for pkg_id in entry["osPackages"]:
            pkg = next((pkg for pkg in catalog.os_packages if pkg.id == pkg_id), None)
            if pkg:
                feature_json.packages.append(
                    Package(
                        package=pkg.name,
                        type=pkg.type,
                        repo_name="",
                        architecture=pkg.architecture,
                        uri=None,
                        tag=getattr(pkg, "tag", None),
                        sources=pkg.sources,
                    )
                )

    output_json.features[feature_json.feature_name] = feature_json

    return output_json


def generate_miscellaneous_json(catalog: Catalog) -> FeatureList:
    """Generate a FeatureList for the Miscellaneous group, if present.

    The catalog is expected to carry a Miscellaneous array of package IDs,
    referencing FunctionalPackages. This creates a single feature named
    "Miscellaneous" containing those packages.
    """
    output_json = FeatureList(features={})

    feature_json = Feature(
        feature_name="Miscellaneous",
        packages=[],
    )

    misc_ids = getattr(catalog, "miscellaneous", [])
    for pkg_id in misc_ids:
        pkg = next((pkg for pkg in catalog.functional_packages if pkg.id == pkg_id), None)
        if not pkg:
            continue

        feature_json.packages.append(
            Package(
                package=pkg.name,
                type=pkg.type,
                repo_name="",
                architecture=pkg.architecture,
                uri=None,
                tag=getattr(pkg, "tag", None),
                sources=pkg.sources,
            )
        )

    output_json.features[feature_json.feature_name] = feature_json

    return output_json


def _package_common_dict(pkg: Package) -> Dict:
    """Common dict representation for a Package (no architecture).

    Shared between generator and adapter to keep JSON field formatting
    consistent for package, type, repo_name, uri, and tag.
    """
    data: Dict = {"package": pkg.package, "type": pkg.type}
    if getattr(pkg, "repo_name", ""):
        data["repo_name"] = pkg.repo_name
    if getattr(pkg, "uri", None) is not None:
        data["uri"] = pkg.uri
    if getattr(pkg, "tag", "") and pkg.tag != "":
        data["tag"] = pkg.tag
    return data


def _package_to_json_dict(pkg: Package) -> Dict:
    data = _package_common_dict(pkg)
    data["architecture"] = pkg.architecture
    return data


def _package_from_json_dict(data: Dict) -> Package:
    return Package(
        package=data["package"],
        type=data["type"],
        repo_name=data.get("repo_name", ""),
        architecture=data.get("architecture", []),
        uri=data.get("uri"),
        tag=data.get("tag"),
    )


def serialize_json(feature_list: FeatureList, output_path: str):
    """
    Serializes the output JSON data to a file.

    Args:
    - feature_list (FeatureList): The feature list data to serialize.
    - output_path (str): The path to write the serialized JSON file to.
    """
    # Custom pretty-printer so that:
    #   - Overall JSON is nicely indented
    #   - Each package entry inside "packages" is a single-line JSON object
    logger.info(
        "Writing FeatureList with %d feature(s) to %s",
        len(feature_list.features),
        output_path,
    )
    with open(output_path, "w", encoding="utf-8") as out_file:
        out_file.write("{\n")

        items = list(feature_list.features.items())
        for i, (feature_name, feature) in enumerate(items):
            # Feature key
            out_file.write(f"  {json.dumps(feature_name)}: {{\n")
            out_file.write("    \"packages\": [\n")

            pkgs = feature.packages
            for j, pkg in enumerate(pkgs):
                pkg_dict = _package_to_json_dict(pkg)
                line = "      " + json.dumps(pkg_dict, separators=(", ", ": "))
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


def deserialize_json(input_path: str) -> FeatureList:
    """
    Deserializes a JSON file to output JSON data.

    Args:
    - input_path (str): The path to read the JSON file from.

    Returns:
    - FeatureList: The deserialized JSON data
    """
    json_data = load_json_file(input_path)

    logger.debug("Deserializing FeatureList from %s", input_path)

    feature_list = FeatureList(
        features={
            feature_name: Feature(
                feature_name=feature_name,
                packages=[
                    _package_from_json_dict(pkg)
                    for pkg in feature_body.get("packages", [])
                ],
            )
            for feature_name, feature_body in json_data.items()
        }
    )

    logger.info(
        "Deserialized FeatureList with %d feature(s) from %s",
        len(feature_list.features),
        input_path,
    )

    return feature_list


def get_functional_layer_roles_from_file(
    functional_layer_json_path: str,
    *,
    configure_logging: bool = False,
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
) -> List[str]:
    """Return role names (top-level keys) from a functional_layer.json file.

    The input JSON is validated against RootLevelSchema.json before it is
    deserialized.
    """
    if configure_logging:
        _configure_logging(log_file=log_file, log_level=log_level)

    logger.info("get_functional_layer_roles_from_file started for %s", functional_layer_json_path)
    logger.debug("Loading root-level schema from %s", _ROOT_LEVEL_SCHEMA_PATH)
    schema = load_json_file(_ROOT_LEVEL_SCHEMA_PATH)

    logger.debug("Validating JSON")
    json_data = load_json_file(functional_layer_json_path)

    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as exc:
        logger.error(
            "JSON validation failed for %s",
            functional_layer_json_path,
        )
        raise
    logger.info("JSON validation succeeded")

    feature_list = deserialize_json(functional_layer_json_path)
    logger.debug("Populating roles info")
    roles = list(feature_list.features.keys())
    logger.info(
        "get_functional_layer_roles_from_file completed for %s (roles=%d)",
        functional_layer_json_path,
        len(roles),
    )
    return roles


def get_package_list(
    functional_layer_json_path: str,
    role: Optional[str] = None,
    *,
    configure_logging: bool = False,
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
) -> List[Dict]:
    """Return packages for a specific role or all roles from a functional_layer.json file.

    The input JSON is validated against RootLevelSchema.json before it is
    deserialized.

    Args:
        functional_layer_json_path: Path to the functional_layer.json file.
        role: Optional role identifier. If None, returns packages for all roles.
        configure_logging: If True, configure logging with optional file output.
        log_file: Path to log file; if not set, logs go to stderr.
        log_level: Logging level (default: logging.INFO).

    Returns:
        List of role objects, each containing:
        - roleName: str
        - packages: List[Dict] with keys: name, type, repo_name, architecture, uri, tag

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        ValidationError: If the JSON fails schema validation.
        ValueError: If the specified role does not exist.
    """
    if configure_logging:
        _configure_logging(log_file=log_file, log_level=log_level)

    logger.info(
        "get_package_list started for %s (role=%s)",
        functional_layer_json_path,
        role if role else "all",
    )

    logger.debug("Checking if file exists: %s", functional_layer_json_path)
    if not os.path.isfile(functional_layer_json_path):
        logger.error("File not found: %s", functional_layer_json_path)
        raise FileNotFoundError(functional_layer_json_path)

    logger.debug("Loading root-level schema from %s", _ROOT_LEVEL_SCHEMA_PATH)
    with open(_ROOT_LEVEL_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    logger.debug("Loading and validating JSON from %s", functional_layer_json_path)
    with open(functional_layer_json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as exc:
        logger.error(
            "JSON validation failed for %s",
            functional_layer_json_path,
        )
        raise
    logger.info("JSON validation succeeded for %s", functional_layer_json_path)

    logger.debug("Deserializing feature list from %s", functional_layer_json_path)
    feature_list = deserialize_json(functional_layer_json_path)

    available_roles = list(feature_list.features.keys())
    logger.debug("Available roles: %s", available_roles)

    if role is not None:
        logger.debug("Filtering for specific role: %s", role)
        if role == "":
            logger.error(
                "Invalid role input: empty string for %s (available roles: %s)",
                functional_layer_json_path,
                available_roles,
            )
            raise ValueError("Role must be a non-empty string")
        # Case-insensitive role matching
        role_lower = role.lower()
        matched_role = None
        for available_role in available_roles:
            if available_role.lower() == role_lower:
                matched_role = available_role
                break

        if matched_role is None:
            logger.error(
                "Role '%s' not found in %s. Available roles: %s",
                role,
                functional_layer_json_path,
                available_roles,
            )
            raise ValueError(
                f"Role '{role}' not found. Available roles: {available_roles}"
            )
        roles_to_process = [matched_role]
    else:
        logger.debug("Processing all roles")
        roles_to_process = available_roles

    result: List[Dict] = []
    total_packages = 0

    for role_name in roles_to_process:
        feature = feature_list.features[role_name]
        packages_list = []

        for pkg in feature.packages:
            pkg_dict = {
                "name": pkg.package,
                "type": pkg.type,
                "repo_name": pkg.repo_name if pkg.repo_name else None,
                "architecture": pkg.architecture,
                "uri": pkg.uri,
                "tag": pkg.tag,
            }
            packages_list.append(pkg_dict)

        role_obj = {
            "roleName": role_name,
            "packages": packages_list,
        }
        result.append(role_obj)
        total_packages += len(packages_list)
        logger.debug(
            "Processed role '%s': %d packages",
            role_name,
            len(packages_list),
        )

    logger.info(
        "get_package_list completed for %s: %d role(s), %d total package(s)",
        functional_layer_json_path,
        len(result),
        total_packages,
    )

    return result


def generate_root_json_from_catalog(
    catalog_path: str,
    schema_path: str = _DEFAULT_SCHEMA_PATH,
    output_root: str = "out/generator",
    *,
    log_file: Optional[str] = None,
    configure_logging: bool = False,
    log_level: int = logging.INFO,
) -> None:
    """Generate per-arch/OS/version FeatureList JSONs for a catalog file.

    - If configure_logging is True, logging is configured using _configure_logging,
      optionally writing to log_file.
    - On missing files, FileNotFoundError is raised after logging an error.
    - No sys.exit is called; callers are expected to handle exceptions.
    """
    # Optional logging configuration for library callers
    if configure_logging:
        _configure_logging(log_file=log_file, log_level=log_level)

    # Shared input validation
    _validate_catalog_and_schema_paths(catalog_path, schema_path)

    catalog = ParseCatalog(catalog_path, schema_path)

    functional_layer_json = generate_functional_layer_json(catalog)
    infrastructure_json = generate_infrastructure_json(catalog)
    drivers_json = generate_drivers_json(catalog)
    base_os_json = generate_base_os_json(catalog)
    miscellaneous_json = generate_miscellaneous_json(catalog)

    combos = _discover_arch_os_version_from_catalog(catalog)
    logger.info(
        "Discovered %d combination(s) for feature-list generation", len(combos)
    )

    for arch, os_name, version in combos:
        base_dir = os.path.join(output_root, arch, os_name, version)
        os.makedirs(base_dir, exist_ok=True)

        logger.info(
            "Generating feature-list JSONs for arch=%s os=%s version=%s into %s",
            arch,
            os_name,
            version,
            base_dir,
        )

        func_arch = _filter_featurelist_for_arch(functional_layer_json, arch)
        infra_arch = _filter_featurelist_for_arch(infrastructure_json, arch)
        drivers_arch = _filter_featurelist_for_arch(drivers_json, arch)
        base_os_arch = _filter_featurelist_for_arch(base_os_json, arch)
        misc_arch = _filter_featurelist_for_arch(miscellaneous_json, arch)

        serialize_json(func_arch, os.path.join(base_dir, 'functional_layer.json'))
        serialize_json(infra_arch, os.path.join(base_dir, 'infrastructure.json'))
        serialize_json(drivers_arch, os.path.join(base_dir, 'drivers.json'))
        serialize_json(base_os_arch, os.path.join(base_dir, 'base_os.json'))
        serialize_json(misc_arch, os.path.join(base_dir, 'miscellaneous.json'))


if __name__ == "__main__":
    # Example usage: generate per-arch/OS/version FeatureList JSONs under
    # out/<arch>/<os_name>/<version>/

    parser = argparse.ArgumentParser(description="Catalog Parser CLI")
    parser.add_argument(
        "--catalog",
        required=True,
        help="Path to input catalog JSON file",
    )
    parser.add_argument(
        "--schema",
        required=False,
        default=_DEFAULT_SCHEMA_PATH,
        help="Path to catalog schema JSON file",
    )
    parser.add_argument(
        "--log-file",
        required=False,
        default=None,
        help="Path to log file; if not set, logs go to stderr",
    )

    args = parser.parse_args()

    # Configure logging once for the CLI
    _configure_logging(log_file=args.log_file, log_level=logging.INFO)

    logger.info("Catalog Parser CLI started for %s", args.catalog)

    try:
        # Reuse the programmatic API to generate all FeatureList JSONs.
        generate_root_json_from_catalog(
            catalog_path=args.catalog,
            schema_path=args.schema,
            output_root=os.path.join("out", "main"),
        )

        logger.info("Catalog Parser CLI completed for %s", args.catalog)

    except FileNotFoundError:
        logger.error("File not found during processing")
        sys.exit(ERROR_CODE_INPUT_NOT_FOUND)
    except ValidationError:
        sys.exit(ERROR_CODE_PROCESSING_ERROR)
    except Exception:
        logger.exception("Unexpected error while generating feature-list JSONs")
        sys.exit(ERROR_CODE_PROCESSING_ERROR)