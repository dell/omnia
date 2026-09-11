# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Kernel-version override validation for the current orchestrator workflow."""

import pytest

from library.functions import (
    TestLogger,
    get_kernel_version_override,
    validate_kernel_version_override_format,
    verify_all_nodes_kernel_version,
    verify_kernel_consistency,
)


def _logger(case_id, title):
    return TestLogger(title, case_id)


def _skip_unconfigured(result, logger):
    if result.get("not_configured"):
        message = "kernel_version_override is empty or runtime artifacts are unavailable"
        logger.skipped(message, result.get("details", ""))
        pytest.skip(message)


@pytest.mark.sanity
@pytest.mark.kernel_override
@pytest.mark.order(200)
def test_kernel_override_config(host):
    """ORCH_FVT_KERNEL_OVERRIDE_V001: Verify kernel_version_override is readable."""
    logger = _logger("ORCH_FVT_KERNEL_OVERRIDE_V001", "Verify kernel override configuration")
    logger.check("Reading kernel_version_override from orchestrator_config.yml")
    result = get_kernel_version_override(host)
    details = f"Configured value: {result.get('kernel_version_override', '') or '<empty>'}"
    (logger.passed if result["success"] else logger.failed)(
        "Kernel override configuration read successfully" if result["success"] else "Unable to read kernel override configuration",
        details if result["success"] else result["error"],
    )
    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.kernel_override
@pytest.mark.order(201)
def test_kernel_override_format(host):
    """ORCH_FVT_KERNEL_OVERRIDE_V002: Verify the configured kernel version format."""
    logger = _logger("ORCH_FVT_KERNEL_OVERRIDE_V002", "Validate kernel override format")
    logger.check("Validating kernel_version_override format")
    result = validate_kernel_version_override_format(host)
    if result.get("is_empty"):
        pytest.skip("kernel_version_override is empty")
    success = result["success"] and result["is_valid_format"]
    details = f"Value: {result['kernel_version_override']}"
    (logger.passed if success else logger.failed)("Kernel version format is valid" if success else "Kernel version format is invalid", details)
    assert success, details



@pytest.mark.sanity
@pytest.mark.kernel_override
@pytest.mark.order(202)
def test_kernel_override_nodes(host):
    """ORCH_FVT_KERNEL_OVERRIDE_V003: Verify provisioned nodes run the override kernel."""
    logger = _logger("ORCH_FVT_KERNEL_OVERRIDE_V003", "Verify node kernel override")
    logger.check("Checking kernels on provisioned nodes")
    result = verify_all_nodes_kernel_version(host)
    _skip_unconfigured(result, logger)
    (logger.passed if result["success"] else logger.failed)("Node kernels match override" if result["success"] else "Node kernels do not match override", result["details"])
    assert result["success"], result["details"]


@pytest.mark.sanity
@pytest.mark.kernel_override
@pytest.mark.order(203)
def test_kernel_consistency_across_nodes(host):
    """ORCH_FVT_KERNEL_OVERRIDE_V004: Verify kernel consistency across provisioned nodes."""
    logger = _logger("ORCH_FVT_KERNEL_OVERRIDE_V004", "Verify kernel consistency")
    logger.check("Checking kernel consistency across nodes")
    result = verify_kernel_consistency(host)
    if not result["nodes"]:
        pytest.skip("No provisioned nodes found")
    (logger.passed if result["success"] else logger.failed)("Node kernels are consistent" if result["success"] else "Node kernels are inconsistent", result["details"])
    assert result["success"], result["details"]




