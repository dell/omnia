# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Context-aware identity helpers for the Pulp RPM backend."""

from ansible.module_utils.repo_manager.security_utils import (
    validate_repository_id,
)


def _path_component(value, field_name):
    """Return a safe, non-empty Pulp base-path component."""
    component = str(value or "").strip().strip("/")
    try:
        return validate_repository_id(component)
    except ValueError as error:
        raise ValueError(f"Invalid Pulp RPM {field_name}") from error


def build_rpm_distribution_identity(distribution_root, architecture, os_type,
                                    os_version, package_name,
                                    package_version=None):
    """Return the repository name and Pulp base path for an RPM distribution."""
    root = str(distribution_root or "").strip().strip("/")
    if not root:
        raise ValueError("Invalid Pulp RPM distribution root")
    try:
        root_parts = [
            validate_repository_id(part) for part in root.split("/")
        ]
    except ValueError as error:
        raise ValueError("Invalid Pulp RPM distribution root") from error

    components = [
        "/".join(root_parts),
        _path_component(architecture, "architecture"),
        _path_component(os_type, "OS type"),
        _path_component(os_version, "OS version"),
        "rpms",
        _path_component(package_name, "repository name"),
    ]
    repository_name = str(package_name)
    version = str(package_version or "").strip()
    if version and version.lower() != "null":
        components.append(_path_component(version, "repository version"))
        repository_name = f"{repository_name}_{version}"

    return validate_repository_id(repository_name), "/".join(components)
