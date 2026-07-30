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
omnia.sh --reinstall / Container — Reinstall Deploy Tests.

Tests the reinstall path of ``omnia.sh --install`` when the omnia_core
container is **already running** (Reinstall → Overwrite path).

Test cases:
    TC_RI_001  Reinstall omnia_core via overwrite path

Usage:
    run_validation omnia_sh_reinstall deploy
"""

import pytest

from main.library import (
    TestLogger,
    PlaybookRunner,
    OMNIA_SH_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
    check_container_running,
    check_omnia_sh_exists,
    validate_current_dataset,
    validate_nfs_config,
)


# =============================================================================
# HELPER: Build reinstall-overwrite input sequence
# =============================================================================

def _build_reinstall_overwrite_inputs() -> str:
    """Build the input sequence for reinstall → overwrite → fresh install.

    When omnia_core is already running, ``omnia.sh --install`` shows:
        select: (1) Enter  (2) Reinstall  (3) Exit → we send "2"
        select: (1) Retain (2) Overwrite  (3) Exit → we send "2"
        confirm cleanup: y/n                       → we send "y"
        … then the full fresh install prompts follow (same as test_deploy.py)

    Returns:
        Multi-line string for piping to omnia.sh --install.
    """
    share_option = OMNIA_SH_VARS["share_option"]
    nfs_type_val = OMNIA_SH_VARS["nfs_type"]

    inputs = []

    # --- Reinstall menu ---
    inputs.append("2")  # select: Reinstall the container
    inputs.append("2")  # select: Overwrite and create new configuration
    inputs.append("y")  # confirm: cleanup

    # --- Fresh install prompts (same as test_deploy._build_fresh_install_inputs) ---
    if share_option == "NFS":
        inputs.append("1")  # select: NFS
        if nfs_type_val == "external":
            inputs.append("1")  # select: External
            inputs.append(OMNIA_SH_VARS.get("nfs_server_ip", ""))
            inputs.append(OMNIA_SH_VARS.get("nfs_share_path", ""))
            inputs.append(OMNIA_SH_VARS.get("omnia_shared_path", ""))
        else:  # internal
            inputs.append("2")  # select: Internal
            oim = OMNIA_SH_VARS.get("oim_server_ip", "") or "localhost"
            inputs.append(oim)
            inputs.append(OMNIA_SH_VARS.get("nfs_share_path", ""))
    else:  # Local
        inputs.append("2")  # select: Local
        inputs.append(OMNIA_SH_VARS.get("omnia_shared_path", ""))

    # --- Admin NIC IP (prompted before password in omnia.sh) ---
    inputs.append(OMNIA_SH_VARS.get("admin_nic_ip", ""))

    # --- Password + confirm ---
    password = OMNIA_SH_VARS.get("omnia_core_password", "")
    inputs.append(password)
    inputs.append(password)

    return "\n".join(inputs)


def _shell_quote_lines(data: str) -> str:
    """Convert multi-line data into shell-safe quoted printf arguments."""
    parts = []
    for line in data.split("\n"):
        escaped = line.replace("'", "'\\''")
        parts.append(f"'{escaped}'")
    return " ".join(parts)


# =============================================================================
# 0. REINSTALL — OVERWRITE (TC-0) — LIVE STREAMING
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(0)
def test_omnia_sh_reinstall_overwrite(host):
    """TC_RI_001: Run omnia.sh --install → Reinstall → Overwrite."""
    source = OMNIA_SH_VARS.get("_source", "test_config.yml")
    log = TestLogger("[TC_RI_001] Reinstall: omnia.sh --install (overwrite)")

    # ── Gate: container MUST be running ─────────────────────────────
    container_result = check_container_running(host)
    if not container_result["success"]:
        log.skipped(
            "omnia_core container is NOT running — reinstall requires "
            "a running container.\n"
            "  For fresh install: run_validation main install deploy"
        )
        pytest.skip(
            "omnia_core container is not running. "
            "Use 'install deploy' for fresh install."
        )

    # ── 1. Validate storage parameters ──────────────────────────────
    log.check("Validating storage parameters...")
    try:
        validate_current_dataset()
    except ValueError as e:
        log.failed("Storage parameter validation failed", str(e))
        pytest.fail(str(e))
    log.passed(f"Storage parameters valid (source: {source})")

    # ── 2. Validate NFS configuration ───────────────────────────────
    log.check("Validating storage configuration...")
    nfs_result = validate_nfs_config()
    if not nfs_result["success"]:
        log.failed(LOG_MSGS["nfs_config_invalid"], nfs_result["error"])
        pytest.fail(nfs_result["error"])
    log.passed(
        f"Config valid: {nfs_result['share_option']}"
        f"/{nfs_result['nfs_type'] or 'N/A'}"
    )

    # ── 3. Verify omnia.sh exists ───────────────────────────────────
    log.check("Checking omnia.sh...")
    sh_result = check_omnia_sh_exists(host)
    if not sh_result["success"]:
        log.failed("omnia.sh not found", sh_result["error"])
        pytest.fail(sh_result["error"])
    log.passed(f"Found: {sh_result['path']} ({sh_result['ref_type']})")

    # ── 4. Build input sequence and run ─────────────────────────────
    input_data = _build_reinstall_overwrite_inputs()
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]

    log.check("Running omnia.sh --install (reinstall → overwrite)...")
    runner = PlaybookRunner()

    install_cmd = (
        f"bash {omnia_sh_path} --install "
        f"< <(printf '%s\\n' {_shell_quote_lines(input_data)}; sleep 1)"
    )

    result = runner.run_shell(
        install_cmd,
        label="omnia.sh --install (reinstall-overwrite)",
        timeout=OMNIA_SH_VARS.get("install_timeout", 600),
    )

    # ── 5. Assert success ───────────────────────────────────────────
    if result["success"]:
        details = (
            f"share_option: {nfs_result['share_option']}\n"
            f"nfs_type: {nfs_result['nfs_type'] or 'N/A'}\n"
            f"source: {source}"
        )
        log.passed("Reinstall (overwrite) completed successfully", details)
    else:
        log.failed("Reinstall (overwrite) failed", result["error"])

    assert result["success"], (
        f"omnia.sh --install (reinstall-overwrite) failed.\n"
        f"{result['error']}"
    )
