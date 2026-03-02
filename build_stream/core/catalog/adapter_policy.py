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

"""Adapter to generate Omnia input JSONs from policy.

Transforms root JSONs from the main directory into target adapter config JSONs
using a declarative adapter policy file.
"""

import json
import os
import argparse
import logging
import shutil
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

import yaml

from jsonschema import ValidationError, validate

from .utils import _configure_logging, load_json_file
from . import adapter_policy_schema_consts as schema

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_POLICY_PATH = os.path.join(_BASE_DIR, "resources", "adapter_policy_default.json")
_DEFAULT_SCHEMA_PATH = os.path.join(_BASE_DIR, "resources", "AdapterPolicySchema.json")

_K8S_VERSION = "1.34.1"
_CSI_VERSION = "v2.15.0"


def _validate_input_policy_and_schema_paths(
    input_dir: str,
    policy_path: str,
    schema_path: str,
) -> None:
    if not os.path.isdir(input_dir):
        logger.error("Input directory not found: %s", input_dir)
        raise FileNotFoundError(input_dir)
    if not os.path.isfile(policy_path):
        logger.error("Adapter policy file not found: %s", policy_path)
        raise FileNotFoundError(policy_path)
    if not os.path.isfile(schema_path):
        logger.error("Adapter policy schema file not found: %s", schema_path)
        raise FileNotFoundError(schema_path)


def validate_policy_config(policy_config: Any, schema_config: Any, policy_path: str, schema_path: str) -> None:
    """Validate the adapter policy JSON against the schema."""
    try:
        validate(instance=policy_config, schema=schema_config)
    except ValidationError as exc:
        loc = "/".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "<root>"
        raise ValueError(
            "Adapter policy validation failed.\n"
            f"Policy: {policy_path}\n"
            f"Schema: {schema_path}\n"
            f"At: {loc}\n"
            f"Error: {exc.message}"
        ) from exc


def discover_architectures(input_dir: str) -> List[str]:
    """Discover available architectures from input directory structure."""
    archs = []
    if os.path.isdir(input_dir):
        for item in os.listdir(input_dir):
            item_path = os.path.join(input_dir, item)
            if os.path.isdir(item_path):
                archs.append(item)
    return archs


def discover_os_versions(input_dir: str, arch: str) -> List[Tuple[str, str]]:
    """Discover OS families and versions for a given architecture.

    Returns list of (os_family, version) tuples.
    """
    results = []
    arch_path = os.path.join(input_dir, arch)
    if not os.path.isdir(arch_path):
        return results

    for os_family in os.listdir(arch_path):
        os_family_path = os.path.join(arch_path, os_family)
        if os.path.isdir(os_family_path):
            for version in os.listdir(os_family_path):
                version_path = os.path.join(os_family_path, version)
                if os.path.isdir(version_path):
                    results.append((os_family, version))
    return results






def _has_non_empty_cluster(target_data: Dict) -> bool:
    """Return True if any subgroup in target_data has a non-empty cluster list."""
    for subgroup_body in target_data.values():
        if subgroup_body.get(schema.CLUSTER):
            return True
    return False


def _collect_non_empty_subgroups(
    target_name: str,
    target_data: Dict,
) -> List[str]:
    """Return subgroup names that have non-empty cluster and differ from target_name."""
    return [
        key for key, body in target_data.items()
        if key != target_name and body.get(schema.CLUSTER)
    ]


def generate_software_config(
    output_dir: str,
    os_family: str,
    os_version: str,
    all_arch_target_configs: Dict[str, Dict[str, Dict]],
) -> None:
    """Generate software_config.json from collected target configs.

    Args:
        output_dir: Root output directory (file written to output_dir/input/software_config.json).
        os_family: OS family string (e.g. "rhel").
        os_version: OS version string (e.g. "10.0").
        all_arch_target_configs: Mapping of arch -> {target_file -> {subgroup -> {cluster: [...]}}}.
    """
    # Discover all target files across architectures
    all_target_files: set = set()
    for arch_targets in all_arch_target_configs.values():
        all_target_files.update(arch_targets.keys())

    softwares: List[Dict] = []
    subgroup_sections: Dict[str, List[Dict]] = {}

    for target_file in sorted(all_target_files):
        target_name = target_file.removesuffix(".json")

        # Determine which arches have non-empty content for this target
        supported_arches: List[str] = []
        for arch in sorted(all_arch_target_configs.keys()):
            target_data = all_arch_target_configs[arch].get(target_file)
            if target_data and _has_non_empty_cluster(target_data):
                supported_arches.append(arch)

        if not supported_arches:
            continue

        entry: Dict[str, Any] = {"name": target_name}
        if "service_k8" in target_name:
            entry["version"] = _K8S_VERSION
        elif "csi" in target_name:
            entry["version"] = _CSI_VERSION
        entry["arch"] = supported_arches
        softwares.append(entry)

        # Collect subgroups (union across arches, non-empty only, exclude target name)
        merged_subgroups: set = set()
        for arch in all_arch_target_configs:
            target_data = all_arch_target_configs[arch].get(target_file)
            if target_data:
                merged_subgroups.update(
                    _collect_non_empty_subgroups(target_name, target_data)
                )
        if merged_subgroups:
            subgroup_sections[target_name] = [
                {"name": sg} for sg in sorted(merged_subgroups)
            ]

    config: Dict[str, Any] = {
        "cluster_os_type": os_family,
        "cluster_os_version": os_version,
        "repo_config": "partial",
        "softwares": softwares,
    }
    config.update(subgroup_sections)

    input_dir = os.path.join(output_dir, "input")
    os.makedirs(input_dir, exist_ok=True)
    output_path = os.path.join(input_dir, "software_config.json")

    # Write with compact single-line arrays to match expected format
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("{\n")
        
        # Write top-level fields
        f.write(f'    "cluster_os_type": "{config["cluster_os_type"]}",\n')
        f.write(f'    "cluster_os_version": "{config["cluster_os_version"]}",\n')
        f.write(f'    "repo_config": "{config["repo_config"]}",\n')
        
        # Write softwares array (compact format)
        f.write('    "softwares": [\n')
        softwares = config["softwares"]
        for i, sw in enumerate(softwares):
            line = "        " + json.dumps(sw, separators=(",", ": "))
            if i < len(softwares) - 1:
                line += ","
            f.write(line + "\n")
        f.write('    ]')
        
        # Write subgroup sections (compact format)
        subgroup_keys = [k for k in config.keys() if k not in ("cluster_os_type", "cluster_os_version", "repo_config", "softwares")]
        for key in subgroup_keys:
            f.write(',\n')
            f.write(f'    "{key}": [\n')
            items = config[key]
            for i, item in enumerate(items):
                line = "        " + json.dumps(item, separators=(",", ": "))
                if i < len(items) - 1:
                    line += ","
                f.write(line + "\n")
            f.write('    ]')
        
        f.write("\n\n}\n")

    logger.info("Generated software_config.json at: %s", output_path)


def _package_key(pkg: Dict) -> Tuple[str, str, str]:
    """Generate a stable key for a package.

    For v2 derived operations (common package extraction), we want equivalence based on
    the full package definition except architecture. This avoids collisions for tarballs
    where repo_name is absent and uri differs.
    """

    def _hashable(v: Any) -> Any:
        if isinstance(v, (dict, list)):
            return json.dumps(v, sort_keys=True)
        return v

    return tuple(
        sorted(
            (k, _hashable(v))
            for k, v in pkg.items()
            if k != "architecture"
        )
    )


def transform_package(pkg: Dict, transform_config: Optional[Dict]) -> Dict:
    """Apply transformation rules to a package dict (excluding filter)."""
    if not transform_config:
        return pkg.copy()

    result = pkg.copy()

    exclude_fields = transform_config.get(schema.EXCLUDE_FIELDS, [])
    for field in exclude_fields:
        result.pop(field, None)

    rename_fields = transform_config.get(schema.RENAME_FIELDS, {})
    for old_name, new_name in rename_fields.items():
        if old_name in result:
            result[new_name] = result.pop(old_name)

    return result


def apply_substring_filter(
    packages: List[Dict],
    filter_config: Dict
) -> List[Dict]:
    """Filter packages by substring matching on a specified field."""
    field = filter_config.get(schema.FIELD, "package")
    values = filter_config.get(schema.VALUES, [])
    case_sensitive = filter_config.get(schema.CASE_SENSITIVE, False)

    if not values:
        return packages

    filtered = []
    for pkg in packages:
        field_value = pkg.get(field, "")
        if not case_sensitive:
            field_value = field_value.lower()
            check_values = [v.lower() for v in values]
        else:
            check_values = values

        if any(v in field_value for v in check_values):
            filtered.append(pkg)

    return filtered


def apply_allowlist_filter(
    packages: List[Dict],
    filter_config: Dict,
) -> List[Dict]:
    field = filter_config.get(schema.FIELD, "package")
    values = filter_config.get(schema.VALUES, [])
    case_sensitive = filter_config.get(schema.CASE_SENSITIVE, False)

    if not values:
        return packages

    if not case_sensitive:
        allowed = {str(v).lower() for v in values}
    else:
        allowed = {str(v) for v in values}

    result: List[Dict] = []
    for pkg in packages:
        field_value = pkg.get(field)
        if field_value is None:
            continue
        s = str(field_value)
        if not case_sensitive:
            s = s.lower()
        if s in allowed:
            result.append(pkg)
    return result


def apply_field_in_filter(
    packages: List[Dict],
    filter_config: Dict,
) -> List[Dict]:
    field = filter_config.get(schema.FIELD)
    values = filter_config.get(schema.VALUES, [])
    case_sensitive = filter_config.get(schema.CASE_SENSITIVE, False)

    if not field or not values:
        return packages

    if not case_sensitive:
        allowed = {str(v).lower() for v in values}
    else:
        allowed = {str(v) for v in values}

    result: List[Dict] = []
    for pkg in packages:
        field_value = pkg.get(field)
        if field_value is None:
            continue

        if isinstance(field_value, list):
            vals = [str(v) for v in field_value]
            if not case_sensitive:
                vals = [v.lower() for v in vals]
            if any(v in allowed for v in vals):
                result.append(pkg)
        else:
            s = str(field_value)
            if not case_sensitive:
                s = s.lower()
            if s in allowed:
                result.append(pkg)
    return result


def apply_any_of_filter(
    packages: List[Dict],
    source_data: Dict,
    source_key: str,
    filter_config: Dict,
) -> List[Dict]:
    filters = filter_config.get(schema.FILTERS, [])
    if not filters:
        return packages

    result: List[Dict] = []
    for pkg in packages:
        for sub_filter in filters:
            filtered = apply_filter([pkg], source_data, source_key, sub_filter)
            if filtered:
                result.append(pkg)
                break
    return result


def compute_common_packages(
    source_data: Dict,
    compare_keys: List[str],
    min_occurrences: int = 2
) -> Tuple[set, Dict[Tuple, Dict]]:
    """Compute packages that appear in multiple source keys.

    Returns:
        - Set of common package keys
        - Dict mapping package key to package dict
    """
    key_counts: Counter = Counter()
    key_to_pkg: Dict[Tuple, Dict] = {}

    for source_key in compare_keys:
        if source_key not in source_data:
            continue

        feature = source_data[source_key]
        packages = feature.get(schema.PACKAGES, [])

        seen_in_this_key: set = set()
        for pkg in packages:
            k = _package_key(pkg)
            key_to_pkg.setdefault(k, pkg)
            if k not in seen_in_this_key:
                seen_in_this_key.add(k)
                key_counts[k] += 1

    common_keys = {k for k, count in key_counts.items() if count >= min_occurrences}
    return common_keys, key_to_pkg


def apply_extract_common_filter(
    packages: List[Dict],
    source_data: Dict,
    filter_config: Dict
) -> List[Dict]:
    """Extract packages that are common across multiple source keys."""
    compare_keys = filter_config.get(schema.COMPARE_KEYS, [])
    min_occurrences = filter_config.get(schema.MIN_OCCURRENCES, 2)

    if not compare_keys:
        return packages

    common_keys, key_to_pkg = compute_common_packages(source_data, compare_keys, min_occurrences)

    # Return common packages in deterministic order
    result = []
    seen = set()
    for k, pkg in key_to_pkg.items():
        if k in common_keys and k not in seen:
            seen.add(k)
            result.append(pkg)

    return result


def apply_extract_unique_filter(
    packages: List[Dict],
    source_data: Dict,
    _source_key: str,
    filter_config: Dict
) -> List[Dict]:
    """Extract packages unique to the current source key (not common with others)."""
    compare_keys = filter_config.get(schema.COMPARE_KEYS, [])
    min_occurrences = filter_config.get(schema.MIN_OCCURRENCES, 2)

    if not compare_keys:
        return packages

    common_keys, _ = compute_common_packages(source_data, compare_keys, min_occurrences)

    # Return packages from current source_key that are NOT in common
    return [pkg for pkg in packages if _package_key(pkg) not in common_keys]


def apply_filter(
    packages: List[Dict],
    _source_data: Dict,
    _source_key: str,
    filter_config: Optional[Dict]
) -> List[Dict]:
    """Apply filter based on filter type."""
    if not filter_config:
        return packages

    filter_type = filter_config.get(schema.TYPE)

    if filter_type == schema.SUBSTRING_FILTER:
        return apply_substring_filter(packages, filter_config)

    if filter_type == schema.ALLOWLIST_FILTER:
        return apply_allowlist_filter(packages, filter_config)

    if filter_type == schema.FIELD_IN_FILTER:
        return apply_field_in_filter(packages, filter_config)

    if filter_type == schema.ANY_OF_FILTER:
        return apply_any_of_filter(packages, _source_data, _source_key, filter_config)

    logger.warning("Unknown/unsupported filter type in v2: %s", filter_type)
    return packages


def merge_transform(base: Optional[Dict], override: Optional[Dict]) -> Optional[Dict]:
    """Merge two transform dicts where override wins."""
    if not base and not override:
        return None
    if not base:
        return override
    if not override:
        return base
    merged = base.copy()
    merged.update(override)
    return merged


def compute_common_keys_from_roles(
    roles: Dict[str, List[Dict]],
    from_keys: List[str],
    min_occurrences: int
) -> set:
    """Compute package keys that are common across the given target roles."""
    key_counts: Counter = Counter()
    for role_key in from_keys:
        pkgs = roles.get(role_key, [])
        seen_in_role: set = set()
        for pkg in pkgs:
            k = _package_key(pkg)
            if k not in seen_in_role:
                seen_in_role.add(k)
                key_counts[k] += 1
    return {k for k, count in key_counts.items() if count >= min_occurrences}


def derive_common_role(
    target_roles: Dict[str, List[Dict]],
    derived_key: str,
    from_keys: List[str],
    min_occurrences: int = 2,
    remove_from_sources: bool = True
) -> None:
    """Derive a common role and optionally remove common packages from source roles."""
    common_keys = compute_common_keys_from_roles(target_roles, from_keys, min_occurrences)

    common_pkgs: List[Dict] = []
    seen: set = set()
    for role_key in from_keys:
        for pkg in target_roles.get(role_key, []):
            k = _package_key(pkg)
            if k in common_keys and k not in seen:
                seen.add(k)
                common_pkgs.append(pkg)

    target_roles[derived_key] = common_pkgs

    if remove_from_sources:
        for role_key in from_keys:
            target_roles[role_key] = [
                pkg for pkg in target_roles.get(role_key, [])
                if _package_key(pkg) not in common_keys
            ]


def check_conditions(
    conditions: Optional[Dict],
    arch: str,
    os_family: str,
    os_version: str
) -> bool:
    """Check if mapping conditions are satisfied."""
    if not conditions:
        return True

    if schema.ARCHITECTURES in conditions:
        if arch not in conditions[schema.ARCHITECTURES]:
            return False

    if schema.OS_FAMILIES in conditions:
        if os_family not in conditions[schema.OS_FAMILIES]:
            return False

    if schema.OS_VERSIONS in conditions:
        if os_version not in conditions[schema.OS_VERSIONS]:
            return False

    return True


def process_target_spec(
    target_file: str,
    target_spec: Dict,
    source_files: Dict[str, Dict],
    target_configs: Dict[str, Dict],
    arch: str,
    os_family: str,
    os_version: str
) -> None:
    """Build a single target file config using v2 target-centric spec."""
    conditions = target_spec.get(schema.CONDITIONS)
    if not check_conditions(conditions, arch, os_family, os_version):
        logger.debug("Skipping target %s (conditions not met)", target_file)
        return

    target_level_transform = target_spec.get(schema.TRANSFORM)

    target_roles: Dict[str, List[Dict]] = {}

    for source_spec in target_spec.get(schema.SOURCES, []):
        source_file = source_spec.get(schema.SOURCE_FILE)
        if not source_file or source_file not in source_files:
            logger.debug("Source file %s not loaded/available", source_file)
            continue

        source_data = source_files[source_file]

        for pull in source_spec.get(schema.PULLS, []):
            source_key = pull.get(schema.SOURCE_KEY)
            if not source_key or source_key not in source_data:
                logger.debug("Source key '%s' not found in %s", source_key, source_file)
                continue

            target_key = pull.get(schema.TARGET_KEY) or source_key
            filter_config = pull.get(schema.FILTER)
            pull_transform = merge_transform(target_level_transform, pull.get(schema.TRANSFORM))

            packages = source_data[source_key].get(schema.PACKAGES, [])
            packages = apply_filter(packages, source_data, source_key, filter_config)
            packages = [transform_package(pkg, pull_transform) for pkg in packages]

            target_roles[target_key] = packages

    for derived in target_spec.get(schema.DERIVED, []) or []:
        derived_key = derived.get(schema.TARGET_KEY)
        operation = derived.get(schema.OPERATION, {})
        op_type = operation.get(schema.TYPE)
        if op_type != schema.EXTRACT_COMMON_OPERATION:
            logger.warning("Unsupported derived operation type: %s", op_type)
            continue

        from_keys = operation.get(schema.FROM_KEYS, [])
        min_occurrences = operation.get(schema.MIN_OCCURRENCES, 2)
        remove_from_sources = operation.get(schema.REMOVE_FROM_SOURCES, True)

        if derived_key and from_keys:
            derive_common_role(
                target_roles=target_roles,
                derived_key=derived_key,
                from_keys=from_keys,
                min_occurrences=min_occurrences,
                remove_from_sources=remove_from_sources
            )

    if target_roles:
        target_configs[target_file] = {
            role_key: {schema.CLUSTER: pkgs}
            for role_key, pkgs in target_roles.items()
        }


def write_config_file(file_path: str, config: Dict) -> None:
    """Write a config JSON file with proper formatting."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as out_file:
        out_file.write("{\n")

        items = list(config.items())
        for i, (top_key, body) in enumerate(items):
            out_file.write(f'  "{top_key}": {{\n')
            out_file.write(f'    "{schema.CLUSTER}": [\n')

            pkgs = body.get(schema.CLUSTER, [])
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


def generate_configs_from_policy(
    input_dir: str,
    output_dir: str,
    policy_path: str = _DEFAULT_POLICY_PATH,
    schema_path: str = _DEFAULT_SCHEMA_PATH,
    *,
    log_file: Optional[str] = None,
    configure_logging: bool = False,
    log_level: int = logging.INFO,
) -> None:
    """Main function to generate adapter configs using adapter policy.

    Args:
        input_dir: Path to input directory (e.g., poc/milestone-1/out1/main)
        output_dir: Path to output directory (e.g., poc/milestone-1/out1/adapter/input/config)
        policy_path: Path to adapter policy JSON file
        schema_path: Path to adapter policy schema JSON file
        software_config_path: Optional path to software_config.json to copy to output
        log_file: Optional path to log file
        configure_logging: Whether to configure logging
        log_level: Logging level
    """
    if configure_logging:
        _configure_logging(log_file=log_file, log_level=log_level)

    _validate_input_policy_and_schema_paths(input_dir, policy_path, schema_path)

    policy_config = load_json_file(policy_path)
    schema_config = load_json_file(schema_path)
    validate_policy_config(policy_config, schema_config, policy_path=policy_path, schema_path=schema_path)
    targets = policy_config.get(schema.TARGETS, {})

    logger.info("Loaded %d target(s) from %s", len(targets), policy_path)

    # Discover architectures
    architectures = discover_architectures(input_dir)
    
    if not architectures:
        logger.warning("No architectures discovered under input directory: %s", input_dir)
        return
        
    logger.info("Discovered architectures: %s", architectures)

    all_arch_target_configs: Dict[str, Dict[str, Dict]] = {}
    resolved_os_family: Optional[str] = None
    resolved_os_version: Optional[str] = None

    for arch in architectures:
        os_versions = discover_os_versions(input_dir, arch)

        for os_family, version in os_versions:
            logger.info("Processing: arch=%s, os=%s, version=%s", arch, os_family, version)

            if resolved_os_family is None:
                resolved_os_family = os_family
                resolved_os_version = version

            source_dir = os.path.join(input_dir, arch, os_family, version)
            target_dir = os.path.join(output_dir, "input", "config", arch, os_family, version)

            if not os.path.isdir(source_dir):
                logger.warning("Source directory not found, skipping: %s", source_dir)
                continue

            source_files: Dict[str, Dict] = {}
            for filename in os.listdir(source_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(source_dir, filename)
                    source_files[filename] = load_json_file(file_path)
                    logger.debug("Loaded source file: %s", filename)

            target_configs: Dict[str, Dict] = {}

            for target_file, target_spec in targets.items():
                process_target_spec(
                    target_file=target_file,
                    target_spec=target_spec,
                    source_files=source_files,
                    target_configs=target_configs,
                    arch=arch,
                    os_family=os_family,
                    os_version=version
                )

            for target_file, data in target_configs.items():
                if data:
                    file_path = os.path.join(target_dir, target_file)
                    write_config_file(file_path, data)
                    logger.info("Written: %s", file_path)

            all_arch_target_configs[arch] = target_configs

    generate_software_config(
        output_dir=output_dir,
        os_family=resolved_os_family or "",
        os_version=resolved_os_version or "",
        all_arch_target_configs=all_arch_target_configs,
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate adapter configs from input JSONs using adapter policy"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Path to input directory containing source JSONs (e.g., out1/main)"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Path to output directory for generated configs (e.g., out1/adapter/input/config)"
    )
    parser.add_argument(
        "--policy",
        default=_DEFAULT_POLICY_PATH,
        help="Path to adapter policy JSON file"
    )
    parser.add_argument(
        "--schema",
        default=_DEFAULT_SCHEMA_PATH,
        help="Path to adapter policy schema JSON file"
    )
    parser.add_argument(
        "--log-file",
        required=False,
        default=None,
        help="Path to log file; if not set, logs go to stderr"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )

    args = parser.parse_args()

    _configure_logging(
        log_file=args.log_file,
        log_level=getattr(logging, args.log_level),
    )

    logger.info("Starting adapter policy generation")
    logger.info("Input directory: %s", args.input_dir)
    logger.info("Output directory: %s", args.output_dir)
    logger.info("Policy file: %s", args.policy)

    generate_configs_from_policy(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        policy_path=args.policy,
        schema_path=args.schema,
        configure_logging=False,
    )

    logger.info("Adapter config generation completed")


if __name__ == "__main__":
    main()
