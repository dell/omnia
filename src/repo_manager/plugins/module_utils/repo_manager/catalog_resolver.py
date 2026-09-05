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
# pylint:
# disable=import-error,line-too-long,no-name-in-module,too-many-branches,too-many-statements,too-many-locals,too-many-nested-blocks

"""
Multi-catalog resolver for repo_manager.

Handles:
- Discovery of catalog JSON files from a catalog directory
- Catalog validation and metadata extraction
- Global package index building with first-wins deduplication
- FunctionalLayer -> Groups -> Packages resolution
- Composite key hash-based change detection

All catalog keys are normalized to lowercase during loading.
"""

import os
import json
import hashlib
import copy
from collections import OrderedDict

from ansible.module_utils.repo_manager.config import DEFAULT_OS_TYPE
from ansible.module_utils.repo_manager.catalog_execution_context_resolver import (
    parse_functional_layer_context,
    resolve_catalog_execution_contexts,
)
from ansible.module_utils.repo_manager.platform_capability_registry import (
    get_platform_capabilities,
)
from ansible.module_utils.repo_manager.package_backend_registry import (
    get_package_backend,
)
from ansible.module_utils.repo_manager.software_utils import normalize_repo_name
from ansible.module_utils.repo_manager.security_utils import (
    ArtifactUrlValidationError,
    parse_python_requirement,
    validate_artifact_url,
    validate_repository_url,
)


class CatalogResolutionError(ValueError):
    """A catalog failure message that is safe to return through Ansible."""


# ---------------------------------------------------------------------------
# Catalog Discovery
# ---------------------------------------------------------------------------

def discover_catalogs(catalog_path, logger):
    """Discover all catalog JSON files from the specified directory.

    Args:
        catalog_path (str): Absolute path to catalog directory or single file.
        logger: Logger instance.

    Returns:
        list[str]: Sorted list of absolute paths to catalog JSON files.
    """
    if os.path.isfile(catalog_path) and catalog_path.endswith('.json'):
        logger.info("Single catalog file specified: %s", catalog_path)
        return [catalog_path]

    if not os.path.isdir(catalog_path):
        logger.error("Catalog path does not exist: %s", catalog_path)
        raise FileNotFoundError(f"Catalog path does not exist: {catalog_path}")

    catalog_files = sorted(
        os.path.join(catalog_path, f)
        for f in os.listdir(catalog_path)
        if f.endswith('.json') and os.path.isfile(os.path.join(catalog_path, f))
    )

    if not catalog_files:
        raise FileNotFoundError(f"No catalog JSON files found in: {catalog_path}")

    logger.info("Discovered %d catalog file(s): %s", len(catalog_files),
                [os.path.basename(f) for f in catalog_files])
    return catalog_files


# ---------------------------------------------------------------------------
# Catalog Loading & Validation (with lowercase key normalization)
# ---------------------------------------------------------------------------

def load_catalog(catalog_file, logger):
    """Load and validate a single catalog JSON file.

    All keys are normalized to lowercase during loading. Supports both
    uppercase (PascalCase) and lowercase keys in the source JSON.

    Args:
        catalog_file (str): Path to the catalog JSON file.
        logger: Logger instance.

    Returns:
        dict: Parsed catalog data with lowercase keys: identifier, name,
              version, functionallayer, groups, packages.

    Raises:
        ValueError: If required fields are missing.
    """
    logger.info("Loading catalog: %s", catalog_file)
    with open(catalog_file, 'r', encoding='utf-8') as fh:
        raw = json.load(fh)

    # Support both "Catalog" and "catalog" wrapper keys
    catalog = raw.get("Catalog") or raw.get("catalog") or raw

    # Build normalized dict with lowercase keys
    normalized = {
        "identifier": catalog.get("Identifier") or catalog.get("identifier", ""),
        "name": catalog.get("Name") or catalog.get("name", ""),
        "version": catalog.get("Version") or catalog.get("version", "1.0"),
        "description": catalog.get("Description") or catalog.get("description", ""),
        "functionallayer": catalog.get("FunctionalLayer") or catalog.get("functionallayer", []),
        "groups": catalog.get("Groups") or catalog.get("groups", {}),
        "packages": catalog.get("Packages") or catalog.get("packages", {}),
    }

    # Validate required fields
    if not normalized["identifier"] and not normalized["name"]:
        raise ValueError(
            f"Catalog {catalog_file} missing required fields: identifier or name")

    # Normalize FunctionalLayer items
    if normalized.get("functionallayer"):
        normalized_fl = []
        for layer in normalized["functionallayer"]:
            normalized_layer = {
                "name": layer.get("Name") or layer.get("name", ""),
                "components": layer.get("Components") or layer.get("components", [])
            }
            normalized_fl.append(normalized_layer)
        normalized["functionallayer"] = normalized_fl

    # Normalize Groups
    if normalized.get("groups"):
        normalized_groups = {}
        for group_key, group_val in normalized["groups"].items():
            normalized_group = {
                "name": group_val.get("Name") or group_val.get("name", ""),
                "type": group_val.get("Type") or group_val.get("type", ""),
                "components": group_val.get("Components") or group_val.get("components", []),
            }
            # Preserve optional fields
            for opt_field in ("os_version", "os", "description"):
                if opt_field in group_val:
                    normalized_group[opt_field] = group_val[opt_field]
            normalized_groups[group_key] = normalized_group
        normalized["groups"] = normalized_groups

    # Normalize Packages
    if normalized.get("packages"):
        normalized_packages = {}
        for pkg_key, pkg_val in normalized["packages"].items():
            normalized_pkg = {
                "name": pkg_val.get("Name") or pkg_val.get("name", ""),
                "packagetype": pkg_val.get("PackageType") or pkg_val.get("packageType") or pkg_val.get("packagetype", "")
            }
            # Preserve optional scalar fields
            for opt_field in ("tag", "version", "registry", "path", "url"):
                possible_keys = [opt_field.capitalize(), opt_field]
                if opt_field == "url":
                    possible_keys = ["URL", "Url", "url", "URI", "Uri", "uri"]
                val = next(
                    (pkg_val[key] for key in possible_keys if pkg_val.get(key) is not None),
                    None,
                )
                if val is not None:
                    if opt_field == "url" and str(val).strip():
                        val = validate_artifact_url(val)
                    normalized_pkg[opt_field] = val

            # Normalize Sources
            if "Sources" in pkg_val or "sources" in pkg_val:
                sources = pkg_val.get("Sources") or pkg_val.get("sources", [])
                normalized_sources = []
                for source in sources:
                    normalized_source = {}
                    source_fields = {
                        "architecture": ["Architecture", "architecture"],
                        "name": ["Name", "name"],
                        "version": ["Version", "version"],
                        "reponame": ["RepoName", "repoName", "reponame"],
                        "registry": ["Registry", "registry"],
                        "url": ["URL", "Url", "url", "URI", "Uri", "uri"],
                        "path": ["Path", "path"],
                    }
                    for norm_key, possible_keys in source_fields.items():
                        for key in possible_keys:
                            if key in source:
                                value = source[key]
                                if norm_key == "url" and str(value).strip():
                                    value = validate_artifact_url(value)
                                normalized_source[norm_key] = value
                                break
                    normalized_sources.append(normalized_source)
                normalized_pkg["sources"] = normalized_sources

            normalized_packages[pkg_key] = normalized_pkg
        normalized["packages"] = normalized_packages

    normalized["_source_file"] = catalog_file
    logger.info("Loaded catalog '%s' (identifier=%s, version=%s)",
                normalized["name"], normalized["identifier"], normalized["version"])
    return normalized


def load_multiple_catalogs(catalog_path, logger):
    """Discover and load all catalogs from a path.

    Args:
        catalog_path (str): Path to catalog directory or single catalog file.
        logger: Logger instance.

    Returns:
        list[dict]: List of validated catalog data dicts, in discovery order.
    """
    catalog_files = discover_catalogs(catalog_path, logger)
    catalogs = []
    failure_categories = set()
    for cf in catalog_files:
        try:
            catalog = load_catalog(cf, logger)
            catalogs.append(catalog)
        except json.JSONDecodeError:
            failure_category = "malformed JSON"
            failure_categories.add(failure_category)
            logger.error(
                "Skipping catalog %s: %s",
                os.path.basename(cf), failure_category,
            )
        except ArtifactUrlValidationError:
            failure_category = "invalid artifact URL"
            failure_categories.add(failure_category)
            logger.error(
                "Skipping catalog %s: %s",
                os.path.basename(cf), failure_category,
            )
        except ValueError:
            failure_category = "invalid catalog structure"
            failure_categories.add(failure_category)
            logger.error(
                "Skipping catalog %s: %s",
                os.path.basename(cf), failure_category,
            )

    if not catalogs:
        failure_summary = ", ".join(sorted(failure_categories))
        if not failure_summary:
            failure_summary = "no valid catalog content"
        raise CatalogResolutionError(
            f"Selected catalog could not be loaded ({failure_summary})"
        )

    logger.info("Successfully loaded %d catalog(s)", len(catalogs))
    return catalogs


# ---------------------------------------------------------------------------
# Composite Key Hashing
# ---------------------------------------------------------------------------

def compute_composite_key_hash(package_name, package_type, version, arch):
    """Compute a hash of the composite key for a package.

    Args:
        package_name (str): Package name.
        package_type (str): Package type (rpm, image, etc.).
        version (str): Package version (empty string if none).
        arch (str): Architecture.

    Returns:
        str: Hex digest of the SHA-256 hash.
    """
    composite = f"{package_name}|{package_type}|{version}|{arch}"
    return hashlib.sha256(composite.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Catalog Resolution: Groups -> Packages (lowercase keys)
# ---------------------------------------------------------------------------

def resolve_catalog_context(catalogs, logger):
    """Resolve ordered execution contexts and referenced RPM repositories."""
    context = resolve_catalog_execution_contexts(catalogs, logger)
    platform_capabilities = get_platform_capabilities(context["os_type"])
    get_package_backend(platform_capabilities["package_backend"])
    context["platform_capabilities"] = platform_capabilities
    for execution_context in context["execution_contexts"]:
        execution_context["platform_capabilities"] = platform_capabilities
        execution_context["referenced_repositories"] = (
            collect_referenced_repositories(catalogs, execution_context, logger)
        )

    if len(context["execution_contexts"]) == 1:
        context["referenced_repositories"] = context["execution_contexts"][0][
            "referenced_repositories"
        ]
    else:
        context["referenced_repositories_by_version"] = {
            item["os_version"]: item["referenced_repositories"]
            for item in context["execution_contexts"]
        }
    return context


def resolve_catalog_groups(catalog, arch, logger, os_version=None):
    """Resolve functionallayer -> groups -> packages for a given architecture.

    This extracts the group names referenced by functional layers that match
    the given architecture, then collects all packages from those groups.

    Args:
        catalog (dict): Parsed catalog data (lowercase keys).
        arch (str): Architecture to filter functional layers for.
        logger: Logger instance.

    Returns:
        dict: Mapping of group_name -> list of package entries.
    """
    if os_version is None:
        context = resolve_catalog_context([catalog], logger)
        if len(context["execution_contexts"]) != 1:
            raise ValueError(
                "os_version is required when a catalog contains multiple versions"
            )
        os_version = context["execution_contexts"][0]["os_version"]

    groups = catalog.get("groups", {})
    packages = catalog.get("packages", {})
    functional_layers = catalog.get("functionallayer", [])

    # Determine which groups apply to this architecture. Preserve catalog order
    # because global package deduplication intentionally uses first-wins.
    relevant_groups = []
    seen_groups = set()
    for fl in functional_layers:
        fl_name = fl.get("name", "")
        parsed_context = parse_functional_layer_context(fl_name)
        if (parsed_context["architecture"] == arch and
                parsed_context["os_version"] == str(os_version)):
            for component in fl.get("components", []):
                if component not in seen_groups:
                    relevant_groups.append(component)
                    seen_groups.add(component)

    # If no functional layers matched, skip this architecture
    if not relevant_groups:
        logger.info("No functional layers found for arch %s, skipping", arch)
        return {}

    logger.info("Resolved %d groups for arch %s: %s",
                len(relevant_groups), arch, list(relevant_groups))

    # Collect packages per group
    group_packages = {}
    for group_name in relevant_groups:
        group_def = groups.get(group_name, {})
        component_names = group_def.get("components", [])
        group_pkgs = []
        for comp_name in component_names:
            if comp_name in packages:
                pkg_entry = packages[comp_name]
                # Package entry might be a dict or nested structure
                if isinstance(pkg_entry, dict):
                    # Single package entry - prefer 'name' field over dict key
                    pkg_entry = copy.deepcopy(pkg_entry)
                    pkg_entry.setdefault("package", pkg_entry.get("name", comp_name))
                    group_pkgs.append(pkg_entry)
                elif isinstance(pkg_entry, list):
                    for p in pkg_entry:
                        p = copy.deepcopy(p)
                        p.setdefault("package", p.get("name", comp_name))
                        group_pkgs.append(p)
        if group_pkgs:
            group_packages[group_name] = group_pkgs

    logger.info("Resolved %d non-empty groups with packages for arch %s",
                len(group_packages), arch)
    return group_packages


def _source_supports_version(source, os_version):
    """Return whether a source is valid for the requested minor version."""
    if os_version is None:
        return True
    source_versions = source.get("version")
    if source_versions in (None, "", []):
        return True
    if not isinstance(source_versions, (list, tuple, set)):
        source_versions = [source_versions]
    return str(os_version) in {str(version) for version in source_versions}


def select_package_source(package, arch, os_version=None):
    """Return the source explicitly compatible with ``arch``.

    Exact architecture entries take priority.  A ``noarch`` source is accepted
    only when the catalog explicitly declares it; sources for another target
    architecture are never used implicitly.
    """
    sources = package.get("sources", [])
    if not isinstance(sources, list):
        return None

    for source in sources:
        if (source.get("architecture") == arch and
                _source_supports_version(source, os_version)):
            return source
    for source in sources:
        if (source.get("architecture") == "noarch" and
                _source_supports_version(source, os_version)):
            return source
    return None


def collect_referenced_repositories(catalogs, catalog_context, logger):
    """Return catalog-referenced RPM repository names per architecture.

    Only packages selected by the resolved functional layers participate. The
    result is deterministic and can be shared by validation and subscription
    setup so both phases require exactly the same repositories.
    """
    if isinstance(catalogs, dict):
        catalogs = [catalogs]

    os_version = catalog_context["os_version"]
    referenced = {
        architecture: []
        for architecture in catalog_context["architectures"]
    }
    seen = {architecture: set() for architecture in referenced}

    for catalog in catalogs:
        for architecture in catalog_context["architectures"]:
            group_packages = resolve_catalog_groups(
                catalog, architecture, logger, os_version=os_version
            )
            for packages in group_packages.values():
                for package in packages:
                    package_type = package.get(
                        "type", package.get("packagetype", "rpm")
                    )
                    if package_type not in ("rpm", "rpm_list", "rpm_repo"):
                        continue
                    source = select_package_source(
                        package, architecture, os_version=os_version
                    )
                    repo_name = (source or {}).get("reponame", "")
                    if repo_name and repo_name not in seen[architecture]:
                        referenced[architecture].append(repo_name)
                        seen[architecture].add(repo_name)

    logger.info("Catalog-referenced RPM repositories: %s", referenced)
    return referenced


# ---------------------------------------------------------------------------
# Global Package Index & Deduplication
# ---------------------------------------------------------------------------

def build_global_package_index(catalogs, logger, catalog_context=None):
    """Build a global package index with first-wins deduplication across catalogs.

    For each architecture, iterate through catalogs in discovery order. The first
    catalog to define a package (identified by composite key) wins. Subsequent
    catalogs referencing the same package just add their catalog name to the
    'catalogs' list.

    Args:
        catalogs (list[dict]): List of loaded catalog data (lowercase keys).
        logger: Logger instance.

    Returns:
        dict: {
            arch: {
                composite_key_hash: {
                    "package_name": str,
                    "type": str,
                    "version": str,
                    "arch": str,
                    "hash": str,
                    "catalog_name": str (first catalog),
                    "catalogs": list[str],
                    "source_catalog_file": str,
                    "group_name": str,
                    "repo_name": str,
                    "definition": dict (full package entry),
                }
            }
        }
    """
    catalog_context = catalog_context or resolve_catalog_context(catalogs, logger)
    if "os_version" not in catalog_context:
        raise ValueError(
            "A version-specific catalog_context is required when a catalog "
            "contains multiple OS versions"
        )
    os_version = catalog_context["os_version"]
    selected_architectures = catalog_context["architectures"]
    global_index = {}  # arch -> OrderedDict of hash -> info
    dedup_stats = {"total": 0, "unique": 0, "duplicates": 0, "dedup_list": {}}

    for catalog in catalogs:
        catalog_id = catalog["identifier"]

        for arch in selected_architectures:
            if arch not in global_index:
                global_index[arch] = OrderedDict()

            group_packages = resolve_catalog_groups(
                catalog, arch, logger, os_version=os_version
            )

            for group_name, pkg_list in group_packages.items():
                for pkg in pkg_list:
                    # All keys are lowercase after normalization
                    pkg_name = pkg.get("package", pkg.get("name", ""))
                    pkg_type = pkg.get("type", pkg.get("packagetype", "rpm"))
                    pkg_version = pkg.get("version", pkg.get("tag", ""))
                    if pkg_version is None:
                        pkg_version = ""
                    if pkg_type == "pip_module":
                        _pip_name, _pip_version, pkg_name = (
                            parse_python_requirement(pkg_name, pkg_version)
                        )
                        # The canonical requirement already contains the
                        # Python version. Keep the composite version empty so
                        # embedded and separately configured forms produce the
                        # same mirror identity and existing embedded pins keep
                        # their established hash.
                        pkg_version = ""
                        pkg["package"] = pkg_name

                    # Extract repo_name, url, and path from sources array for current arch
                    sources = pkg.get("sources", [])
                    repo_name = None
                    source_url = None
                    source_path = None
                    source_registry = None
                    selected_source = select_package_source(
                        pkg, arch, os_version=os_version
                    )
                    if sources and selected_source is None:
                        raise ValueError(
                            f"Catalog package '{pkg_name}' in group '{group_name}' "
                            f"has no source for architecture '{arch}' or 'noarch' "
                            f"compatible with {catalog_context['os_type']} {os_version}"
                        )
                    if selected_source:
                        repo_name = selected_source.get("reponame", "")
                        source_url = selected_source.get("url")
                        source_path = selected_source.get("path")
                        source_registry = selected_source.get("registry")
                        pkg["selected_source"] = copy.deepcopy(selected_source)

                    # Promote repo_name to package definition
                    if repo_name:
                        pkg["repo_name"] = repo_name
                    if source_registry:
                        pkg["source_registry"] = source_registry

                    # Promote url/path from sources to package definition for tarball/iso types
                    if source_url:
                        pkg["url"] = source_url
                        logger.debug("Promoted url from sources to package '%s' for arch '%s'",
                                     pkg_name, arch)
                    if source_path:
                        pkg["path"] = source_path
                        logger.debug("Promoted path from sources to package '%s' for arch '%s'",
                                     pkg_name, arch)

                    composite_hash = compute_composite_key_hash(
                        pkg_name, pkg_type, pkg_version, arch)

                    dedup_stats["total"] += 1

                    if composite_hash in global_index[arch]:
                        # Duplicate - just add catalog reference
                        existing = global_index[arch][composite_hash]
                        if catalog_id not in existing["catalogs"]:
                            existing["catalogs"].append(catalog_id)
                        dedup_stats["duplicates"] += 1
                        # Collect duplicate info for consolidated logging
                        if arch not in dedup_stats["dedup_list"]:
                            dedup_stats["dedup_list"][arch] = []
                        dedup_stats["dedup_list"][arch].append(f"{pkg_name} ({pkg_type})")
                    else:
                        # First occurrence - add to index
                        global_index[arch][composite_hash] = {
                            "package_name": pkg_name,
                            "type": pkg_type,
                            "version": pkg_version,
                            "arch": arch,
                            "hash": composite_hash,
                            "catalog_name": catalog_id,
                            "catalogs": [catalog_id],
                            "source_catalog_file": catalog.get("_source_file", ""),
                            "group_name": group_name,
                            "repo_name": repo_name or "",
                            "definition": pkg,
                        }
                        dedup_stats["unique"] += 1

    logger.info("Global package index built: total=%d, unique=%d, duplicates=%d",
                dedup_stats["total"], dedup_stats["unique"], dedup_stats["duplicates"])

    # Log consolidated duplicate list per architecture
    if dedup_stats["dedup_list"]:
        for arch, dup_packages in dedup_stats["dedup_list"].items():
            if dup_packages:
                unique_dups = sorted(set(dup_packages))
                logger.info("DEDUP summary for %s (%d duplicates): %s",
                            arch, len(dup_packages), ", ".join(unique_dups))

    return global_index


# ---------------------------------------------------------------------------
# Task List Generation from Global Index
# ---------------------------------------------------------------------------

def build_tasklist_from_index(global_index, arch, logger):
    """Build a task list from the global package index for a given architecture.

    Groups packages by their group_name and returns a dict suitable for
    consumption by transform_package_dict and the parallel execution framework.

    Args:
        global_index (dict): Output from build_global_package_index.
        arch (str): Architecture to build tasks for.
        logger: Logger instance.

    Returns:
        dict: group_name -> list of task dicts (package entries with type, package, etc.)
    """
    if arch not in global_index:
        logger.info("No packages found in global index for arch %s", arch)
        return {}

    tasks_by_group = {}
    for _hash, info in global_index[arch].items():
        group_name = info["group_name"]
        pkg_def = dict(info["definition"])

        # Normalize field names to lowercase for parallel_tasks compatibility
        if "type" not in pkg_def:
            pkg_def["type"] = pkg_def.get("packagetype", "rpm")
        if "package" not in pkg_def:
            pkg_def["package"] = pkg_def.get("name", info["package_name"])
        if "version" not in pkg_def:
            pkg_def["version"] = pkg_def.get("tag", "")
        # For container images, normalize tag
        if "tag" not in pkg_def and "tag" in info.get("definition", {}):
            pkg_def["tag"] = info["definition"]["tag"]

        # Ensure catalog_name is attached for status tracking
        pkg_def["catalog_name"] = info["catalog_name"]
        pkg_def["catalogs"] = info["catalogs"]

        if group_name not in tasks_by_group:
            tasks_by_group[group_name] = []
        tasks_by_group[group_name].append(pkg_def)

    logger.info("Built task list for arch %s: %d groups, %d total packages",
                arch, len(tasks_by_group),
                sum(len(v) for v in tasks_by_group.values()))
    return tasks_by_group


# ---------------------------------------------------------------------------
# Repo URL Extraction from New Config Format
# ---------------------------------------------------------------------------

def parse_repo_urls_from_config(config_data, repo_config_policy, arch, os_version, logger, global_caching_policy=True):
    """Parse repository URLs from the new repo_manager_config.yml format.

    The new config has:
        repositories:
          "10.0":
            x86_64:
              baseos: {url: ..., gpgkey: ...}
              appstream: {url: ..., gpgkey: ...}

    Args:
        config_data (dict): Loaded repo_manager_config.yml data.
        repo_config_policy (str): Global repo config policy (always/partial).
        arch (str): Architecture to extract repos for.
        os_version (str): OS version key (e.g., "10.0").
        logger: Logger instance.
        global_caching_policy (bool): Global caching policy from config (default: True).

    Returns:
        list[dict]: List of parsed repo entries with url, gpgkey, name, policy, etc.
    """
    repositories = config_data.get("repositories", {})
    version_repos = repositories.get(os_version, {})
    arch_repos = version_repos.get(arch, {})

    parsed = []
    for repo_name, repo_def in arch_repos.items():
        if repo_name in ("additional_repos", "user_repos"):
            # Additional and user repos handled separately
            continue
        if not isinstance(repo_def, dict):
            continue
        url = repo_def.get("url", "")
        if not url:
            # Empty repo definition (e.g., subscription repos)
            continue
        url = validate_repository_url(url)

        gpgkey = repo_def.get("gpgkey", "")
        policy = repo_def.get("policy", repo_config_policy)
        caching = repo_def.get("caching", global_caching_policy)
        sslcacert = repo_def.get("sslcacert", "")
        sslclientkey = repo_def.get("sslclientkey", "")
        sslclientcert = repo_def.get("sslclientcert", "")
        priority = repo_def.get("priority")

        parsed.append({
            "name": repo_name,
            "url": url,
            "gpgkey": gpgkey,
            "policy": policy,
            "caching": caching,
            "sslcacert": sslcacert,
            "sslclientkey": sslclientkey,
            "sslclientcert": sslclientcert,
            "priority": priority,
        })

    logger.info("Parsed %d repository entries for arch %s, version %s",
                len(parsed), arch, os_version)
    return parsed


def parse_additional_repos_from_config(config_data, repo_config_policy, arch,
                                       os_version, logger,
                                       global_caching_policy=True,
                                       os_type=None):
    """Parse additional_repos from the new repo_manager_config.yml format.

    Args:
        config_data (dict): Loaded repo_manager_config.yml data.
        repo_config_policy (str): Global repo config policy.
        arch (str): Architecture.
        os_version (str): OS version key.
        logger: Logger instance.
        global_caching_policy (bool): Global caching policy from config (default: True).

    Returns:
        list[dict]: List of additional repo entries.
    """
    repositories = config_data.get("repositories", {})
    version_repos = repositories.get(os_version, {})
    arch_repos = version_repos.get(arch, {})
    additional = arch_repos.get("additional_repos", {})

    if not additional or not isinstance(additional, dict):
        return []

    parsed = []
    for repo_name, repo_def in additional.items():
        if not isinstance(repo_def, dict):
            continue
        url = repo_def.get("url", "")
        if not url:
            continue
        url = validate_repository_url(url)

        # Normalize repo name to standard format
        normalized_name = normalize_repo_name(
            repo_name, arch, os_type or DEFAULT_OS_TYPE, os_version
        )

        parsed.append({
            "name": normalized_name,
            "original_name": repo_name,  # Keep original for reference
            "url": url,
            "gpgkey": repo_def.get("gpgkey", ""),
            "policy": repo_def.get("policy", repo_config_policy),
            "caching": repo_def.get("caching", global_caching_policy),
            "sslcacert": repo_def.get("sslcacert", ""),
            "sslclientkey": repo_def.get("sslclientkey", ""),
            "sslclientcert": repo_def.get("sslclientcert", ""),
            "priority": repo_def.get("priority"),
        })

    logger.info("Parsed %d additional repo entries for arch %s", len(parsed), arch)
    return parsed


def parse_user_repos_from_config(config_data, os_version, arch,
                                 repo_config_policy, logger,
                                 global_caching_policy=True,
                                 os_type=None):
    """Parse user custom repositories from repo_manager_config.yml user_repos section.

    Args:
        config_data: Parsed repo_manager_config.yml data
        os_version: OS version (e.g., "10.0")
        arch: Architecture (e.g., "x86_64")
        repo_config_policy: Default repo policy from config
        logger: Logger instance
        global_caching_policy (bool): Global caching policy from config (default: True).

    Returns:
        list: Parsed user repository entries
    """
    repositories = config_data.get("repositories", {})
    version_repos = repositories.get(os_version, {})
    arch_repos = version_repos.get(arch, {})
    user_repos = arch_repos.get("user_repos", {})

    if not user_repos or not isinstance(user_repos, dict):
        return []

    parsed = []
    for repo_name, repo_def in user_repos.items():
        if not isinstance(repo_def, dict):
            continue
        url = repo_def.get("url", "")
        if not url:
            continue
        url = validate_repository_url(url)

        # Normalize repo name to standard format
        normalized_name = normalize_repo_name(
            repo_name, arch, os_type or DEFAULT_OS_TYPE, os_version
        )

        parsed.append({
            "name": normalized_name,
            "original_name": repo_name,  # Keep original for reference
            "url": url,
            "gpgkey": repo_def.get("gpgkey", ""),
            "policy": repo_def.get("policy", repo_config_policy),
            "caching": repo_def.get("caching", global_caching_policy),
            "sslcacert": repo_def.get("sslcacert", ""),
            "sslclientkey": repo_def.get("sslclientkey", ""),
            "sslclientcert": repo_def.get("sslclientcert", ""),
            "priority": repo_def.get("priority"),
        })

    logger.info("Parsed %d user repo entries for arch %s", len(parsed), arch)
    return parsed


def parse_registries_from_config(config_data, logger):
    """Parse container registry configurations from repo_manager_config.yml.

    Args:
        config_data (dict): Loaded repo_manager_config.yml data.
        logger: Logger instance.

    Returns:
        dict: registry_name -> registry config dict.
    """
    registries = config_data.get("registries", {})
    if not registries:
        logger.info("No registries configured")
        return {}

    logger.info("Parsed %d registry entries", len(registries))
    return registries


# ---------------------------------------------------------------------------
# Config Loading Helper
# ---------------------------------------------------------------------------

def load_repo_manager_config(config_path, logger):
    """Load and parse the repo_manager_config.yml file.

    Args:
        config_path (str): Path to repo_manager_config.yml.
        logger: Logger instance.

    Returns:
        tuple: (config_data, is_catalog_based)
            config_data (dict): Parsed YAML data.
            is_catalog_based (bool): Always True (catalog-based is the only mode).
    """
    import yaml
    with open(config_path, 'r', encoding='utf-8') as fh:
        config_data = yaml.safe_load(fh) or {}

    logger.info("Loaded catalog-based configuration from %s", config_path)
    return config_data, True


def get_catalog_path(config_data, config_file_dir, logger):
    """Extract the catalog path.

    Reads from the CATALOG_FILE_PATH environment variable. Falls back to
    catalog_config.catalog in repo_manager_config.yml if the env var is not set.

    Args:
        config_data (dict): Parsed repo_manager_config.yml data.
        config_file_dir (str): Directory containing the config file.
        logger: Logger instance.

    Returns:
        str: Absolute path to the catalog file or directory.
    """
    # Prefer CATALOG_FILE_PATH environment variable
    catalog_env = os.environ.get("CATALOG_FILE_PATH", "")
    if catalog_env:
        catalog_path = os.path.abspath(catalog_env)
        logger.info("Using CATALOG_FILE_PATH env var: %s", catalog_path)
        return catalog_path

    # Fallback to catalog_config in config file
    catalog_config = config_data.get("catalog_config", {})
    catalog_ref = catalog_config.get("catalog", "")

    if not catalog_ref:
        raise ValueError(
            "CATALOG_FILE_PATH env var not set and catalog_config.catalog "
            "is not set in repo_manager_config.yml")

    # Resolve relative to config file directory
    if not os.path.isabs(catalog_ref):
        catalog_path = os.path.join(config_file_dir, catalog_ref)
    else:
        catalog_path = catalog_ref

    catalog_path = os.path.abspath(catalog_path)
    logger.info("Resolved catalog path from config: %s", catalog_path)
    return catalog_path


def get_repo_config_policy(config_data):
    """Extract the repo_config policy from config data.

    Args:
        config_data (dict): Parsed repo_manager_config.yml.

    Returns:
        str: Policy string ('partial' or 'always').
    """
    return config_data.get("repo_config", "partial")
