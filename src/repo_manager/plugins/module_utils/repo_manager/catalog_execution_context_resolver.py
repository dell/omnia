# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Resolve deterministic platform execution contexts from catalog layers."""

import re

from ansible.module_utils.repo_manager.config import (
    ARCH_SUFFIXES,
    PLATFORM_VERSION_ORDER,
    SUPPORTED_OS_TYPES,
)


_SUPPORTED_OS_PATTERN = "|".join(
    re.escape(item) for item in SUPPORTED_OS_TYPES
)
_SUPPORTED_ARCH_PATTERN = "|".join(
    re.escape(item) for item in ARCH_SUFFIXES
)
FUNCTIONAL_LAYER_PATTERN = re.compile(
    rf"^(?P<layer>.+)_(?P<os_type>{_SUPPORTED_OS_PATTERN})_"
    rf"(?P<major>[0-9]+)_(?P<minor>[0-9]+)_"
    rf"(?P<architecture>{_SUPPORTED_ARCH_PATTERN})$"
)


def parse_functional_layer_context(layer_name):
    """Return the platform context encoded in a functional-layer name."""
    match = FUNCTIONAL_LAYER_PATTERN.fullmatch(str(layer_name or ""))
    if not match:
        raise ValueError(
            "Functional layer name must end with "
            "_<os>_<major>_<minor>_<architecture>: "
            f"'{layer_name}'"
        )
    parsed = match.groupdict()
    return {
        "os_type": parsed["os_type"],
        "os_version": f"{parsed['major']}.{parsed['minor']}",
        "architecture": parsed["architecture"],
    }


def version_sort_key(version):
    """Return a numeric sort key for a dotted operating-system version."""
    parts = str(version).split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(
            f"Operating-system version must contain numeric components: '{version}'"
        )
    return tuple(int(part) for part in parts)


def resolve_catalog_execution_contexts(catalogs, logger):
    """Return one ordered execution context per OS minor version.

    A catalog may select one or more minor versions and one or more supported
    architectures. Multiple operating-system types in one execution remain
    unsupported because their repository-access providers may require
    incompatible host preparation.
    """
    if isinstance(catalogs, dict):
        catalogs = [catalogs]
    if not catalogs:
        raise ValueError("No catalogs were supplied for context resolution")

    os_types = set()
    layers_by_version = {}
    for catalog in catalogs:
        for layer in catalog.get("functionallayer", []):
            layer_name = layer.get("name", "")
            parsed = parse_functional_layer_context(layer_name)
            os_types.add(parsed["os_type"])
            layers_by_version.setdefault(parsed["os_version"], []).append({
                "name": layer_name,
                "components": list(layer.get("components", [])),
                "catalog_identifier": catalog.get("identifier", ""),
                **parsed,
            })

    if not layers_by_version:
        raise ValueError("Catalog does not contain any functional layers")
    if len(os_types) != 1:
        raise ValueError(
            "Catalog functional layers must use exactly one OS type; found: "
            + ", ".join(sorted(os_types))
        )

    os_type = next(iter(os_types))
    os_versions = sorted(
        layers_by_version,
        key=version_sort_key,
        reverse=PLATFORM_VERSION_ORDER == "descending",
    )
    execution_contexts = []
    all_architectures = set()
    all_functional_layers = []

    for os_version in os_versions:
        functional_layers = layers_by_version[os_version]
        discovered_architectures = {
            layer["architecture"] for layer in functional_layers
        }
        architectures = [
            arch for arch in ARCH_SUFFIXES if arch in discovered_architectures
        ]
        all_architectures.update(architectures)
        all_functional_layers.extend(functional_layers)
        execution_contexts.append({
            "context_id": f"{os_type}_{os_version}",
            "os_type": os_type,
            "os_version": os_version,
            "architectures": architectures,
            "functional_layers": functional_layers,
        })

    context = {
        "os_type": os_type,
        "os_versions": os_versions,
        "architectures": [
            arch for arch in ARCH_SUFFIXES if arch in all_architectures
        ],
        "functional_layers": all_functional_layers,
        "execution_contexts": execution_contexts,
    }

    # Preserve the established contract for every existing single-version
    # catalog. Multi-version callers must use execution_contexts explicitly.
    if len(execution_contexts) == 1:
        context["os_version"] = execution_contexts[0]["os_version"]

    logger.info(
        "Resolved catalog execution contexts: os=%s, versions=%s, contexts=%s",
        os_type,
        os_versions,
        [item["context_id"] for item in execution_contexts],
    )
    return context
