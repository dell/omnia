# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Context-aware identity helpers for the Pulp RPM backend."""


def _path_component(value, field_name):
    """Return a safe, non-empty Pulp base-path component."""
    component = str(value or "").strip().strip("/")
    if not component or component in (".", "..") or "/" in component:
        raise ValueError(f"Invalid Pulp RPM {field_name}: '{value}'")
    return component


def build_rpm_distribution_identity(distribution_root, architecture, os_type,
                                    os_version, package_name,
                                    package_version=None):
    """Return the repository name and Pulp base path for an RPM distribution."""
    root = str(distribution_root or "").strip().strip("/")
    if not root or any(part in ("", ".", "..") for part in root.split("/")):
        raise ValueError(
            f"Invalid Pulp RPM distribution root: '{distribution_root}'"
        )

    components = [
        root,
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

    return repository_name, "/".join(components)
