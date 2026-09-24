#!/usr/bin/python
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

"""Build catalog-scoped artifact and RPM task lists for parallel execution."""

# pylint: disable=import-error,no-name-in-module,too-many-locals,too-many-statements

import os
import shutil
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.security_utils import (
    redact_sensitive_value,
    validate_repository_id,
    validate_no_url_credentials,
)
from ansible.module_utils.repo_manager.software_utils import (
    transform_package_dict,
    remove_duplicates_from_trans,
    build_repo_name,
    normalize_repo_name,
    resolve_pulp_policy,
    resolve_repository_pulp_policy,
)
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_repo_manager_config,
    get_catalog_path,
    get_repo_config_policy,
    load_multiple_catalogs,
    build_global_package_index,
    parse_repo_urls_from_config,
    parse_additional_repos_from_config,
    parse_user_repos_from_config,
    resolve_catalog_context,
)
from ansible.module_utils.repo_manager.repo_settings import get_caching_policy
from ansible.module_utils.repo_manager.mirror_status import (
    load_mirror_index,
    save_mirror_index,
    save_global_package_index,
    update_mirror_index_entry,
    migrate_mirror_index,
    detect_package_changes,
    filter_tasks_for_processing,
    mark_package_entries_pending,
    repositories_requiring_retry,
)
from ansible.module_utils.repo_manager.config import (
    LOG_DIR_DEFAULT,
    MIRROR_INDEX_FILENAME,
    MIRROR_STATUS_DIR,
    REPO_MANAGER_CONFIG_PATH_DEFAULT,
)
DOCUMENTATION = r"""
---
module: prepare_tasklist
short_description: Prepare task list for parallel execution
description:
  - This module prepares a list of tasks for parallel execution.
  - It parses configuration and creates executable task definitions.
version_added: "1.0.0"
options:
    config:
      description: Configuration dictionary
      required: true
      type: dict
    task_type:
      description: Type of tasks to prepare
      required: true
      type: str

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Prepare sync task list
  prepare_tasklist:
    config: "{{ repo_config }}"
    task_type: sync
  register: tasklist
"""

RETURN = r"""
tasks:
  description: List of prepared tasks
  type: list
  returned: success
task_count:
  description: Number of tasks prepared
  type: int
  returned: success
"""

def normalize_resync_selection(
        resync_repos, retry_repositories=None,
        policy_changed_repositories=None):
    """Return all-selection flag and exact repositories requiring RPM work."""
    if resync_repos in (None, ""):
        all_selected = False
        values = []
    elif resync_repos == "all":
        all_selected = True
        values = []
    elif isinstance(resync_repos, str):
        all_selected = False
        values = [value.strip() for value in resync_repos.split(",")]
    elif isinstance(resync_repos, list):
        all_selected = False
        values = resync_repos
    else:
        raise ValueError("resync_repos must be a repository list or 'all'")
    selected_repositories = {
        validate_repository_id(value)
        for value in values
        if value
    }
    selected_repositories.update({
        validate_repository_id(repo_name)
        for repo_name in (retry_repositories or set())
    })
    selected_repositories.update({
        validate_repository_id(repo_name)
        for repo_name in (policy_changed_repositories or set())
    })
    return all_selected, selected_repositories


def packages_requiring_reconciliation(
        change_results, configured_registry_names, repository_context,
        resync_all=False, selected_repositories=None):
    """Return mirrored packages selected by explicit or recovery work.

    Ordinary successful RPMs stay skipped.  An explicit resync, a persisted
    repository failure, or an effective-policy transition selects only the
    packages mapped to the exact repository and execution context.
    """
    reconciliation_packages = []
    selected_repositories = selected_repositories or set()
    arch, os_type, os_version = repository_context
    for package_info in change_results.get("skip", []):
        package_type = package_info.get("type")
        if package_type in ("rpm", "rpm_repo"):
            repo_name = (
                package_info.get("repo_name")
                or package_info.get("definition", {}).get("repo_name", "")
            )
            if not repo_name:
                continue
            full_repo_name = validate_repository_id(normalize_repo_name(
                repo_name, arch, os_type, os_version
            ))
            if resync_all or full_repo_name in selected_repositories:
                reconciliation_packages.append(package_info)
            continue

        if (package_type == "image"
                and package_info.get("definition", {}).get("source_registry")
                in configured_registry_names):
            # Reconcile rotated private-registry credentials, certificates,
            # URLs, and policies even when the image identity is unchanged.
            reconciliation_packages.append(package_info)

    return reconciliation_packages


def main():
    """
    Prepares package lists and processes software based on catalog-based configuration.

    Reads from catalog/ directory and repo_manager_config.yml. Uses multi-catalog
    deduplication and pulp_mirror_index.json for incremental mirroring.
    """

    module_args = {
        "local_repo_config_path": {"type": "str", "required": False, "default": REPO_MANAGER_CONFIG_PATH_DEFAULT},
        "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
        "sub_urls": {"type": "dict", "required": False, "default": {}},
        "cluster_os_type": {"type": "str", "required": True},
        "cluster_os_version": {"type": "str", "required": True},
        "architectures": {
            "type": "list", "elements": "str", "required": True
        },
        "referenced_repositories": {
            "type": "dict", "required": False, "default": None
        },
        "resync_repos": {"type": "raw", "required": False, "default": None},
    }

    module = AnsibleModule(argument_spec=module_args)
    log_dir = module.params["log_dir"]
    local_repo_config_path = module.params["local_repo_config_path"]
    sub_urls = module.params["sub_urls"]
    cluster_os_type = module.params["cluster_os_type"]
    cluster_os_version = module.params["cluster_os_version"]
    selected_architectures = module.params["architectures"]
    referenced_repositories = module.params["referenced_repositories"]
    resync_repos = module.params["resync_repos"]
    logger = setup_standard_logger(log_dir)
    start_time = datetime.now().strftime("%I:%M:%S %p")
    logger.info(f"Start execution time: {start_time}")

    try:
        config_dir = os.path.dirname(os.path.abspath(local_repo_config_path))
        config_data, _ = load_repo_manager_config(local_repo_config_path, logger)
        repo_config = get_repo_config_policy(config_data)
        global_caching_policy = get_caching_policy(config_data)

        # Discover and load catalogs
        catalog_path = get_catalog_path(config_data, config_dir, logger)
        catalogs = load_multiple_catalogs(catalog_path, logger)

        resolved_context = resolve_catalog_context(catalogs, logger)
        matching_contexts = [
            context for context in resolved_context["execution_contexts"]
            if context["os_type"] == cluster_os_type
            and context["os_version"] == cluster_os_version
        ]
        if len(matching_contexts) != 1:
            raise ValueError(
                "Catalog context changed between setup and task preparation: "
                f"expected {cluster_os_type} {cluster_os_version} "
                f"{selected_architectures}, resolved "
                f"{resolved_context['execution_contexts']}"
            )
        active_context = matching_contexts[0]
        if selected_architectures != active_context["architectures"]:
            raise ValueError(
                "Catalog architectures changed between setup and task "
                f"preparation: expected {selected_architectures}, resolved "
                f"{active_context['architectures']}"
            )
        if referenced_repositories is None:
            # Preserve direct module callers while the production role passes
            # the setup-resolved map explicitly.
            referenced_repositories = active_context[
                "referenced_repositories"
            ]
        elif referenced_repositories != active_context["referenced_repositories"]:
            raise ValueError(
                "Catalog repository mapping changed between setup and task "
                "preparation"
            )

        # Build global package index with cross-catalog deduplication
        global_index = build_global_package_index(
            catalogs, logger, catalog_context=active_context
        )

        # Load mirror index for incremental mirroring
        mirror_index_dir = os.path.join(log_dir, MIRROR_STATUS_DIR)
        mirror_index_path = os.path.join(mirror_index_dir, MIRROR_INDEX_FILENAME)
        mirror_data = load_mirror_index(mirror_index_path, logger)
        source_schema_version = mirror_data.get(
            "MirrorIndex", {}
        ).get("schema_version", 1)
        mirror_index_migrated = migrate_mirror_index(
            mirror_data, global_index, logger
        )
        if mirror_index_migrated and os.path.isfile(mirror_index_path):
            backup_path = (
                f"{mirror_index_path}.schema-v{source_schema_version}.bak"
            )
            if not os.path.exists(backup_path):
                shutil.copy2(mirror_index_path, backup_path)
                logger.info("Backed up legacy mirror index to %s", backup_path)

        # Save global package index to file for reference
        global_index_path = os.path.join(mirror_index_dir, "global_package_index.json")
        save_global_package_index(global_index_path, global_index, logger)

        # Build task list per architecture with change detection
        final_tasks_dict = {}
        sw_archs = []
        rpm_reconciliation_hashes = set()
        retry_repositories = repositories_requiring_retry(mirror_data)

        for arch in selected_architectures:
            if arch not in global_index or not global_index[arch]:
                logger.info("No packages found for arch %s, skipping", arch)
                continue

            sw_archs.append(arch)

            # Detect changes against mirror index
            change_results = detect_package_changes(global_index, mirror_data, arch, logger)
            packages_to_process = filter_tasks_for_processing(change_results, logger)

            rpm_policy_by_repo = {
                repo_name: resolve_repository_pulp_policy(
                    config_data, cluster_os_version, arch, repo_name, logger
                )
                for repo_name in referenced_repositories.get(arch, [])
            }
            repository_states = mirror_data.get(
                "MirrorIndex", {}
            ).get("repositories", {})
            policy_changed_repositories = set()
            for repo_name, policy in rpm_policy_by_repo.items():
                full_repo_name = validate_repository_id(normalize_repo_name(
                    repo_name, arch, cluster_os_type, cluster_os_version
                ))
                stored_policy = repository_states.get(
                    full_repo_name, {}
                ).get("policy")
                if stored_policy and stored_policy != policy:
                    policy_changed_repositories.add(full_repo_name)

            configured_registry_names = set((config_data.get("registries") or {}).keys())
            resync_all, selected_repositories = normalize_resync_selection(
                resync_repos,
                retry_repositories=retry_repositories,
                policy_changed_repositories=policy_changed_repositories,
            )
            reconciliation_packages = packages_requiring_reconciliation(
                change_results,
                configured_registry_names,
                (arch, cluster_os_type, cluster_os_version),
                resync_all=resync_all,
                selected_repositories=selected_repositories,
            )
            if reconciliation_packages:
                logger.info(
                    "Reprocessing %d package(s) to reconcile external Pulp state",
                    len(reconciliation_packages)
                )
                packages_to_process.extend(reconciliation_packages)
                rpm_reconciliation_hashes.update(
                    package_info["hash"]
                    for package_info in reconciliation_packages
                    if package_info.get("type") in ("rpm", "rpm_repo")
                )

            if not packages_to_process:
                logger.info("No packages to process for arch %s (all up-to-date)", arch)
                continue

            # Group packages by group_name for the task dict
            tasks_by_group = {}
            for pkg_info in packages_to_process:
                group_name = pkg_info["group_name"]
                pkg_def = dict(pkg_info["definition"])

                # Normalize field names for parallel_tasks compatibility
                if "type" not in pkg_def:
                    pkg_def["type"] = pkg_def.get("packagetype", "rpm")
                if "package" not in pkg_def:
                    pkg_def["package"] = pkg_def.get("name", pkg_info.get("package_name", ""))
                if "version" not in pkg_def:
                    pkg_def["version"] = pkg_def.get("tag", "")
                # For tarballs/downloads, ensure url/path keys exist
                # (already lowercase in catalog data)

                pkg_def["catalog_name"] = pkg_info["catalog_name"]
                pkg_def["catalogs"] = pkg_info["catalogs"]

                if pkg_def["type"] in ("rpm", "rpm_repo"):
                    repo_name = (
                        pkg_def.get("repo_name")
                        or pkg_info.get("repo_name", "")
                    )
                    if repo_name not in rpm_policy_by_repo:
                        rpm_policy_by_repo[repo_name] = (
                            resolve_repository_pulp_policy(
                                config_data, cluster_os_version, arch,
                                repo_name, logger
                            )
                        )
                    pkg_def["pulp_policy"] = rpm_policy_by_repo[repo_name]

                if group_name not in tasks_by_group:
                    tasks_by_group[group_name] = []
                tasks_by_group[group_name].append(pkg_def)

            # Transform into the expected format and deduplicate
            trans = transform_package_dict(tasks_by_group, arch, logger)
            trans = remove_duplicates_from_trans(trans)
            logger.info("Catalog-based tasklist for arch %s: %s", arch, list(trans.keys()))
            final_tasks_dict.update(trans)

        # Save updated mirror index. RPMs selected for resync/recovery become
        # pending before Pulp work starts, so an interruption before DNF cannot
        # incorrectly preserve their previous successful state.
        mark_package_entries_pending(
            mirror_data, rpm_reconciliation_hashes
        )

        # Mark new packages as pending.
        for arch in sw_archs:
            arch_index = global_index.get(arch, {})
            for composite_hash, pkg_info in arch_index.items():
                existing_pkg = mirror_data.get(
                    "MirrorIndex", {}
                ).get("packages", {}).get(composite_hash)
                if existing_pkg is None:
                    update_mirror_index_entry(
                        mirror_data, pkg_info["package_name"], pkg_info["type"],
                        pkg_info["version"], arch, composite_hash,
                        pkg_info.get("group_name", ""), pkg_info["catalogs"],
                        "pending", "", pkg_info.get("repo_name", "")
                    )
        save_mirror_index(mirror_index_path, mirror_data, logger)

        # Parse repository URLs from config
        local_config = []
        explicitly_configured_repos = set()
        for arch in sw_archs:
            referenced_repo_names = referenced_repositories.get(arch, [])
            repos = parse_repo_urls_from_config(config_data, repo_config, arch,
                                                 cluster_os_version, logger,
                                                 global_caching_policy,
                                                 referenced_repo_names)
            for repo in repos:
                sw_name = build_repo_name(arch, cluster_os_type, cluster_os_version, repo["name"])
                pulp_policy = resolve_pulp_policy(repo.get("policy", repo_config),
                                                   repo.get("caching", global_caching_policy), logger)
                local_config.append({
                    "package": sw_name,
                    "url": repo["url"],
                    "gpgkey": repo.get("gpgkey", "") or "null",
                    "version": "null",
                    "ca_cert": repo.get("sslcacert", ""),
                    "client_key": repo.get("sslclientkey", ""),
                    "client_cert": repo.get("sslclientcert", ""),
                    "policy": pulp_policy,
                    "sw_arch": arch,
                    "priority": repo.get("priority"),
                })
                explicitly_configured_repos.add((arch, repo["name"]))

        # Add subscription-discovered URLs only when a repository does not have
        # an explicit configured URL. This makes a user-provided URL the highest
        # priority and prevents duplicate Pulp entries for the same repository.
        if sub_urls:
            for arch in sw_archs:
                if arch in sub_urls and sub_urls[arch]:
                    for url_entry in sub_urls[arch]:
                        name = url_entry.get("name", "unknown")
                        if (arch, name) in explicitly_configured_repos:
                            logger.info(
                                "Using explicitly configured URL for repository %s (%s); "
                                "skipping subscription-discovered URL",
                                name, arch
                            )
                            continue
                        sw_name = build_repo_name(arch, cluster_os_type, cluster_os_version, name)
                        pulp_policy = resolve_pulp_policy(
                            url_entry.get("policy", repo_config),
                            url_entry.get("caching", global_caching_policy), logger)
                        local_config.append({
                            "package": sw_name,
                            "url": url_entry.get("url", ""),
                            "gpgkey": url_entry.get("gpgkey", "") or "null",
                            "version": "null",
                            "ca_cert": url_entry.get("sslcacert", ""),
                            "client_key": url_entry.get("sslclientkey", ""),
                            "client_cert": url_entry.get("sslclientcert", ""),
                            "policy": pulp_policy,
                            "sw_arch": arch,
                            "priority": url_entry.get("priority"),
                        })

        # Parse additional repos from config
        additional_repos_config = {}
        for arch in sw_archs:
            add_repos = parse_additional_repos_from_config(
                config_data, repo_config, arch, cluster_os_version, logger,
                global_caching_policy, os_type=cluster_os_type,
                referenced_repo_names=referenced_repositories.get(arch, []))
            if add_repos:
                additional_repos_config[arch] = add_repos
            else:
                additional_repos_config[arch] = []

        # Parse user repos from config
        user_repos_config = {}
        for arch in sw_archs:
            user_repos = parse_user_repos_from_config(
                config_data, cluster_os_version, arch, repo_config, logger,
                global_caching_policy, os_type=cluster_os_type,
                referenced_repo_names=referenced_repositories.get(arch, []))
            if user_repos:
                user_repos_config[arch] = user_repos
            else:
                user_repos_config[arch] = []

        validate_no_url_credentials(final_tasks_dict)
        logger.info(
            "Package processing completed: %s",
            redact_sensitive_value(final_tasks_dict),
        )
        module.exit_json(
            changed=False,
            software_dict=final_tasks_dict,
            local_config=local_config,
            additional_repos_config=additional_repos_config,
            user_repos_config=user_repos_config,
            sw_archs=sw_archs
        )

    except Exception as error:
        logger.error(
            "Package task preparation failed (%s).", type(error).__name__
        )
        module.fail_json(
            msg=f"Package task preparation failed ({type(error).__name__})."
        )


if __name__ == "__main__":
    main()
