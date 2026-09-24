# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Target-aware Python artifact download helpers.

The Repo Manager process can run on a different Python version and CPU
architecture than the nodes consuming the offline repository.  This module
therefore builds explicit target-wheel commands and permits only an explicit
source-distribution fallback.  It never retries with an unconstrained host
``pip download`` command.
"""

import os
import re
import tempfile


_PYTHON_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+$")
_PYTHON_DISTRIBUTION_SUFFIXES = (
    ".whl",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".zip",
)


def build_pip_platform_args(target_python, architecture, platform_map, logger):
    """Return mandatory target-wheel selection arguments for ``pip``.

    A target Python version without a known architecture mapping is rejected;
    silently falling back to the OIM host platform can produce unusable wheels.
    """
    target_python = str(target_python or "").strip()
    architecture = str(architecture or "").strip()
    if not _PYTHON_VERSION_PATTERN.fullmatch(target_python):
        raise ValueError("Target Python version must use major.minor format")

    platforms = platform_map.get(architecture, [])
    if not platforms:
        raise ValueError("Target architecture has no configured pip platforms")

    abi = "cp" + target_python.replace(".", "")
    arguments = [
        "--python-version", target_python,
        "--implementation", "cp",
        "--abi", abi,
        "--only-binary=:all:",
    ]
    for platform in platforms:
        arguments.extend(["--platform", str(platform)])

    logger.info(
        "Pip target-platform arguments prepared for %s/%s",
        architecture,
        target_python,
    )
    return arguments


def build_target_wheel_command(
        package_spec, destination, target_python, architecture,
        platform_map, logger):
    """Build an explicit wheel command for the target interpreter/platform."""
    return [
        "pip", "download", "-d", destination,
        *build_pip_platform_args(
            target_python, architecture, platform_map, logger
        ),
        package_spec,
    ]


def build_source_distribution_command(package_spec, destination):
    """Build the only permitted fallback: the requested package's sdist.

    ``--no-deps`` is intentional. Dependency resolution under host markers
    would reintroduce the cross-target bug; dependencies must already be
    available as target-compatible wheels or explicit catalog selections.
    """
    return [
        "pip", "download", "-d", destination,
        "--no-deps", "--no-binary=:all:", package_spec,
    ]


def _distribution_files(directory):
    """Return regular Python distribution files from one staging directory."""
    artifacts = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if (
                os.path.isfile(path)
                and not os.path.islink(path)
                and name.lower().endswith(_PYTHON_DISTRIBUTION_SUFFIXES)):
            artifacts.append(path)
    return artifacts


def _publish_staged_artifacts(staging_directory, target_directory):
    """Atomically expose completed downloads and return their final paths."""
    artifacts = _distribution_files(staging_directory)
    published = []
    for staged_path in artifacts:
        final_path = os.path.join(
            target_directory, os.path.basename(staged_path)
        )
        os.replace(staged_path, final_path)
        published.append(final_path)
    return published


def download_python_artifacts(
        package_spec, target_directory, target_python, architecture,
        platform_map, execute_command, logger):
    """Download target wheels or an explicit source distribution.

    Each attempt uses a private staging directory, so a failed wheel
    resolution cannot leave a partial set that is later uploaded as success.
    Returns final artifact paths, or an empty list when both safe attempts fail.
    """
    os.makedirs(target_directory, exist_ok=True)

    with tempfile.TemporaryDirectory(
            prefix=".pip-wheel-", dir=target_directory) as staging_directory:
        wheel_command = build_target_wheel_command(
            package_spec,
            staging_directory,
            target_python,
            architecture,
            platform_map,
            logger,
        )
        if execute_command(wheel_command, logger):
            artifacts = _publish_staged_artifacts(
                staging_directory, target_directory
            )
            if artifacts:
                return artifacts
            logger.error("Target wheel download produced no distribution files")

    logger.warning(
        "Target wheel resolution failed; attempting an explicit "
        "source-distribution download without host dependency resolution"
    )
    with tempfile.TemporaryDirectory(
            prefix=".pip-sdist-", dir=target_directory) as staging_directory:
        source_command = build_source_distribution_command(
            package_spec, staging_directory
        )
        if execute_command(source_command, logger):
            artifacts = _publish_staged_artifacts(
                staging_directory, target_directory
            )
            if artifacts:
                return artifacts
            logger.error("Source download produced no distribution files")

    return []


def artifacts_are_platform_independent(file_paths):
    """Return whether a downloaded Python artifact set is architecture-neutral."""
    for file_path in file_paths:
        name = os.path.basename(file_path).lower()
        if not name.endswith(".whl"):
            continue
        wheel_parts = name[:-4].rsplit("-", maxsplit=3)
        if len(wheel_parts) != 4:
            return False
        _distribution, _python_tag, abi_tag, platform_tag = wheel_parts
        if abi_tag != "none" or platform_tag != "any":
            return False
    return bool(file_paths)
