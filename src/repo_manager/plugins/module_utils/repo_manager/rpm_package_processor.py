# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Policy decisions shared by Repo Manager RPM package processing."""


def catalog_rpm_type(package_name, rpm_type_mapping):
    """Return the supported catalog RPM type for a package."""
    package_type = rpm_type_mapping.get(package_name, "rpm")
    return package_type if package_type in ("rpm", "rpm_repo") else "rpm"


def _legacy_package_action(package_name, rpm_type_mapping, repo_config_value):
    """Return the pre-policy-map action for backward-compatible direct callers."""
    if repo_config_value == "always":
        return "download", False
    if catalog_rpm_type(package_name, rpm_type_mapping) == "rpm_repo":
        return "download", True
    return "validate", False


def partition_rpm_work(rpm_list, rpm_type_mapping, repo_config_value,
                       rpm_policy_mapping=None):
    """Split RPMs using each package's effective Pulp retention policy.

    Prepared catalog tasks provide ``rpm_policy_mapping``. Direct legacy callers
    that do not provide it retain the earlier global-policy/package-type
    behavior.
    """
    downloads = []
    validations = []
    require_mapped_repo = False
    policy_mapping = rpm_policy_mapping or {}

    for package_name in rpm_list:
        pulp_policy = policy_mapping.get(package_name)
        if pulp_policy is None:
            action, requires_mapping = _legacy_package_action(
                package_name, rpm_type_mapping, repo_config_value
            )
        elif pulp_policy in ("immediate", "on_demand"):
            action = "download"
            requires_mapping = pulp_policy == "on_demand"
        elif pulp_policy == "streamed":
            action = "validate"
            requires_mapping = False
        else:
            raise ValueError("Unsupported effective Pulp policy for RPM processing")

        if action == "download":
            downloads.append(package_name)
            require_mapped_repo = require_mapped_repo or requires_mapping
        else:
            validations.append(package_name)

    return downloads, validations, require_mapped_repo
