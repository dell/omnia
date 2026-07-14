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

"""
Omnia.sh Install — Deploy Tests.

Runs the image build and omnia.sh --install steps with live streaming
output, identical to running the commands directly on the OIM server.
These tests run BEFORE the verification tests (test_omnia_sh.py).

Usage:
    run_validation omnia_sh_install deploy       # Build + install only
    run_validation omnia_sh_install test          # Build + install + verify
    run_validation omnia_sh_install verify        # Verification tests only
"""

import os

import pytest

from automation_library.core import TestLogger, OMNIA_SH_PATH
from automation_library.playbook_runner import PlaybookRunner
from automation_library.omnia_sh.vars.omnia_sh_vars import OMNIA_SH_VARS
from automation_library.omnia_sh.messages.omnia_sh_msgs import (
    TEST_NAMES, TEST_LOG_MSGS as LOG_MSGS, TEST_ASSERT_MSGS as ASSERT_MSGS, SKIP_MSGS
)
from automation_library.omnia_sh.functions.omnia_sh_func import (
    check_container_running,
    check_omnia_sh_exists,
    validate_nfs_config,
    run_omnia_sh_install_testinfra,
    setup_internal_nfs_server,
)

# Build timeout: 30 minutes (container image build can be slow)
BUILD_TIMEOUT = 1800


# =============================================================================
# 0. BUILD IMAGES (TC-0) — LIVE STREAMING
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(0)
def test_build_container_images(host):
    """
    Deploy TC-0: Build omnia_core container image via omnia.sh --build.

    Runs src/main/omnia.sh --build to build the core container image.
    All output is streamed line-by-line to the terminal in real-time,
    providing the same experience as running the build directly.

    Skips if omnia_core container is already running.
    """
    log = TestLogger("Deploy: Build container images")

    # Skip if container already running
    container_result = check_container_running(host)
    if container_result["success"]:
        log.skipped(SKIP_MSGS["container_running"])
        pytest.skip(SKIP_MSGS["container_running"])

    # Verify omnia.sh exists
    log.check(f"Checking omnia.sh at {OMNIA_SH_PATH}")
    assert os.path.isfile(OMNIA_SH_PATH), (
        f"omnia.sh not found at {OMNIA_SH_PATH}"
    )

    # Run omnia.sh --build with live streaming output
    runner = PlaybookRunner()
    result = runner.run_shell(
        f"bash {OMNIA_SH_PATH} --build",
        label="omnia.sh --build",
        timeout=BUILD_TIMEOUT,
    )

    if result["success"]:
        log.passed(
            f"Container images built successfully (rc={result['rc']}, "
            f"duration={result['duration']:.1f}s)"
        )
    else:
        log.failed(
            f"Container image build failed (rc={result['rc']}, "
            f"duration={result['duration']:.1f}s)",
            result["error"],
        )

    assert result["success"], (
        f"omnia.sh --build failed (rc={result['rc']}, "
        f"duration={result['duration']:.1f}s)\n"
        f"Check the live output above for errors."
    )


# =============================================================================
# 1. INSTALL (TC-1)
# =============================================================================

@pytest.mark.deploy
@pytest.mark.order(1)
def test_omnia_sh_install(host):
    """
    Deploy TC-1: Run omnia.sh --install.

    Steps:
    - Validate NFS configuration
    - Verify omnia.sh script exists
    - Setup internal NFS server (if applicable)
    - Run omnia.sh --install with progress output

    Skips if omnia_core container is already running.
    """
    log = TestLogger(TEST_NAMES["omnia_sh_install"])

    # Skip if container already running
    container_result = check_container_running(host)
    if container_result["success"]:
        print(f"    │ {SKIP_MSGS['container_running']}", flush=True)
        log.skipped(SKIP_MSGS["container_running"])
        pytest.skip(SKIP_MSGS["container_running"])

    # Validate NFS configuration
    print("    ▸ Validating NFS configuration...", flush=True)
    nfs_result = validate_nfs_config()
    if not nfs_result["success"]:
        log.failed(LOG_MSGS["nfs_config_invalid"], nfs_result["error"])
        assert False, ASSERT_MSGS["nfs_config_invalid"].format(
            missing_fields=", ".join(nfs_result.get("missing_fields", []))
        )
    print(f"    ✓ NFS config valid: {nfs_result['share_option']}/{nfs_result['nfs_type'] or 'N/A'}", flush=True)

    # Verify omnia.sh exists
    print("    ▸ Checking omnia.sh...", flush=True)
    sh_result = check_omnia_sh_exists(host)
    if not sh_result["success"]:
        log.failed(LOG_MSGS["download_failed"], sh_result["error"])
        assert False, ASSERT_MSGS["download_failed"].format(error=sh_result["error"])
    print(f"    ✓ Found: {sh_result['path']} ({sh_result['ref_type']})", flush=True)

    # For internal NFS, setup NFS server first
    if OMNIA_SH_VARS["share_option"] == "NFS" and OMNIA_SH_VARS["nfs_type"] == "internal":
        print("    ▸ Setting up internal NFS server...", flush=True)
        nfs_setup_result = setup_internal_nfs_server(host)
        if not nfs_setup_result["success"]:
            log.failed(LOG_MSGS["internal_nfs_failed"], nfs_setup_result["error"])
            pytest.fail(nfs_setup_result["error"])
        print(f"    ✓ {nfs_setup_result['details']}", flush=True)

    # Run omnia.sh --install with progress callback
    print("    ▸ Running omnia.sh --install...", flush=True)

    def _progress(elapsed: int) -> None:
        print(f"    │ Running... {elapsed}s elapsed", flush=True)

    result = run_omnia_sh_install_testinfra(host, progress_callback=_progress)

    if result["success"]:
        output_lines = result["output"].strip().split("\n")
        for line in output_lines:
            print(f"    │ {line}", flush=True)
        details = f"share_option: {nfs_result['share_option']}\nnfs_type: {nfs_result['nfs_type'] or 'N/A'}"
        log.passed(LOG_MSGS["install_success"], details)
    else:
        log.failed(LOG_MSGS["install_failed"], result["error"])

    assert result["success"], ASSERT_MSGS["install_failed"].format(error=result["error"])
