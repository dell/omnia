# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Verify OCI references and target platforms from Pulp container metadata."""

from ansible.module_utils.repo_manager.pulp_commands import (
    build_container_tags_href,
    pulp_common_commands,
    pulp_container_commands,
)
from ansible.module_utils.repo_manager.pulp_object_state import query_pulp_object
from ansible.module_utils.repo_manager.security_utils import (
    validate_container_digest,
    validate_container_tag,
)


_PULP_ARCHITECTURES = {
    "x86_64": "amd64",
    "aarch64": "arm64",
}
_MAX_MANIFEST_DEPTH = 2


def _list_results(details):
    """Return list results from supported Pulp CLI JSON shapes."""
    if isinstance(details, list):
        return details
    if isinstance(details, dict) and isinstance(details.get("results"), list):
        return details["results"]
    return None


def _manifest_platforms(manifest_href, logger, executor, depth=0):
    """Return ``(state, platforms)`` for one image or manifest-list href."""
    if depth > _MAX_MANIFEST_DEPTH:
        logger.error("Container manifest nesting exceeds the supported depth")
        return False, set()
    present, details = query_pulp_object(
        pulp_common_commands["show_href"] % manifest_href,
        logger,
        executor,
    )
    if present is not True:
        return present, set()
    if not isinstance(details, dict):
        return None, set()

    architecture = details.get("architecture")
    operating_system = details.get("os")
    if isinstance(architecture, str) and architecture:
        if operating_system not in (None, "linux"):
            return True, set()
        return True, {architecture}

    listed_manifests = details.get("listed_manifests")
    if not isinstance(listed_manifests, list) or not listed_manifests:
        return None, set()

    platforms = set()
    for child_href in listed_manifests:
        if not isinstance(child_href, str) or not child_href:
            return None, set()
        child_state, child_platforms = _manifest_platforms(
            child_href, logger, executor, depth + 1
        )
        if child_state is not True:
            return child_state, set()
        platforms.update(child_platforms)
    return True, platforms


def verify_container_reference(
        repository_version, reference, architecture, logger, executor):
    """Return tri-state readiness for one tag/digest and target architecture.

    ``True`` means that the exact reference exists in the supplied repository
    version and, when requested, resolves to a Linux manifest for the target
    CPU architecture. ``False`` is confirmed absence/incompatibility and
    ``None`` is unreadable or malformed Pulp state.
    """
    if not isinstance(repository_version, str) or not repository_version:
        return None

    is_digest = isinstance(reference, str) and reference.startswith("sha256:")
    try:
        if is_digest:
            reference = validate_container_digest(reference)
            command = pulp_container_commands["list_manifest_digest"] % (
                reference, repository_version,
            )
        else:
            reference = validate_container_tag(reference)
            command = pulp_common_commands["show_href"] % (
                build_container_tags_href(repository_version, reference)
            )
    except (TypeError, ValueError):
        return None

    readable, details = query_pulp_object(command, logger, executor)
    if readable is not True:
        return readable
    matches = _list_results(details)
    if matches is None:
        return None
    if len(matches) != 1 or not isinstance(matches[0], dict):
        return False

    manifest_href = (
        matches[0].get("pulp_href")
        if is_digest else matches[0].get("tagged_manifest")
    )
    if not isinstance(manifest_href, str) or not manifest_href:
        # Presence-only compatibility is retained for internal callers that do
        # not yet provide a target architecture.
        return True if not architecture and not is_digest else None
    if not architecture:
        return True

    expected_architecture = _PULP_ARCHITECTURES.get(str(architecture))
    if expected_architecture is None:
        logger.error("Unsupported target architecture for container image")
        return None
    manifest_state, platforms = _manifest_platforms(
        manifest_href, logger, executor
    )
    if manifest_state is not True:
        return manifest_state
    if expected_architecture not in platforms:
        logger.error(
            "Container reference has platforms %s, not required %s",
            sorted(platforms),
            expected_architecture,
        )
        return False
    return True
