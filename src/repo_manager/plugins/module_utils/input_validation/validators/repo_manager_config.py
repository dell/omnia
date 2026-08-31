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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
"""
Repo manager configuration validator.

This module validates repo_manager_config.yml for:
- User registry configuration
- Repository URL validation
- Subscription status checking
- Catalog package repository mapping validation
- Catalog image registry mapping validation
"""
import os
import glob
import re
import json

from ansible.module_utils.input_validation.core.config import (
    files, SYSTEM_ENTITLEMENT_PATH, SYSTEM_REDHAT_REPO,
    CONTAINER_ENTITLEMENT_PATH, CONTAINER_REDHAT_REPO,
    OMNIA_ENTITLEMENT_PATH, OMNIA_REDHAT_REPO,
    CATALOG_DIR, CATALOG_FILE_PATH, OMNIA_BASE_DIR
)
from ansible.module_utils.input_validation.core.utils import create_error_msg, create_file_path
from ansible.module_utils.input_validation.messages.common_messages import (
    CERTIFICATE_FILE_NOT_FOUND_MSG, KEY_FILE_NOT_FOUND_MSG,
    NO_REQUIRED_REPO_URLS_MSG, DUPLICATE_REPO_NAME_IN_ARCH_MSG,
    PRIORITY_MUST_BE_INTEGER_MSG, PRIORITY_MUST_BE_IN_RANGE_MSG,
    ADDITIONAL_REPO_PRIORITY_CONFLICT_MSG,
    MISSING_REPO_CONFIGURATION_MSG, MISSING_REPO_URL_MSG,
    MISSING_ARCH_SOURCE_MSG, RPM_REPO_STREAMED_POLICY_MSG,
)
from ansible.module_utils.repo_manager.registry_utils import (
    PUBLIC_REGISTRY_URLS,
    build_registry_base_url,
)
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_multiple_catalogs,
    resolve_catalog_groups,
    select_package_source,
)
from ansible.module_utils.repo_manager.repo_settings import (
    DEFAULT_CACHING_POLICY,
    POLICY_CACHING_MAP,
)


def validate(
    input_file_path, data, logger, _module, omnia_base_dir, _module_utils_base, _project_name
):
    """
    Validates local repo configuration.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger: Logger instance.
        module: Ansible module instance.
        omnia_base_dir (str): The base directory of the Omnia configuration.
        module_utils_base (str): The base directory of the module utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    errors = []
    repo_manager_config_yml = create_file_path(input_file_path, files["repo_manager_config"])

    errors.extend(_validate_registry_configs(data, repo_manager_config_yml))

    # Validate caching_policy parameter
    caching_policy = data.get("caching_policy")
    if caching_policy is not None and not isinstance(caching_policy, bool):
        errors.append(create_error_msg(
            repo_manager_config_yml, "caching_policy",
            f"caching_policy must be a boolean, got {type(caching_policy).__name__}"
        ))

    # Collect repo names and check for duplicates
    sub_result = _check_subscription_status(logger)
    logger.info(f"validate_repo_manager_config: Subscription status: {sub_result}")

    all_archs = ['x86_64', 'aarch64']

    # Repository version keys are authoritative for Repo Manager.
    repository_versions = list((data.get("repositories") or {}).keys())
    cluster_os_version = repository_versions[0] if repository_versions else "10.0"

    # Check for duplicate repo names using new collection method
    for arch in all_archs:
        repos_section = data.get("repositories", {}).get(cluster_os_version, {}).get(arch, {})
        names = _collect_all_repo_names(repos_section)

        # Check for duplicates
        seen = set()
        for name in names:
            if name in seen:
                errors.append(DUPLICATE_REPO_NAME_IN_ARCH_MSG.format(name=name, arch=arch))
            seen.add(name)

        _validate_repo_priorities(
            repos_section, cluster_os_version, arch, errors
        )

    # Note: Software-specific validations are now handled by catalog-based approach
    # The catalog JSON files define packages and their dependencies directly

    # Validate catalog package repository mapping
    catalog_errors = _validate_catalog_repo_mapping(
        data, cluster_os_version, all_archs, logger, omnia_base_dir, sub_result
    )
    errors.extend(catalog_errors)

    # Validate catalog image registry mapping
    registry_errors = _validate_catalog_registry_mapping(
        data, logger, omnia_base_dir
    )
    errors.extend(registry_errors)

    return errors


def _validate_registry_configs(config_data, _config_path):
    """Validate registry URL, authentication references, and TLS paths."""
    errors = []
    vault_paths = {}
    registries = config_data.get("registries") or {}
    if not isinstance(registries, dict):
        return errors  # The JSON schema reports the type error.

    for registry_name, registry_config in registries.items():
        if not isinstance(registry_config, dict):
            continue  # The JSON schema reports the type error.
        try:
            build_registry_base_url(registry_config)
        except (TypeError, ValueError) as exc:
            errors.append(create_error_msg(
                f"registries.{registry_name}.base_url", registry_config.get("base_url", ""),
                str(exc)
            ))

        auth = registry_config.get("auth") or {}
        if not isinstance(auth, dict):
            continue  # The JSON schema reports the type error.
        if auth.get("type") == "basic":
            credentials_config = auth.get("credentials") or {}
            if not isinstance(credentials_config, dict):
                continue  # The JSON schema reports the type error.
            vault_path = credentials_config.get("vault_path", "")
            if vault_path in vault_paths:
                errors.append(create_error_msg(
                    f"registries.{registry_name}.auth.credentials.vault_path", vault_path,
                    f"vault_path is already used by registry '{vault_paths[vault_path]}'"
                ))
            elif vault_path:
                vault_paths[vault_path] = registry_name

        tls = registry_config.get("tls") or {}
        if not isinstance(tls, dict):
            continue  # The JSON schema reports the type error.
        client_cert = tls.get("client_cert_path") or ""
        client_key = tls.get("client_key_path") or ""
        if bool(client_cert) != bool(client_key):
            errors.append(create_error_msg(
                f"registries.{registry_name}.tls", registry_name,
                "client_cert_path and client_key_path must be configured together"
            ))

        for key, path, missing_message in (
            ("ca_path", tls.get("ca_path"), CERTIFICATE_FILE_NOT_FOUND_MSG),
            ("client_cert_path", client_cert, CERTIFICATE_FILE_NOT_FOUND_MSG),
            ("client_key_path", client_key, KEY_FILE_NOT_FOUND_MSG),
        ):
            if path and not os.path.isfile(path):
                errors.append(create_error_msg(
                    f"registries.{registry_name}.tls.{key}", path,
                    f"{missing_message}: {path}"
                ))

    return errors


def _collect_all_repo_names(repos_section):
    """
    Collect all repository names from both flat and nested structures.
    Handles additional_repos and user_repos as nested containers.
    """
    names = []
    for repo_name in repos_section:
        if repo_name in ("additional_repos", "user_repos"):
            nested = repos_section.get(repo_name, {}) or {}
            for nested_name in nested:
                names.append(nested_name)
        else:
            names.append(repo_name)
    return names


def _get_catalog_path(logger):
    """
    Get catalog path using consistent priority:
    1. CATALOG_FILE_PATH environment variable (primary)
    2. CATALOG_DIR discovery (fallback)
    3. Hardcoded fallback (last resort)
    
    Args:
        logger: Logger instance.
    
    Returns:
        str: Catalog file path or None if not found.
    """
    # Priority 1: CATALOG_FILE_PATH environment variable
    if CATALOG_FILE_PATH:
        if os.path.exists(CATALOG_FILE_PATH):
            logger.info("Using CATALOG_FILE_PATH env var: %s", CATALOG_FILE_PATH)
            return CATALOG_FILE_PATH
        logger.warning(f"CATALOG_FILE_PATH set but file not found: {CATALOG_FILE_PATH}")
    
    # Priority 2: CATALOG_DIR discovery
    if os.path.exists(CATALOG_DIR):
        catalog_files = glob.glob(os.path.join(CATALOG_DIR, "*.json"))
        if catalog_files:
            logger.info(f"Using discovered catalog from CATALOG_DIR: {catalog_files[0]}")
            return catalog_files[0]
        logger.warning(f"CATALOG_DIR exists but no JSON files found: {CATALOG_DIR}")
    else:
        logger.warning(f"CATALOG_DIR not found: {CATALOG_DIR}")
    
    # Priority 3: Hardcoded fallback
    catalog_path = os.path.join(OMNIA_BASE_DIR, "catalog", "catalog_rhel.json")
    logger.warning(f"Using fallback catalog path: {catalog_path}")
    return catalog_path


def _validate_priority(repo_config, repo_path, errors):
    """
    Validate priority field if present in repository configuration.
    """
    if repo_config and isinstance(repo_config, dict):
        priority = repo_config.get("priority")
        if priority is not None:
            if isinstance(priority, bool) or not isinstance(priority, int):
                errors.append(PRIORITY_MUST_BE_INTEGER_MSG.format(repo_path=repo_path))
            elif priority < 1 or priority > 100:
                errors.append(PRIORITY_MUST_BE_IN_RANGE_MSG.format(repo_path=repo_path))


def _validate_repo_priorities(repos_section, cluster_os_version, arch, errors):
    """Validate all priority fields and the aggregated additional-repo contract."""
    base_path = f"repositories.{cluster_os_version}.{arch}"
    for repo_name, repo_config in (repos_section or {}).items():
        repo_path = f"{base_path}.{repo_name}"
        if repo_name in ("additional_repos", "user_repos"):
            if not isinstance(repo_config, dict):
                continue
            for nested_name, nested_config in repo_config.items():
                _validate_priority(
                    nested_config, f"{repo_path}.{nested_name}", errors
                )
        else:
            _validate_priority(repo_config, repo_path, errors)

    additional_repos = (repos_section or {}).get("additional_repos") or {}
    if not isinstance(additional_repos, dict):
        return

    effective_priorities = set()
    for repo_config in additional_repos.values():
        if not isinstance(repo_config, dict):
            continue
        if not str(repo_config.get("url") or "").strip():
            continue
        priority = repo_config.get("priority")
        if priority is None:
            effective_priorities.add(99)
        elif (not isinstance(priority, bool) and isinstance(priority, int)
              and 1 <= priority <= 100):
            effective_priorities.add(priority)

    if len(effective_priorities) > 1:
        errors.append(ADDITIONAL_REPO_PRIORITY_CONFLICT_MSG.format(
            repo_path=f"{base_path}.additional_repos",
            priorities=", ".join(
                str(value) for value in sorted(effective_priorities)
            ),
        ))


def _check_subscription_status(logger=None):
    """
    Check if the system has an active Red Hat subscription enabled.

    Returns:
        bool: True if subscription is enabled, False otherwise.
    """
    # Check all possible entitlement certificate locations
    entitlement_paths = [
        (SYSTEM_ENTITLEMENT_PATH, SYSTEM_REDHAT_REPO),
        (CONTAINER_ENTITLEMENT_PATH, CONTAINER_REDHAT_REPO),
        (OMNIA_ENTITLEMENT_PATH, OMNIA_REDHAT_REPO),
    ]

    has_entitlement = False
    entitlement_certs = []
    repo_file_to_check = None

    for entitlement_path, repo_path in entitlement_paths:
        entitlement_certs = glob.glob(entitlement_path)
        has_entitlement = len(entitlement_certs) > 0
        if has_entitlement:
            repo_file_to_check = repo_path
            if logger:
                logger.info(
                    f"Found {len(entitlement_certs)} entitlement certs at {entitlement_path}"
                )
            break
    else:
        if logger:
            logger.info("No entitlement certs found in any known location")

    # Check repos
    has_repos = False
    repo_urls = []
    redhat_repo_used = None

    if repo_file_to_check and os.path.exists(repo_file_to_check):
        try:
            with open(repo_file_to_check, "r", encoding="utf-8") as f:
                for line in f:
                    if re.match(r"^\s*baseurl\s*=", line):
                        url = line.split("=", 1)[1].strip()
                        if re.search(r"(codeready-builder|baseos|appstream)", url, re.IGNORECASE):
                            repo_urls.append(url)

            if repo_urls:
                has_repos = True
                redhat_repo_used = repo_file_to_check
                if logger:
                    logger.info(f"Found {len(repo_urls)} repo URLs in {repo_file_to_check}")
            elif logger:
                logger.info(f"{NO_REQUIRED_REPO_URLS_MSG} in {repo_file_to_check}")
        except (IOError, OSError) as e:
            if logger:
                logger.warning(f"Error reading {repo_file_to_check}: {e}")
    elif logger:
        logger.info(f"Repo file {repo_file_to_check} does not exist")

    subscription_enabled = has_entitlement and has_repos

    if logger:
        logger.info(
            f"Subscription enabled: {subscription_enabled} "
            f"(entitlement={has_entitlement}, repos={has_repos}, "
            f"entitlement_source={entitlement_certs[0] if entitlement_certs else 'None'}, "
            f"repo_source={redhat_repo_used})"
        )

    return subscription_enabled


def _load_catalogs_for_validation(logger):
    """Load catalogs through the same normalization path used at runtime."""
    catalog_path = _get_catalog_path(logger)
    if not catalog_path or not os.path.exists(catalog_path):
        return catalog_path, None, create_error_msg(
            "catalog", catalog_path or "",
            "Catalog file was not found; catalog mapping validation cannot continue"
        )
    try:
        return catalog_path, load_multiple_catalogs(catalog_path, logger), None
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        return catalog_path, None, create_error_msg(
            "catalog", catalog_path,
            f"Failed to load catalog for mapping validation: {exc}"
        )


def _iter_selected_packages(catalogs, all_archs, logger):
    """Yield each unique package selected by a functional layer and architecture."""
    seen = set()
    for catalog in catalogs:
        for arch in all_archs:
            for group_name, packages in resolve_catalog_groups(
                    catalog, arch, logger).items():
                for package in packages:
                    package_name = package.get("package", package.get("name", ""))
                    package_type = package.get(
                        "type", package.get("packagetype", "rpm")
                    )
                    version = package.get("version", package.get("tag", "")) or ""
                    identity = (catalog.get("identifier", ""), arch,
                                package_name, package_type, str(version))
                    if identity in seen:
                        continue
                    seen.add(identity)
                    yield {
                        "catalog": catalog,
                        "arch": arch,
                        "group_name": group_name,
                        "package_name": package_name,
                        "package_type": package_type,
                        "version": version,
                        "definition": package,
                        "source": select_package_source(package, arch),
                    }


def _collect_repo_configs(repos_section):
    """Return repository name to configuration mappings for one architecture."""
    configs = {}
    for repo_name, repo_config in (repos_section or {}).items():
        if repo_name in ("additional_repos", "user_repos"):
            for nested_name, nested_config in (repo_config or {}).items():
                configs[nested_name] = nested_config or {}
        else:
            configs[repo_name] = repo_config or {}
    return configs


def _effective_repo_download_policy(config_data, repo_config):
    """Resolve the Pulp policy using the same per-repo/global precedence as runtime."""
    repo_config = repo_config if isinstance(repo_config, dict) else {}
    policy = str(
        repo_config.get("policy", config_data.get("repo_config", "partial"))
    ).lower()
    caching = repo_config.get(
        "caching", config_data.get("caching_policy", DEFAULT_CACHING_POLICY)
    )
    if not isinstance(caching, bool):
        return None  # The schema/type validation reports this independently.
    return POLICY_CACHING_MAP.get((policy, caching), "on_demand")


def _validate_catalog_repo_mapping(config_data, cluster_os_version, all_archs,
                                   logger, _omnia_base_dir,
                                   subscription_enabled=False):
    """
    Validate that all catalog package reponame entries have corresponding repositories
    in repo_manager_config.yml.

    Args:
        config_data (dict): Parsed repo_manager_config.yml data.
        cluster_os_version (str): OS version (e.g., "10.0").
        all_archs (list): List of architectures to validate.
        logger: Logger instance.
        _omnia_base_dir (str): Base directory for catalog path (unused).

    Returns:
        list: List of error messages.
    """
    errors = []
    _catalog_path, catalogs, load_error = _load_catalogs_for_validation(logger)
    if load_error:
        return [load_error]

    configured_repos = {}
    for arch in all_archs:
        repos_section = (
            config_data.get("repositories", {})
            .get(cluster_os_version, {})
            .get(arch, {})
        )
        configured_repos[arch] = _collect_repo_configs(repos_section)

    base_subscription_repos = {"baseos", "appstream", "codeready-builder"}
    missing_sources = set()
    missing_mappings = set()
    missing_urls = set()
    streamed_rpm_repos = set()

    for selected in _iter_selected_packages(catalogs, all_archs, logger):
        arch = selected["arch"]
        package_name = selected["package_name"]
        package_type = selected["package_type"]
        source = selected["source"]
        if source is None:
            missing_sources.add((package_name, arch))
            continue

        if package_type not in ("rpm", "rpm_repo"):
            continue
        reponame = source.get("reponame", "")
        if not reponame:
            missing_mappings.add(("<missing reponame>", arch))
            continue

        repo_config = configured_repos.get(arch, {}).get(reponame)
        subscription_provides_repo = (
            subscription_enabled and reponame in base_subscription_repos
        )

        # Subscription supplies only these three RHEL repositories. Every other
        # selected source still requires a configured, non-empty URL.
        if not subscription_provides_repo:
            if repo_config is None:
                missing_mappings.add((reponame, arch))
                continue
            if not str(repo_config.get("url") or "").strip():
                missing_urls.add((reponame, arch))
                continue

        if (package_type == "rpm_repo"
                and _effective_repo_download_policy(
                    config_data, repo_config or {}
                ) == "streamed"):
            streamed_rpm_repos.add((package_name, reponame, arch))

    for package_name, arch in sorted(missing_sources):
        errors.append(create_error_msg(
            "catalog.sources", package_name,
            MISSING_ARCH_SOURCE_MSG.format(
                package_name=package_name, arch=arch
            )
        ))

    for reponame, arch in sorted(missing_mappings):
        errors.append(create_error_msg(
            "repositories", reponame,
            MISSING_REPO_CONFIGURATION_MSG.format(
                reponame=reponame,
                archs=[arch],
                cluster_os_version=cluster_os_version
            )
        ))

    for reponame, arch in sorted(missing_urls):
        errors.append(create_error_msg(
            "repositories", reponame,
            MISSING_REPO_URL_MSG.format(
                reponame=reponame, arch=arch,
                cluster_os_version=cluster_os_version
            )
        ))

    for package_name, reponame, arch in sorted(streamed_rpm_repos):
        errors.append(create_error_msg(
            "repositories", reponame,
            RPM_REPO_STREAMED_POLICY_MSG.format(
                package_name=package_name,
                reponame=reponame,
                arch=arch,
            )
        ))
    
    if errors:
        logger.error("Found %d catalog repository validation error(s)", len(errors))
    else:
        logger.info("All catalog package repositories are configured in repo_manager_config.yml")
    
    return errors


def _validate_catalog_registry_mapping(config_data, logger, _omnia_base_dir):
    """
    Validate that all catalog image registry entries have corresponding user registry
    details in repo_manager_config.yml (for private registries only).

    Public registries (docker.io, ghcr.io, quay.io, registry.k8s.io) are allowed
    without user registry configuration.

    Args:
        config_data (dict): Parsed repo_manager_config.yml data.
        logger: Logger instance.
        _omnia_base_dir (str): Base directory for catalog path (unused).

    Returns:
        list: List of error messages.
    """
    errors = []
    _catalog_path, catalogs, load_error = _load_catalogs_for_validation(logger)
    if load_error:
        return [load_error]

    # Collect configured user registries
    configured_registries = set()
    registries_section = config_data.get("registries", {})
    if isinstance(registries_section, dict):
        configured_registries = set(registries_section.keys())

    # Check each image package's registry
    private_registries_missing = {}
    invalid_image_mappings = []
    seen_images = set()
    for selected in _iter_selected_packages(catalogs, ['x86_64', 'aarch64'], logger):
        if selected["package_type"] != "image" or selected["source"] is None:
            continue
        pkg_name = selected["package_name"]
        image_name = selected["definition"].get("name", pkg_name)
        registry = selected["source"].get("registry", "")
        image_identity = (image_name, registry)
        if image_identity in seen_images:
            continue
        seen_images.add(image_identity)

        if not registry:
            invalid_image_mappings.append(create_error_msg(
                f"catalog.packages.{pkg_name}.sources.registry", "",
                "Image sources must define a registry"
            ))
            continue

        if not image_name.startswith(f"{registry}/"):
            invalid_image_mappings.append(create_error_msg(
                f"catalog.packages.{pkg_name}.name", image_name,
                f"Image name must start with catalog registry '{registry}/'"
            ))

        if registry in PUBLIC_REGISTRY_URLS:
            continue

        if registry not in configured_registries:
            private_registries_missing.setdefault(registry, []).append(pkg_name)

    # Generate errors for missing private registry configurations
    errors.extend(invalid_image_mappings)
    for registry, package_names in sorted(private_registries_missing.items()):
        errors.append(create_error_msg(
            "registries", registry,
            f"Catalog package(s) {sorted(set(package_names))} reference private registry "
            f"'{registry}', but it is not configured under registries"
        ))

    if errors:
        logger.error(f"Found {len(errors)} missing private registry configurations")
    else:
        logger.info(
            "All catalog image registries are properly configured in "
            "repo_manager_config.yml"
        )

    return errors
