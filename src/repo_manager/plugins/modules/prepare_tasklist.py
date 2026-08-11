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

# pylint: disable=import-error,no-name-in-module,too-many-locals,too-many-statements
#!/usr/bin/python

import os
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.software_utils import (
    transform_package_dict,
    remove_duplicates_from_trans,
    build_repo_name,
    resolve_pulp_policy,
)
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_repo_manager_config,
    get_catalog_path,
    get_repo_config_policy,
    load_multiple_catalogs,
    build_global_package_index,
    parse_repo_urls_from_config,
    parse_additional_repos_from_config,
)
from ansible.module_utils.repo_manager.mirror_status import (
    load_mirror_index,
    save_mirror_index,
    save_global_package_index,
    update_mirror_index_entry,
    detect_package_changes,
    filter_tasks_for_processing,
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

from ansible.module_utils.repo_manager.config import (
    CSV_FILE_PATH_DEFAULT,
    LOG_DIR_DEFAULT,
    REPO_MANAGER_CONFIG_PATH_DEFAULT,
    ARCH_SUFFIXES,
    MIRROR_STATUS_DIR,
    MIRROR_INDEX_FILENAME,
)


def main():
    """
    Prepares package lists and processes software based on catalog-based configuration.

    Reads from catalog/ directory and repo_manager_config.yml. Uses multi-catalog
    deduplication and pulp_mirror_index.json for incremental mirroring.
    """

    module_args = {
        "csv_file_path": {"type": "str", "required": False, "default": CSV_FILE_PATH_DEFAULT},
        "local_repo_config_path": {"type": "str", "required": False, "default": REPO_MANAGER_CONFIG_PATH_DEFAULT},
        "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
        "key_path": {"type": "str", "required": True},
        "sub_urls": {"type": "dict", "required": False, "default": {}}
    }

    module = AnsibleModule(argument_spec=module_args)
    log_dir = module.params["log_dir"]
    csv_file_path = module.params["csv_file_path"]
    local_repo_config_path = module.params["local_repo_config_path"]
    vault_key_path = module.params["key_path"]
    sub_urls = module.params["sub_urls"]
    logger = setup_standard_logger(log_dir)
    start_time = datetime.now().strftime("%I:%M:%S %p")
    logger.info(f"Start execution time: {start_time}")

    try:
        config_dir = os.path.dirname(os.path.abspath(local_repo_config_path))
        config_data, _ = load_repo_manager_config(local_repo_config_path, logger)
        repo_config = get_repo_config_policy(config_data)

        # Discover and load catalogs
        catalog_path = get_catalog_path(config_data, config_dir, logger)
        catalogs = load_multiple_catalogs(catalog_path, logger)

        # Extract OS info from first catalog's identifier
        first_catalog = catalogs[0]
        catalog_id = first_catalog["identifier"]
        cluster_os_type = "rhel"
        cluster_os_version = "10.0"
        parts = catalog_id.split("-")
        for i, part in enumerate(parts):
            if part in ("rhel"):
                cluster_os_type = part
                version_parts = []
                for j in range(i + 1, min(i + 3, len(parts))):
                    if parts[j].isdigit():
                        version_parts.append(parts[j])
                    else:
                        break
                if version_parts:
                    cluster_os_version = ".".join(version_parts)
                break

        logger.info("Detected OS: %s %s from catalog identifier: %s",
                    cluster_os_type, cluster_os_version, catalog_id)

        # Build global package index with cross-catalog deduplication
        global_index = build_global_package_index(catalogs, logger)

        # Load mirror index for incremental mirroring
        mirror_index_dir = os.path.join(log_dir, MIRROR_STATUS_DIR)
        mirror_index_path = os.path.join(mirror_index_dir, MIRROR_INDEX_FILENAME)
        mirror_data = load_mirror_index(mirror_index_path, logger)

        # Save global package index to file for reference
        global_index_path = os.path.join(mirror_index_dir, "global_package_index.json")
        save_global_package_index(global_index_path, global_index, logger)

        # Build task list per architecture with change detection
        final_tasks_dict = {}
        sw_archs = []

        for arch in ARCH_SUFFIXES:
            if arch not in global_index or not global_index[arch]:
                logger.info("No packages found for arch %s, skipping", arch)
                continue

            sw_archs.append(arch)

            # Detect changes against mirror index
            change_results = detect_package_changes(global_index, mirror_data, arch, logger)
            packages_to_process = filter_tasks_for_processing(change_results, logger)

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

                if group_name not in tasks_by_group:
                    tasks_by_group[group_name] = []
                tasks_by_group[group_name].append(pkg_def)

            # Transform into the expected format and deduplicate
            trans = transform_package_dict(tasks_by_group, arch, logger)
            trans = remove_duplicates_from_trans(trans)
            logger.info("Catalog-based tasklist for arch %s: %s", arch, list(trans.keys()))
            final_tasks_dict.update(trans)

        # Save updated mirror index (mark new packages as pending)
        for arch in sw_archs:
            arch_index = global_index.get(arch, {})
            for composite_hash, pkg_info in arch_index.items():
                existing_pkg = mirror_data.get("MirrorIndex", {}).get("packages", {}).get(pkg_info["package_name"])
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
        for arch in sw_archs:
            repos = parse_repo_urls_from_config(config_data, repo_config, arch,
                                                 cluster_os_version, logger)
            for repo in repos:
                sw_name = build_repo_name(arch, cluster_os_type, cluster_os_version, repo["name"])
                pulp_policy = resolve_pulp_policy(repo.get("policy", repo_config),
                                                   repo.get("caching", True), logger)
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
                })

        # Handle subscription URLs override
        if sub_urls:
            for arch in sw_archs:
                if arch in sub_urls and sub_urls[arch]:
                    for url_entry in sub_urls[arch]:
                        name = url_entry.get("name", "unknown")
                        sw_name = build_repo_name(arch, cluster_os_type, cluster_os_version, name)
                        pulp_policy = resolve_pulp_policy(
                            url_entry.get("policy", repo_config),
                            url_entry.get("caching", True), logger)
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
                        })

        # Parse additional repos from config
        additional_repos_config = {}
        for arch in sw_archs:
            add_repos = parse_additional_repos_from_config(
                config_data, repo_config, arch, cluster_os_version, logger)
            if add_repos:
                additional_repos_config[arch] = add_repos
            else:
                additional_repos_config[arch] = []

        logger.info(f"Package processing completed: {final_tasks_dict}")
        module.exit_json(
            changed=False,
            software_dict=final_tasks_dict,
            local_config=local_config,
            additional_repos_config=additional_repos_config,
            sw_archs=sw_archs
        )

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
