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
from ansible.module_utils.input_validation.core.file_utils import load_json
from ansible.module_utils.input_validation.messages.common_messages import (
    CERTIFICATE_FILE_NOT_FOUND_MSG, KEY_FILE_NOT_FOUND_MSG,
    NO_REQUIRED_REPO_URLS_MSG, DUPLICATE_REPO_NAME_IN_ARCH_MSG,
    PRIORITY_MUST_BE_INTEGER_MSG, PRIORITY_MUST_BE_IN_RANGE_MSG,
    MISSING_REPO_CONFIGURATION_MSG
)


def validate(
    input_file_path, data, logger, _module, _omnia_base_dir, _module_utils_base, _project_name
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

    # Validate user_registry
    user_registry = data.get("user_registry")
    if user_registry:
        for registry in user_registry:
            cert_path = registry.get("cert_path")
            key_path = registry.get("key_path")

            if cert_path and not os.path.exists(cert_path):
                errors.append(create_error_msg(
                    repo_manager_config_yml, "user_registry",
                    f"{CERTIFICATE_FILE_NOT_FOUND_MSG}: {cert_path}"))

            if key_path and not os.path.exists(key_path):
                errors.append(create_error_msg(
                    repo_manager_config_yml, "user_registry",
                    f"{KEY_FILE_NOT_FOUND_MSG}: {key_path}"))

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

    # Get cluster_os_version from repo_manager_config.yml (catalog-based approach)
    cluster_os_version = data.get("cluster_os_version", "10.0")

    # Check for duplicate repo names using new collection method
    for arch in all_archs:
        repos_section = data.get("repositories", {}).get(cluster_os_version, {}).get(arch, {})
        names = _collect_all_repo_names(repos_section)

        # Add base subscription repos if subscription is active
        if sub_result:
            base_subscription_repos = ["baseos", "appstream", "codeready-builder"]
            names = names + base_subscription_repos

        # Check for duplicates
        seen = set()
        for name in names:
            if name in seen:
                errors.append(DUPLICATE_REPO_NAME_IN_ARCH_MSG.format(name=name, arch=arch))
            seen.add(name)

    # Note: Software-specific validations are now handled by catalog-based approach
    # The catalog JSON files define packages and their dependencies directly

    # Validate catalog package repository mapping
    catalog_errors = _validate_catalog_repo_mapping(
        data, cluster_os_version, all_archs, logger, omnia_base_dir
    )
    errors.extend(catalog_errors)

    # Validate catalog image registry mapping
    registry_errors = _validate_catalog_registry_mapping(
        data, logger, omnia_base_dir
    )
    errors.extend(registry_errors)

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
            if not isinstance(priority, int):
                errors.append(PRIORITY_MUST_BE_INTEGER_MSG.format(repo_path=repo_path))
            elif priority < 1 or priority > 100:
                errors.append(PRIORITY_MUST_BE_IN_RANGE_MSG.format(repo_path=repo_path))


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
                    if line.startswith("baseurl ="):
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


def _validate_catalog_repo_mapping(config_data, cluster_os_version, all_archs, logger, _omnia_base_dir):
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

    # Use unified catalog path resolution
    catalog_path = _get_catalog_path(logger)
    if not catalog_path or not os.path.exists(catalog_path):
        logger.warning("Catalog file not found, skipping repo mapping validation")
        return errors
    
    try:
        catalog = load_json(catalog_path)
        catalog_obj = catalog.get("catalog") or catalog.get("Catalog") or catalog
        packages = catalog_obj.get("packages") or catalog_obj.get("Packages") or {}
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as e:
        logger.warning(f"Failed to load catalog from {catalog_path}: {e}, skipping repo mapping validation")
        return errors

    # Collect all configured repositories per architecture
    configured_repos = {}
    for arch in all_archs:
        repos_section = config_data.get("repositories", {}).get(cluster_os_version, {}).get(arch, {})
        repo_names = _collect_all_repo_names(repos_section)
        configured_repos[arch] = set(repo_names)
    
    # Check each package's reponame against configured repositories
    missing_repos = {}
    for pkg_name, pkg_def in packages.items():
        sources = pkg_def.get("sources") or pkg_def.get("Sources") or []
        if not isinstance(sources, list):
            continue
        
        for source in sources:
            arch = source.get("architecture", "")
            reponame = source.get("reponame") or source.get("RepoName", "")
            
            if not reponame or not arch:
                continue
            
            # Skip if architecture not in our list
            if arch not in all_archs:
                continue
            
            # Check if reponame is configured
            if arch in configured_repos and reponame not in configured_repos[arch]:
                if reponame not in missing_repos:
                    missing_repos[reponame] = []
                missing_repos[reponame].append(arch)
    
    # Generate errors for missing repositories
    for reponame, archs in missing_repos.items():
        errors.append(
            MISSING_REPO_CONFIGURATION_MSG.format(
                reponame=reponame,
                archs=archs,
                cluster_os_version=cluster_os_version
            )
        )
    
    if errors:
        logger.error(f"Found {len(errors)} missing repository mappings in config")
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

    # Use unified catalog path resolution
    catalog_path = _get_catalog_path(logger)
    if not catalog_path or not os.path.exists(catalog_path):
        logger.warning("Catalog file not found, skipping registry mapping validation")
        return errors
    
    try:
        catalog = load_json(catalog_path)
        catalog_obj = catalog.get("catalog") or catalog.get("Catalog") or catalog
        packages = catalog_obj.get("packages") or catalog_obj.get("Packages") or {}
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as e:
        logger.warning(f"Failed to load catalog from {catalog_path}: {e}, skipping registry mapping validation")
        return errors

    # Public registries that don't require user registry configuration
    public_registries = {
        "docker.io",
        "ghcr.io",
        "quay.io",
        "registry.k8s.io",
        "nvcr.io",
        "public.ecr.aws",
        "gcr.io"
    }

    # Collect configured user registries
    configured_registries = set()
    registries_section = config_data.get("registries", {})
    if isinstance(registries_section, dict):
        configured_registries = set(registries_section.keys())

    # Check each image package's registry
    private_registries_missing = set()
    for pkg_name, pkg_def in packages.items():
        packagetype = pkg_def.get("packagetype") or pkg_def.get("PackageType", "")
        if packagetype != "image":
            continue

        sources = pkg_def.get("sources") or pkg_def.get("Sources") or []
        if not isinstance(sources, list):
            continue

        for source in sources:
            registry = source.get("registry") or source.get("Registry", "")

            if not registry:
                continue

            # Skip public registries
            if registry in public_registries:
                continue

            # Check if private registry is configured
            if registry not in configured_registries:
                private_registries_missing.add(registry)

    # Generate errors for missing private registry configurations
    for registry in sorted(private_registries_missing):
        errors.append(
            f"Catalog image references private registry '{registry}', "
            f"but this registry is not configured in repo_manager_config.yml under 'registries'. "
            f"Please add the registry configuration with BaseURL, Port, Auth, and TLS settings."
        )

    if errors:
        logger.error(f"Found {len(errors)} missing private registry configurations")
    else:
        logger.info("All catalog image registries are properly configured in repo_manager_config.yml")

    return errors
