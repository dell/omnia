# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Isolated package-manager cache paths for Repo Manager contexts."""

import os


def get_package_manager_cache_path(repo_store_path, package_manager, os_type,
                                   os_version, architecture):
    """Return a cache path isolated by manager, OS, version and architecture."""
    values = (package_manager, os_type, os_version, architecture)
    if any(not str(value or "").strip() for value in values):
        raise ValueError("Package-manager cache context values must not be empty")
    return os.path.join(
        repo_store_path, ".data", "package_manager_cache",
        str(package_manager), str(os_type), str(os_version), str(architecture)
    )


def prepare_dnf_cache_options(repo_store_path, os_type, os_version,
                              architecture):
    """Create the active DNF cache directories and return CLI options."""
    context_path = get_package_manager_cache_path(
        repo_store_path, "dnf", os_type, os_version, architecture
    )
    cache_path = os.path.join(context_path, "cache")
    persist_path = os.path.join(context_path, "persist")
    os.makedirs(cache_path, mode=0o755, exist_ok=True)
    os.makedirs(persist_path, mode=0o755, exist_ok=True)
    return [
        f"--setopt=cachedir={cache_path}",
        f"--setopt=persistdir={persist_path}",
    ]
