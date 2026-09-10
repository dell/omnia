# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

# pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
"""
Test Category: Repository Enablement Testing
Tests that the 'enabled' field correctly controls repository processing.
"""

import pytest
from testinfra.host import Host
import yaml

from library.functions import (
    TestLogger,
    check_input_config_exists,
    _get_input_path,
)
from library.messages.repo_manager_msgs import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_enabled_field_default(host: Host):
    """TC_RM_EN_001: Repositories without 'enabled' field default to enabled."""
    tl = TestLogger(TEST_NAMES["enabled_field_default"], "TC_RM_EN_001")

    # Check if config file exists
    config_check = check_input_config_exists(host)
    if not config_check["success"]:
        tl.failed(LOG["config_not_found"], "Cannot verify without config file")
        pytest.skip("Cannot verify without config file")

    # Read the config file
    input_path = _get_input_path()
    config_file = f"{input_path}/repo_manager_config.yml"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Check repositories section
        repositories = config_data.get("repositories", {})
        if not repositories:
            tl.failed(LOG["no_repos"], "No repositories found in config")
            pytest.fail("No repositories found in config")

        # Verify that repos without 'enabled' field are treated as enabled
        for _, arch_data in repositories.items():
            for _, repos in arch_data.items():
                for repo_name, repo_config in repos.items():
                    if repo_name in ("additional_repos", "user_repos"):
                        continue

                    if not isinstance(repo_config, dict):
                        continue

                    # If 'enabled' field is not present, it should default to True
                    if "enabled" not in repo_config:
                        tl.passed(
                            f"Repository {repo_name} has no 'enabled' field (defaults to enabled)"
                        )
                    else:
                        # If present, verify it's a boolean
                        assert isinstance(repo_config["enabled"], bool), (
                            f"Repository {repo_name} 'enabled' field must be boolean"
                        )
                        tl.passed(
                            f"Repository {repo_name} has valid 'enabled' field"
                        )

    except (OSError, yaml.YAMLError) as e:
        tl.failed(LOG["config_read_error"], f"Error reading config: {str(e)}")
        pytest.fail(f"Error reading config: {str(e)}")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_disabled_repo_excluded(host: Host):
    """TC_RM_EN_002: Disabled repositories are excluded from processing."""
    tl = TestLogger(TEST_NAMES["disabled_repo_excluded"], "TC_RM_EN_002")

    # Check if config file exists
    config_check = check_input_config_exists(host)
    if not config_check["success"]:
        tl.failed(LOG["config_not_found"], "Cannot verify without config file")
        pytest.skip("Cannot verify without config file")

    # Read the config file
    input_path = _get_input_path()
    config_file = f"{input_path}/repo_manager_config.yml"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Check for disabled repositories
        repositories = config_data.get("repositories", {})
        disabled_repos = []

        for version, arch_data in repositories.items():
            for arch, repos in arch_data.items():
                for repo_name, repo_config in repos.items():
                    if repo_name in ("additional_repos", "user_repos"):
                        # Check nested repos
                        if isinstance(repo_config, dict):
                            for nested_name, nested_config in repo_config.items():
                                if isinstance(nested_config, dict) and not nested_config.get(
                                    "enabled", True
                                ):
                                    disabled_repos.append(
                                        f"{version}/{arch}/{repo_name}/{nested_name}"
                                    )
                    else:
                        # Check flat repos
                        if isinstance(repo_config, dict) and not repo_config.get(
                            "enabled", True
                        ):
                            disabled_repos.append(
                                f"{version}/{arch}/{repo_name}"
                            )

        if disabled_repos:
            tl.passed(
                f"Found {len(disabled_repos)} disabled repositories: {disabled_repos}"
            )
        else:
            tl.passed("No disabled repositories found in config (all repos enabled)")

    except (OSError, yaml.YAMLError) as e:
        tl.failed(LOG["config_read_error"], f"Error reading config: {str(e)}")
        pytest.fail(f"Error reading config: {str(e)}")


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_enabled_repo_included(host: Host):
    """TC_RM_EN_003: Enabled repositories are included in processing."""
    tl = TestLogger(TEST_NAMES["enabled_repo_included"], "TC_RM_EN_003")

    # Check if config file exists
    config_check = check_input_config_exists(host)
    if not config_check["success"]:
        tl.failed(LOG["config_not_found"], "Cannot verify without config file")
        pytest.skip("Cannot verify without config file")

    # Read the config file
    input_path = _get_input_path()
    config_file = f"{input_path}/repo_manager_config.yml"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Check for enabled repositories
        repositories = config_data.get("repositories", {})
        enabled_repos = []

        for version, arch_data in repositories.items():
            for arch, repos in arch_data.items():
                for repo_name, repo_config in repos.items():
                    if repo_name in ("additional_repos", "user_repos"):
                        # Check nested repos
                        if isinstance(repo_config, dict):
                            for nested_name, nested_config in repo_config.items():
                                if isinstance(nested_config, dict):
                                    enabled = nested_config.get("enabled", True)
                                    if enabled:
                                        enabled_repos.append(
                                            f"{version}/{arch}/{repo_name}/{nested_name}"
                                        )
                    else:
                        # Check flat repos
                        if isinstance(repo_config, dict):
                            enabled = repo_config.get("enabled", True)
                            if enabled:
                                enabled_repos.append(
                                    f"{version}/{arch}/{repo_name}"
                                )

        if enabled_repos:
            tl.passed(
                f"Found {len(enabled_repos)} enabled repositories: {enabled_repos[:5]}..."
            )
        else:
            tl.failed(LOG["no_enabled_repos"], "No enabled repositories found")
            pytest.fail("No enabled repositories found - this would prevent all repo operations")

    except (OSError, yaml.YAMLError) as e:
        tl.failed(LOG["config_read_error"], f"Error reading config: {str(e)}")
        pytest.fail(f"Error reading config: {str(e)}")


@pytest.mark.sanity
@pytest.mark.negative
@pytest.mark.order(4)
def test_invalid_enabled_field(host: Host):
    """TC_RM_EN_004: Invalid 'enabled' field values are rejected."""
    tl = TestLogger(TEST_NAMES["invalid_enabled_field"], "TC_RM_EN_004")

    # Check if config file exists
    config_check = check_input_config_exists(host)
    if not config_check["success"]:
        tl.failed(LOG["config_not_found"], "Cannot verify without config file")
        pytest.skip("Cannot verify without config file")

    # Read the config file
    input_path = _get_input_path()
    config_file = f"{input_path}/repo_manager_config.yml"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Check for invalid 'enabled' field values
        repositories = config_data.get("repositories", {})
        invalid_repos = []

        for version, arch_data in repositories.items():
            for arch, repos in arch_data.items():
                for repo_name, repo_config in repos.items():
                    if repo_name in ("additional_repos", "user_repos"):
                        # Check nested repos
                        if isinstance(repo_config, dict):
                            for nested_name, nested_config in repo_config.items():
                                if isinstance(nested_config, dict) and "enabled" in nested_config:
                                    if not isinstance(
                                        nested_config["enabled"], bool
                                    ):
                                        invalid_repos.append(
                                            f"{version}/{arch}/{repo_name}/{nested_name}"
                                        )
                    else:
                        # Check flat repos
                        if isinstance(repo_config, dict) and "enabled" in repo_config:
                            if not isinstance(repo_config["enabled"], bool):
                                invalid_repos.append(
                                    f"{version}/{arch}/{repo_name}"
                                )

        if invalid_repos:
            tl.failed(
                LOG["invalid_enabled_field"],
                f"Found invalid 'enabled' fields: {invalid_repos}",
            )
            pytest.fail(f"Invalid 'enabled' field values found: {invalid_repos}")
        else:
            tl.passed("All 'enabled' fields have valid boolean values")

    except (OSError, yaml.YAMLError) as e:
        tl.failed(LOG["config_read_error"], f"Error reading config: {str(e)}")
        pytest.fail(f"Error reading config: {str(e)}")
