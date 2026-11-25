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
OCI Image Ingest — Non-Functional Tests.

Covers TC-NFT-001 through TC-NFT-005 from the ER-UTIL-001 test plan:
  TC-NFT-001: Registry connection validation timeout
  TC-NFT-002: Image transfer elapsed time recorded
  TC-NFT-003: Error phase identification
  TC-NFT-004: Credential security compliance
  TC-NFT-005: Logging completeness
"""

import os
import re
import time

import pytest
import yaml

from library.functions import (
    TestLogger,
    run_on_host,
)
from library.functions.oci_image_ingest_func import (
    check_fault_run,
    credentials_leaked_in,
    latest_completed_run,
    run_fault_scenario,
    get_oci_src_utils_path,
    get_oci_log_path,
    get_oci_output_path,
    validate_build_status,
    validate_oci_config_structure,
    verify_s3_endpoint,
)
from library.vars import (
    TEST_CASES as TC,
    CMDS,
    OCI_CREDENTIAL_FIELDS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# TC-NFT-001: Registry connection validation timeout
# =============================================================================

# Production waits the whole connect timeout, then logs the failure; the log span
# also covers the task start-up before the connection attempt (~1 s measured).
OVERHEAD_ALLOWANCE_S = 5


def _log_time(line):
    from datetime import datetime
    return datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")


@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(901)
def test_nft_registry_connection_timeout(host):
    """Production registry validation fails an unreachable registry within 30 s.

    Runs the production pipeline with the registry hostname set to an RFC 5737
    TEST-NET address and measures, from the production ingest log, the time from
    credential validation to the recorded failure of the connection phase. Also
    checks the production default connect timeout is <= 30 s. The production role
    waits the full timeout, so the measured span is the timeout plus ~1 s of task
    overhead; the assertion allows OVERHEAD_ALLOWANCE_S for that.
    """
    tc = TC["nft_registry_connection_timeout"]
    tl = TestLogger(tc["title"], tc["id"])

    src = get_oci_src_utils_path(host)
    defaults = run_on_host(
        host, f"cat {src}/roles/validate_registry_connection/defaults/main.yml").stdout
    configured = yaml.safe_load(defaults)["oci_ingest_connect_timeout"]
    assert int(configured) <= 30, f"production connect timeout {configured}s exceeds 30s"

    run = run_fault_scenario(host, "registry_unreachable")
    if run["skipped"]:
        tl.skipped(run["skipped"])
        pytest.skip(run["skipped"])
    errors = check_fault_run(run, "connection", ["Registry connection failed"])
    assert not errors, "; ".join(errors)

    stamps = [(_log_time(l), l) for l in run["log"]]
    begin = next(t for t, l in stamps if "credentials validated" in l)
    end = next(t for t, l in stamps if " - ERROR - " in l and "run failed" in l)
    elapsed = (end - begin).total_seconds()
    assert elapsed <= int(configured) + OVERHEAD_ALLOWANCE_S, (
        f"connection-phase failure took {elapsed:.1f}s "
        f"(production timeout {configured}s + {OVERHEAD_ALLOWANCE_S}s overhead allowance)"
    )

    tl.passed(
        f"Unreachable registry failed the connection phase in {elapsed:.1f}s "
        f"(production timeout {configured}s)"
    )


@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(902)
def test_nft_transfer_elapsed_time_recorded(host):
    """Elapsed time is recorded in the production log for every ingested mapping.

    Reads the most recent completed run from the production ingest log and checks
    that each mapping's result line carries elapsed_seconds, non-decreasing across
    mappings and within the run. The production code logs one cumulative value per
    mapping (not separate pull/extract/squashfs/upload durations), so that is what
    is asserted here.
    """
    tc = TC["nft_transfer_elapsed_time"]
    tl = TestLogger(tc["title"], tc["id"])

    run = latest_completed_run(host)
    if not run:
        tl.skipped("No completed ingest run in the production log")
        pytest.skip("No completed ingest run in the production log")

    mappings = int(re.search(r"mappings=(\d+)", run[0]).group(1))
    results = [l for l in run if re.search(r"mapping=\S+ result=", l)]
    assert len(results) == mappings, f"{len(results)} result lines for {mappings} mappings"
    elapsed = []
    for line in results:
        match = re.search(r"elapsed_seconds=(\d+)", line)
        assert match, f"no elapsed_seconds in: {line[:160]}"
        elapsed.append(int(match.group(1)))
    assert elapsed == sorted(elapsed), f"elapsed_seconds not monotonic: {elapsed}"
    total = (_log_time(run[-1]) - _log_time(run[0])).total_seconds()
    assert elapsed[-1] <= total + 1, f"elapsed {elapsed[-1]}s exceeds logged run time {total:.0f}s"

    tl.passed(f"elapsed_seconds recorded for {mappings} mapping(s): {elapsed}")


@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(903)
def test_nft_error_phase_identification(host):
    """Induced failures report the failing phase without leaking credentials.

    Runs the five production fault scenarios (connection, pull, materialization and
    two upload faults) and asserts each failure is attributed to its phase in the
    playbook output and ingest log, and that no stored registry credential value
    appears in either.
    """
    tc = TC["nft_error_phase_identification"]
    tl = TestLogger(tc["title"], tc["id"])

    scenarios = {
        "registry_unreachable": ("connection", "Registry connection failed"),
        "storage": ("pull", "Insufficient free space"),
        "mksquashfs": ("materialization", "mksquashfs failed"),
        "s3_unreachable": ("upload", "S3 upload failed"),
        "s3_partial": ("upload", "S3 upload failed"),
    }
    seen = []
    for name, (phase, message) in scenarios.items():
        run = run_fault_scenario(host, name)
        if run["skipped"]:
            tl.skipped(run["skipped"])
            pytest.skip(run["skipped"])
        errors = check_fault_run(run, phase, [message])
        assert not errors, f"{name}: {'; '.join(errors)}"
        assert not credentials_leaked_in(host, run["output"] + "\n" + "\n".join(run["log"])), (
            f"{name}: stored registry credential value found in output or log"
        )
        seen.append(phase)

    tl.passed(f"Phase-attributed failures without credential leakage: {', '.join(seen)}")


@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(904)
def test_nft_credential_security_compliance(host):
    """Verify credential security: Vault encryption, file permissions, no leakage.

    Checks:
    1. Credential file has 0600 permissions.
    2. Credential file is Vault-encrypted.
    3. Zero credential values in all non-Vault output paths.
    """
    tc = TC["nft_credential_security"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import get_oci_credentials_path
    cred_path = get_oci_credentials_path(host)

    # 1. Check file permissions (0600)
    perm_result = run_on_host(
        host,
        CMDS["file_permissions"].format(path=cred_path),
    )
    perms = perm_result.stdout.strip()
    assert perms == "600", (
        f"Credential file permissions should be 600, got {perms}"
    )

    # 2. Check Vault encryption
    header_result = run_on_host(
        host,
        CMDS["head_file"].format(n=1, path=cred_path),
    )
    header = header_result.stdout.strip()
    assert "$ANSIBLE_VAULT" in header, (
        f"Credential file not Vault-encrypted: header = {header}"
    )

    # 3. Scan all output paths for credential leakage
    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)
    leaked = []
    for pattern in OCI_CREDENTIAL_FIELDS:
        for scan_path in [output_path, log_path]:
            cmd = CMDS["credential_scan"].format(
                pattern=pattern, path=scan_path
            )
            result = run_on_host(host, cmd)
            if result.stdout.strip() and "clean" not in result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        leaked.append(f"{pattern} in {line.strip()}")

    assert not leaked, f"Credential leakage detected: {leaked}"

    tl.passed(
        f"Credential file: perms={perms}, Vault-encrypted; "
        f"zero credential leakage in outputs"
    )


# =============================================================================
# TC-NFT-005: Logging completeness
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(905)
def test_nft_logging_completeness(host):
    """The production ingest log records every required operational field.

    For the most recent completed run: endpoint, namespace, image reference, digest,
    operation, S3 endpoint/prefix, artifact names, sizes and SHA-256 checksums, and
    elapsed time must all be logged, and no stored credential value may appear.
    """
    tc = TC["nft_logging_completeness"]
    tl = TestLogger(tc["title"], tc["id"])

    run = latest_completed_run(host)
    if not run:
        tl.skipped("No completed ingest run in the production log")
        pytest.skip("No completed ingest run in the production log")
    text = "\n".join(run)

    required = {
        "run start": r"run started: project=\S+ run_id=\S+ registries=\S+ mappings=\d+ s3_endpoint=https?://\S+",
        "registry endpoint": r"registry validated: endpoint=\S+ protocol=\S+ namespaces=\S+",
        "namespace/image/digest/operation": (
            r"mapping=\S+ registry=\S+ namespace=\S+ image=\S+ digest=sha256:[0-9a-f]{64} "
            r"platform=\S+ operation=repo_to_bucket"),
        "S3 prefix": r"s3_prefix=\S+/\S+-ingest/\S+",
        "artifact size": r'"size_bytes": \d+',
        "artifact checksum": r'"sha256": "[0-9a-f]{64}"',
        "elapsed time": r"elapsed_seconds=\d+",
        "build status path": r"build_status.yml written: path=\S+",
    }
    missing = [k for k, pat in required.items() if not re.search(pat, text)]
    assert not missing, f"production log missing: {missing}"
    names = set(re.findall(r'"name": "([^"]+)"', text))
    for prefix in ("vmlinuz-", "initramfs-", "rootfs.squashfs"):
        assert any(n.startswith(prefix) for n in names), f"no {prefix} artifact logged"
    assert not credentials_leaked_in(host, text), "stored credential value found in the log"

    tl.passed(f"All {len(required)} operational fields logged; no credentials logged")
