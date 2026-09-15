# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Focused unit tests for Orchestrator input validation."""

import logging

import pytest

from ut import source_loader  # noqa: F401  # initializes module_utils path
from ansible.module_utils.orchestrator_validation.validators import (
    orchestrator_config_validator,
)


pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("orchestrator-validation-test")


def _validate_cloud_init(config):
    errors = []
    orchestrator_config_validator._validate_additional_cloud_init_config(  # pylint: disable=protected-access
        config, errors, LOGGER
    )
    return errors


def test_empty_additional_cloud_init_path_is_valid():
    """ORCH_UT_078: Empty additional cloud-init cleanly disables the feature."""
    assert _validate_cloud_init({"additional_cloud_init_config_file": ""}) == []


def test_existing_additional_cloud_init_file_is_valid(tmp_path):
    """ORCH_UT_079: A configured regular cloud-init file is accepted."""
    config_file = tmp_path / "additional.yml"
    config_file.write_text("common: {}\ngroups: {}\n", encoding="utf-8")
    assert _validate_cloud_init(
        {"additional_cloud_init_config_file": str(config_file)}
    ) == []


def test_missing_additional_cloud_init_file_is_rejected(tmp_path):
    """ORCH_UT_080: A missing configured cloud-init file fails validation."""
    missing = tmp_path / "missing.yml"
    errors = _validate_cloud_init(
        {"additional_cloud_init_config_file": str(missing)}
    )
    assert len(errors) == 1
    assert str(missing) in errors[0]


def test_additional_cloud_init_directory_is_rejected(tmp_path):
    """ORCH_UT_081: A directory cannot masquerade as cloud-init input."""
    errors = _validate_cloud_init(
        {"additional_cloud_init_config_file": str(tmp_path)}
    )
    assert len(errors) == 1
