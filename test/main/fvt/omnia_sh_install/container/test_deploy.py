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
omnia.sh --install / Container — Fresh Install Deploy Tests.

Performs a fresh ``omnia.sh --install`` when no omnia_core container exists.

Test cases:
    TC_IT_001  Build omnia_core container image (omnia.sh --build)
    TC_IT_002  Run omnia.sh --install (fresh install)

For reinstall, see ``test_reinstall.py`` (marker: @reinstall).

Usage:
    run_validation omnia_sh_install deploy
    run_validation omnia_sh_install test
"""

import pytest

from main.library import (
    TestLogger,
    PlaybookRunner,
    OMNIA_SH_VARS,
    TEST_NAMES,
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
    SKIP_MSGS,
    validate_current_dataset,
    check_container_running,
    check_omnia_sh_exists,
    validate_nfs_config,
    setup_internal_nfs_server,
    run_on_oim,
)
from main.library.vars.common_vars import CMDS

from main.library.vars.omnia_sh_vars import OMNIA_SH_VARS as _VARS

BUILD_TIMEOUT = _VARS.get("build_timeout", 1800)


# =============================================================================
# HELPER: Build fresh-install input sequence
# =============================================================================

def _build_fresh_install_inputs() -> str:
    """Build the input sequence for a fresh omnia.sh --install.

    The omnia.sh script uses ``select`` (bash) and ``read`` prompts.
    ``select`` expects line numbers (1, 2, …) not option text.

    Fresh install prompt order:
        1. Storage type select   → "1" (NFS) or "2" (Local)
        2a. [NFS] NFS type select → "1" (External) or "2" (Internal)
        2b. [NFS External] NFS server IP, share path, mount point
        2c. [NFS Internal] OIM IP, share path
        2d. [Local] omnia shared path
        3. Admin NIC IP          → IP address
        4. Password              → password text
        5. Confirm password      → password text (repeated)

    Returns:
        Multi-line string ready to pipe via ``< <(echo "…")``.
    """
    share_option = OMNIA_SH_VARS["share_option"]
    nfs_type_val = OMNIA_SH_VARS["nfs_type"]

    inputs = []

    # --- Storage type ---
    if share_option == "NFS":
        inputs.append("1")                                     # select: NFS
        if nfs_type_val == "external":
            inputs.append("1")                                 # select: External
            inputs.append(OMNIA_SH_VARS.get("nfs_server_ip", ""))
            inputs.append(OMNIA_SH_VARS.get("nfs_share_path", ""))
            inputs.append(OMNIA_SH_VARS.get("omnia_shared_path", ""))
        else:                                                  # internal
            inputs.append("2")                                 # select: Internal
            oim = OMNIA_SH_VARS.get("oim_server_ip", "") or "localhost"
            inputs.append(oim)
            inputs.append(OMNIA_SH_VARS.get("nfs_share_path", ""))
    else:                                                      # Local
        inputs.append("2")                                     # select: Local
        inputs.append(OMNIA_SH_VARS.get("omnia_shared_path", ""))

    # --- Admin NIC IP (prompted before password in omnia.sh) ---
    inputs.append(OMNIA_SH_VARS.get("admin_nic_ip", ""))

    # --- Password + confirm ---
    password = OMNIA_SH_VARS.get("omnia_core_password", "")
    inputs.append(password)
    inputs.append(password)

    return "\n".join(inputs)


# =============================================================================
# 0. BUILD IMAGES (TC-0) — LIVE STREAMING
# =============================================================================

@pytest.mark.order(0)
def test_build_container_images(host):
    """
    TC_IT_001: Build omnia_core container image via omnia.sh --build.
    """
    log = TestLogger("[TC_IT_001] Deploy: Build container images")

    # Skip if container already running and not force_rebuild
    container_result = check_container_running(host)
    if container_result["success"] and not OMNIA_SH_VARS.get("force_rebuild", True):
        log.skipped(SKIP_MSGS["container_running"])
        pytest.skip(SKIP_MSGS["container_running"])

    # Verify omnia.sh exists
    omnia_sh = OMNIA_SH_VARS["omnia_sh_path"]
    log.check(f"Checking omnia.sh at {omnia_sh}")
    sh_result = check_omnia_sh_exists(host)
    assert sh_result["success"], f"omnia.sh not found at {omnia_sh}"

    # Run omnia.sh --build with live streaming output
    runner = PlaybookRunner()
    result = runner.run_shell(
        f"bash {omnia_sh} --build",
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
# 1. FRESH INSTALL (TC-1) — LIVE STREAMING
# =============================================================================

@pytest.mark.order(1)
def test_omnia_sh_install(host):
    """
    TC_IT_002: Run omnia.sh --install (fresh install).
    """
    source = OMNIA_SH_VARS.get("_source", "test_config.yml")
    log = TestLogger("[TC_IT_002] " + TEST_NAMES["omnia_sh_install"])

    # ── Gate: container must NOT be running ──────────────────────────
    container_result = check_container_running(host)
    if container_result["success"]:
        log.skipped(
            "omnia_core container is already running — fresh install "
            "cannot proceed.\n"
            "  To reinstall: run_validation main uninstall deploy  first,\n"
            "  or use:       run_validation main install test --marker reinstall"
        )
        pytest.skip(
            "omnia_core container is already running. "
            "Run 'uninstall deploy' first or use --marker reinstall."
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
        pytest.fail(ASSERT_MSGS["nfs_config_invalid"].format(
            missing_fields=", ".join(nfs_result.get("missing_fields", []))
        ))
    log.passed(
        f"Config valid: {nfs_result['share_option']}"
        f"/{nfs_result['nfs_type'] or 'N/A'}"
    )

    # ── 3. Verify omnia.sh exists ───────────────────────────────────
    log.check("Checking omnia.sh...")
    sh_result = check_omnia_sh_exists(host)
    if not sh_result["success"]:
        log.failed(LOG_MSGS["download_failed"], sh_result["error"])
        assert False, ASSERT_MSGS["download_failed"].format(
            error=sh_result["error"]
        )
    log.passed(f"Found: {sh_result['path']} ({sh_result['ref_type']})")

    # ── 4. Internal NFS setup ───────────────────────────────────────
    if (OMNIA_SH_VARS["share_option"] == "NFS"
            and OMNIA_SH_VARS["nfs_type"] == "internal"):
        log.check("Setting up internal NFS server...")
        nfs_setup = setup_internal_nfs_server(host)
        if not nfs_setup["success"]:
            log.failed(LOG_MSGS["internal_nfs_failed"], nfs_setup["error"])
            pytest.fail(nfs_setup["error"])
        log.passed(nfs_setup["details"])

    # ── 5. NFS server reachability (external) ───────────────────────
    if (nfs_result["share_option"] == "NFS"
            and nfs_result.get("nfs_type") == "external"):
        nfs_ip = OMNIA_SH_VARS.get("nfs_server_ip", "")
        log.check(f"Checking NFS server reachability: {nfs_ip}")
        ping = run_on_oim(host, CMDS["ping_host"].format(host=nfs_ip))
        if ping.rc != 0:
            log.failed(
                f"NFS server {nfs_ip} is not reachable",
                f"Ensure the NFS server is online.\nConfig: {source}",
            )
            pytest.fail(f"NFS server {nfs_ip} is not reachable.")
        log.passed(f"NFS server {nfs_ip} is reachable")

    # ── 6. Build input sequence and run ─────────────────────────────
    input_data = _build_fresh_install_inputs()
    omnia_sh_path = OMNIA_SH_VARS["omnia_sh_path"]

    log.check("Running omnia.sh --install...")
    runner = PlaybookRunner()

    # Pipe inputs via process-substitution; close stdin after so the
    # trailing ``ssh omnia_core`` inside omnia.sh exits immediately
    # instead of consuming leftover input.
    install_cmd = (
        f"bash {omnia_sh_path} --install "
        f"< <(printf '%s\\n' {_shell_quote_lines(input_data)}; sleep 1)"
    )

    result = runner.run_shell(
        install_cmd,
        label="omnia.sh --install",
        timeout=OMNIA_SH_VARS.get("install_timeout", 600),
    )

    # ── 7. Assert success ───────────────────────────────────────────
    if result["success"]:
        details = (
            f"share_option: {nfs_result['share_option']}\n"
            f"nfs_type: {nfs_result['nfs_type'] or 'N/A'}\n"
            f"source: {source}"
        )
        log.passed(LOG_MSGS["install_success"], details)
    else:
        log.failed(LOG_MSGS["install_failed"], result["error"])

    assert result["success"], ASSERT_MSGS["install_failed"].format(
        error=result["error"]
    )


# =============================================================================
# HELPER: Shell-safe quoting for printf
# =============================================================================

def _shell_quote_lines(data: str) -> str:
    """Convert multi-line input data into shell-safe quoted arguments.

    Each line becomes a separate quoted argument so ``printf '%s\\n'``
    prints them one per line.  Single quotes inside values are escaped.
    """
    parts = []
    for line in data.split("\n"):
        escaped = line.replace("'", "'\\''")
        parts.append(f"'{escaped}'")
    return " ".join(parts)
