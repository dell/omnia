# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Platform capability registry for Repo Manager execution dispatch."""

from copy import deepcopy

from ansible.module_utils.repo_manager.repo_settings import get_config_value


def get_platform_profiles():
    """Return configured platform profiles without exposing mutable globals."""
    profiles = get_config_value("platform_profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("platform_profiles must be a mapping")
    return deepcopy(profiles)


def get_platform_capabilities(os_type, require_enabled=True):
    """Return capabilities for an operating system or raise a clear error."""
    profiles = get_platform_profiles()
    profile = profiles.get(str(os_type))
    if not isinstance(profile, dict):
        raise ValueError(
            f"No platform capability profile is configured for '{os_type}'"
        )
    if require_enabled and not bool(profile.get("enabled", False)):
        status = profile.get("implementation_status", "disabled")
        raise ValueError(
            f"Platform '{os_type}' is not enabled ({status}); no changes were made"
        )

    required = ("package_manager", "package_backend", "repository_access")
    missing = [name for name in required if not str(profile.get(name, "")).strip()]
    if missing:
        raise ValueError(
            f"Platform '{os_type}' is missing capabilities: {', '.join(missing)}"
        )
    return deepcopy(profile)
