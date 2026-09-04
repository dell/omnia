# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Artifact-type to processor registry for Repo Manager workers."""

from ansible.module_utils.repo_manager.download_common import (
    process_ansible_galaxy_collection,
    process_git,
    process_iso,
    process_manifest,
    process_pip,
    process_rpm_file,
    process_shell,
    process_tarball,
)
from ansible.module_utils.repo_manager.download_image import process_image
from ansible.module_utils.repo_manager.download_rpm import process_rpm


_ARTIFACT_PROCESSORS = {
    "manifest": process_manifest,
    "git": process_git,
    "tarball": process_tarball,
    "shell": process_shell,
    "ansible_galaxy_collection": process_ansible_galaxy_collection,
    "iso": process_iso,
    "pip_module": process_pip,
    "image": process_image,
    "rpm_file": process_rpm_file,
    "rpm": process_rpm,
    "rpm_repo": process_rpm,
}


def get_artifact_processor(artifact_type):
    """Return the processor registered for a catalog artifact type."""
    processor = _ARTIFACT_PROCESSORS.get(str(artifact_type or ""))
    if processor is None:
        raise ValueError(f"Unknown task type: {artifact_type}")
    return processor


def supported_artifact_types():
    """Return registered executable artifact types in deterministic order."""
    return tuple(_ARTIFACT_PROCESSORS)
