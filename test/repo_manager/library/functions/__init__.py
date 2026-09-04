# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager library functions.

This module exports all verification functions for repo_manager testing.
"""

from omnia_auto import TestLogger

# Repo Manager verification functions
from .repo_manager_func import (
    run_playbook,
    check_input_config_exists,
    check_endpoint_config_exists,
    check_credentials_present,
    check_repo_configured,
    check_pulp_container_running,
    check_pulp_status_healthy,
    check_pulp_endpoint_reachable,
    check_pulp_cli_configured,
    check_pulp_certificates_exist,
    check_pulp_cli_repository_list,
    check_pulp_api_detailed_status,
    check_software_download_status,
    check_per_software_package_status,
    check_pulp_repositories_synced,
    check_pulp_distributions_published,
    check_container_repos_synced,
    check_file_repos_synced,
    check_pulp_content_accessible,
    check_software_packages_in_pulp,
    check_repo_status_exists,
    check_repo_status_success,
    check_repo_status_has_repo,
    check_repo_status_has_file_repo,
    check_pulp_container_removed,
    check_pulp_cli_removed,
    check_pulp_directories_removed,
    check_repo_policy,
    check_repo_caching,
    check_pulp_mode,
    verify_repo_status_pulp_mode,
    check_global_repo_config,
    check_global_caching_policy,
    check_pulp_remote_policy,
    check_pulp_repository_exists,
    verify_policy_resolution,
    # Catalog verification functions
    check_catalog_file_exists,
    check_catalog_structure,
    check_catalog_functional_layers,
    check_catalog_groups,
    check_catalog_packages,
    check_catalog_has_group,
    check_catalog_has_package,
    check_catalog_package_type,
    check_catalog_input_file_exists,
    check_catalog_log_file_exists,
    parse_catalog_input_file,
)
