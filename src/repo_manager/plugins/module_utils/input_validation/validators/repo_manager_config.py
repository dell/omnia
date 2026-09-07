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
Repo Manager configuration validator.

This module validates repo_manager_config.yml for:
- User registry configuration
- Catalog-scoped repository URL validation
- Shared subscription-status consumption
- Catalog package repository mapping validation
- Catalog image registry mapping validation
"""
import os
import json

from ansible.module_utils.input_validation.core.config import (
    files, CATALOG_FILE_PATH
)
from ansible.module_utils.input_validation.core.utils import create_error_msg, create_file_path
from ansible.module_utils.input_validation.messages.common_messages import (
    CERTIFICATE_FILE_NOT_FOUND_MSG, KEY_FILE_NOT_FOUND_MSG,
    DUPLICATE_REPO_NAME_IN_ARCH_MSG,
    PRIORITY_MUST_BE_INTEGER_MSG, PRIORITY_MUST_BE_IN_RANGE_MSG,
    ADDITIONAL_REPO_PRIORITY_CONFLICT_MSG,
    MISSING_REPO_CONFIGURATION_MSG, MISSING_REPO_URL_MSG,
    MISSING_ARCH_SOURCE_MSG, RPM_REPO_STREAMED_POLICY_MSG,
)
from ansible.module_utils.repo_manager.registry_utils import (
    PUBLIC_REGISTRY_URLS,
    get_image_path_for_registry,
    get_registry_authority,
)
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_multiple_catalogs,
    resolve_catalog_context,
    resolve_catalog_groups,
    select_package_source,
)
from ansible.module_utils.repo_manager.repo_settings import (
    DEFAULT_CACHING_POLICY,
    POLICY_CACHING_MAP,
    SUBSCRIPTION_REPOSITORIES,
    iterate_all_repos,
)
from ansible.module_utils.repo_manager.security_utils import (
    redact_url_credentials,
    validate_repository_url,
)


def validate(
    input_file_path, data, logger, module, omnia_base_dir,
    _module_utils_base, _project_name
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

    # Load catalog content for source validation, but consume the execution
    # contexts and subscription decision already resolved by orchestration.
    # Validation must never perform a second subscription check.
    _catalog_path, catalogs, load_error = _load_catalogs_for_validation(logger)
    if load_error:
        errors.append(load_error)
        return errors
    module_params = getattr(module, "params", {}) or {}
    execution_contexts = module_params.get("catalog_execution_contexts")
    subscription_enabled = module_params.get("subscription_enabled")
    if not isinstance(execution_contexts, list) or not execution_contexts:
        errors.append(create_error_msg(
            "catalog_execution_contexts", "",
            "Resolved catalog execution contexts were not provided"
        ))
        return errors
    if not isinstance(subscription_enabled, bool):
        errors.append(create_error_msg(
            "subscription_enabled", "",
            "Resolved subscription status was not provided"
        ))
        return errors
    for execution_context in execution_contexts:
        if (not isinstance(execution_context, dict)
                or not isinstance(
                    execution_context.get("referenced_repositories"), dict
                )):
            errors.append(create_error_msg(
                "catalog_execution_contexts", "",
                "Resolved catalog repository mapping was not provided"
            ))
            return errors

    repositories = data.get("repositories") or {}
    logger.info(
        "validate_repo_manager_config: Using shared subscription status: %s",
        subscription_enabled,
    )

    for execution_context in execution_contexts:
        cluster_os_version = execution_context["os_version"]
        selected_architectures = execution_context["architectures"]

        if cluster_os_version not in repositories:
            errors.append(create_error_msg(
                "repositories", cluster_os_version,
                "Catalog OS version is not configured under repositories"
            ))

        for arch in selected_architectures:
            repos_section = (
                repositories.get(cluster_os_version, {}).get(arch, {})
            )
            referenced_repo_names = set(
                execution_context["referenced_repositories"].get(arch, [])
            )
            names = [
                name for name in _collect_all_repo_names(repos_section)
                if name in referenced_repo_names
            ]
            seen = set()
            for name in names:
                if name in seen:
                    errors.append(
                        DUPLICATE_REPO_NAME_IN_ARCH_MSG.format(
                            name=name, arch=arch
                        )
                    )
                seen.add(name)

            _validate_repo_priorities(
                repos_section, cluster_os_version, arch, errors,
                referenced_repo_names=referenced_repo_names,
            )

        errors.extend(_validate_catalog_repo_mapping(
            data, cluster_os_version, selected_architectures, logger,
            omnia_base_dir, subscription_enabled, catalogs=catalogs,
            referenced_repositories=execution_context.get(
                "referenced_repositories", {}
            )
        ))

    # Registry mappings can differ by context, so validate the complete ordered
    # context list once while de-duplicating repeated image identities.
    errors.extend(_validate_catalog_registry_mapping(
        data, logger, omnia_base_dir, catalogs=catalogs,
        catalog_context={"execution_contexts": execution_contexts}
    ))

    return errors


def _validate_registry_configs(config_data, _config_path):
    """Validate registry URL, authentication references, and TLS paths."""
    errors = []
    vault_paths = {}
    registry_authorities = {}
    registries = config_data.get("registries") or {}
    if not isinstance(registries, dict):
        return errors  # The JSON schema reports the type error.

    for registry_name, registry_config in registries.items():
        if not isinstance(registry_config, dict):
            continue  # The JSON schema reports the type error.
        try:
            authority = get_registry_authority(registry_config)
            authority_key = authority.lower()
            if authority_key in registry_authorities:
                errors.append(create_error_msg(
                    f"registries.{registry_name}.base_url",
                    registry_config.get("base_url", ""),
                    "Registry endpoint is already configured by registry "
                    f"'{registry_authorities[authority_key]}'"
                ))
            else:
                registry_authorities[authority_key] = registry_name
        except (TypeError, ValueError) as exc:
            safe_base_url = redact_url_credentials(
                registry_config.get("base_url", "")
            )
            errors.append(create_error_msg(
                f"registries.{registry_name}.base_url", safe_base_url,
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
                    f"registries.{registry_name}.tls.{key}", "<configured path>",
                    f"{missing_message}: configured path does not exist"
                ))

    return errors


def _validate_repository_urls(config_data, os_version=None,
                              architectures=None,
                              referenced_repositories=None):
    """Reject unsafe RPM URLs within the requested catalog scope.

    Omitting the optional scope retains the all-repository utility behavior
    used by direct security tests. Production validation always supplies the
    catalog version, selected architectures and referenced repository map.
    """
    errors = []
    repositories = config_data.get("repositories") or {}
    if not isinstance(repositories, dict):
        return errors

    version_items = repositories.items()
    if os_version is not None:
        version_items = [(os_version, repositories.get(os_version, {}))]

    selected_architectures = (
        set(architectures) if architectures is not None else None
    )
    for version, version_repositories in version_items:
        if not isinstance(version_repositories, dict):
            continue
        for arch, repositories_for_arch in version_repositories.items():
            if (selected_architectures is not None
                    and arch not in selected_architectures):
                continue
            if not isinstance(repositories_for_arch, dict):
                continue
            for repo_name, repo_config in iterate_all_repos(
                    repositories_for_arch):
                if (referenced_repositories is not None
                        and repo_name not in referenced_repositories.get(
                            arch, [])):
                    continue
                if not isinstance(repo_config, dict):
                    continue
                url = repo_config.get("url")
                if not url or not isinstance(url, str):
                    continue
                try:
                    validate_repository_url(url)
                except ValueError as error:
                    errors.append(create_error_msg(
                        f"repositories.{version}.{arch}.{repo_name}.url",
                        "<redacted URL>",
                        str(error),
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
    Return the exact catalog selected for this Repo Manager execution.

    Args:
        logger: Logger instance.

    Returns:
        str: Catalog file path or None if not found.
    """
    if CATALOG_FILE_PATH:
        if os.path.exists(CATALOG_FILE_PATH):
            logger.info("Using CATALOG_FILE_PATH env var: %s", CATALOG_FILE_PATH)
            return CATALOG_FILE_PATH
        logger.warning(f"CATALOG_FILE_PATH set but file not found: {CATALOG_FILE_PATH}")

    return None


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


def _validate_repo_priorities(repos_section, cluster_os_version, arch, errors,
                              referenced_repo_names=None):
    """Validate priorities for the selected catalog repository scope."""
    base_path = f"repositories.{cluster_os_version}.{arch}"
    referenced = (
        set(referenced_repo_names)
        if referenced_repo_names is not None else None
    )
    for repo_name, repo_config in (repos_section or {}).items():
        repo_path = f"{base_path}.{repo_name}"
        if repo_name in ("additional_repos", "user_repos"):
            if not isinstance(repo_config, dict):
                continue
            for nested_name, nested_config in repo_config.items():
                if referenced is not None and nested_name not in referenced:
                    continue
                _validate_priority(
                    nested_config, f"{repo_path}.{nested_name}", errors
                )
        elif referenced is not None and repo_name not in referenced:
            continue
        else:
            _validate_priority(repo_config, repo_path, errors)

    additional_repos = (repos_section or {}).get("additional_repos") or {}
    if not isinstance(additional_repos, dict):
        return

    effective_priorities = set()
    for repo_name, repo_config in additional_repos.items():
        if referenced is not None and repo_name not in referenced:
            continue
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


def _iter_selected_packages(catalogs, all_archs, logger, os_version=None):
    """Yield each unique package selected by a functional layer and architecture."""
    seen = set()
    for catalog in catalogs:
        for arch in all_archs:
            for group_name, packages in resolve_catalog_groups(
                    catalog, arch, logger, os_version=os_version).items():
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
                        "source": select_package_source(
                            package, arch, os_version=os_version
                        ),
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
                                   subscription_enabled=False, catalogs=None,
                                   referenced_repositories=None):
    """
    Validate that all catalog package reponame entries have corresponding repositories
    in repo_manager_config.yml.

    Args:
        config_data (dict): Parsed repo_manager_config.yml data.
        cluster_os_version (str): OS version (e.g., "10.0").
        all_archs (list): List of architectures to validate.
        logger: Logger instance.
        _omnia_base_dir (str): Base directory for catalog path (unused).
        subscription_enabled (bool): Shared subscription decision.
        catalogs (list): Loaded catalog documents.
        referenced_repositories (dict): Authoritative catalog-selected
            repository names by architecture. When omitted, names are derived
            for direct helper compatibility.

    Returns:
        list: List of error messages.
    """
    errors = []
    if catalogs is None:
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

    base_subscription_repos = set(SUBSCRIPTION_REPOSITORIES)
    selected_repos_by_arch = {
        arch: set((referenced_repositories or {}).get(arch, []))
        for arch in all_archs
    }
    missing_sources = set()
    missing_mappings = set()
    missing_urls = set()
    streamed_rpm_repos = set()

    for selected in _iter_selected_packages(
            catalogs, all_archs, logger, os_version=cluster_os_version):
        arch = selected["arch"]
        package_name = selected["package_name"]
        package_type = selected["package_type"]
        source = selected["source"]
        if source is None:
            missing_sources.add((package_name, arch))
            continue

        if package_type not in ("rpm", "rpm_list", "rpm_repo"):
            continue
        reponame = source.get("reponame", "")
        if not reponame:
            missing_mappings.add(("<missing reponame>", arch))
            continue

        if referenced_repositories is None:
            selected_repos_by_arch[arch].add(reponame)

        repo_config = configured_repos.get(arch, {}).get(reponame)

        if (package_type == "rpm_repo"
                and _effective_repo_download_policy(
                    config_data, repo_config or {}
                ) == "streamed"):
            streamed_rpm_repos.add((package_name, reponame, arch))

    # Apply mapping and URL rules once per referenced repository. In
    # non-subscription mode every selected RPM repository, including BaseOS,
    # AppStream and CodeReady Builder, requires an explicit URL. Subscription
    # mode exempts only those exact three names when discovery will supply them.
    for arch in all_archs:
        for reponame in sorted(selected_repos_by_arch.get(arch, set())):
            repo_config = configured_repos.get(arch, {}).get(reponame)
            subscription_provides_repo = (
                subscription_enabled and reponame in base_subscription_repos
            )
            if repo_config is None:
                if not subscription_provides_repo:
                    missing_mappings.add((reponame, arch))
                continue
            if not isinstance(repo_config, dict):
                missing_urls.add((reponame, arch))
                continue

            url = repo_config.get("url")
            if not str(url or "").strip():
                if not subscription_provides_repo:
                    missing_urls.add((reponame, arch))
                continue

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

    errors.extend(_validate_repository_urls(
        config_data,
        os_version=cluster_os_version,
        architectures=all_archs,
        referenced_repositories=selected_repos_by_arch,
    ))

    if errors:
        logger.error("Found %d catalog repository validation error(s)", len(errors))
    else:
        logger.info("All catalog package repositories are configured in repo_manager_config.yml")

    return errors


def _validate_catalog_registry_mapping(config_data, logger, _omnia_base_dir,
                                       catalogs=None, catalog_context=None):
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
    if catalogs is None:
        _catalog_path, catalogs, load_error = _load_catalogs_for_validation(logger)
        if load_error:
            return [load_error]
    if catalog_context is None:
        try:
            catalog_context = resolve_catalog_context(catalogs, logger)
        except ValueError as exc:
            return [create_error_msg("catalog.functionallayer", "", str(exc))]

    # Collect configured user registries.
    configured_registries = {}
    registries_section = config_data.get("registries", {})
    if isinstance(registries_section, dict):
        configured_registries = registries_section

    # Check each image package's registry
    private_registries_missing = {}
    invalid_image_mappings = []
    seen_images = set()
    execution_contexts = catalog_context.get(
        "execution_contexts", [catalog_context]
    )
    for execution_context in execution_contexts:
        for selected in _iter_selected_packages(
                catalogs, execution_context["architectures"], logger,
                os_version=execution_context["os_version"]):
            if (selected["package_type"] != "image"
                    or selected["source"] is None):
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

            if registry in PUBLIC_REGISTRY_URLS:
                if not image_name.startswith(f"{registry}/"):
                    invalid_image_mappings.append(create_error_msg(
                        f"catalog.packages.{pkg_name}.name", image_name,
                        f"Image name must start with public registry '{registry}/'"
                    ))
                continue

            if registry not in configured_registries:
                private_registries_missing.setdefault(
                    registry, []
                ).append(pkg_name)
                continue

            try:
                get_image_path_for_registry(
                    image_name, registry, configured_registries[registry]
                )
            except (TypeError, ValueError) as exc:
                invalid_image_mappings.append(create_error_msg(
                    f"catalog.packages.{pkg_name}.name", image_name, str(exc)
                ))

    # Generate errors for missing private registry configurations
    errors.extend(invalid_image_mappings)
    for registry, package_names in sorted(private_registries_missing.items()):
        errors.append(create_error_msg(
            "registries", registry,
            f"Catalog package(s) {sorted(set(package_names))} reference private registry "
            f"'{registry}', but it is not configured under registries"
        ))

    if errors:
        logger.error("Found %d catalog registry mapping error(s)", len(errors))
    else:
        logger.info(
            "All catalog image registries are properly configured in "
            "repo_manager_config.yml"
        )

    return errors
