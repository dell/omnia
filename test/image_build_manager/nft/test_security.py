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
Image Build Manager — Non-Functional Security Tests.

Regression guards for the CWE-732 / CWE-522 hardening that restricts
secret-bearing files to root-only access (0600, root:root). A future
accidental revert to a world-readable mode will fail one of these cases.

Cases:
  IMGBM_NFT_SECURITY_001 — /etc/containers/systemd/minio.container 0600 root:root
  IMGBM_NFT_SECURITY_002 — /root/.s3cfg 0600 root:root
  IMGBM_NFT_SECURITY_003 — no *.container under /etc/containers/systemd/ is o+r
  IMGBM_NFT_SECURITY_004 — registry secret canary absent from probe output
  IMGBM_NFT_SECURITY_005 — session regctl configuration is 0600 root-owned and removed
  IMGBM_NFT_SECURITY_006 — unsafe registry host or namespace rejected before any command
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_permissions,
)
from library.functions.oci_registry_probe_func import (
    LAB_CA_FILE,
    LAB_HOST,
    find_leaks,
    lab_available,
    lab_credentials,
    lab_registry,
    new_secret,
    parse_session_state,
    run_probe,
    run_validate,
    session_removed,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


MINIO_QUADLET_PATH = "/etc/containers/systemd/minio.container"
S3CFG_PATH = "/root/.s3cfg"


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(10)
def test_minio_quadlet_permissions(host):
    """MinIO quadlet must be 0600 root:root (contains S3 credentials)."""
    tc = TC["minio_quadlet_permissions"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_file_permissions(
        host, MINIO_QUADLET_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(11)
def test_s3cfg_permissions(host):
    """/root/.s3cfg must be 0600 root:root (contains MinIO access key/secret)."""
    tc = TC["s3cfg_permissions"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_file_permissions(
        host, S3CFG_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["details"])

    assert result["success"], result["details"]


def _lab_or_skip(tl: TestLogger):
    if not lab_available() or lab_credentials() is None:
        tl.skipped(LOG["oci_probe_skipped"])
        pytest.skip(LOG["oci_probe_skipped"])
    return lab_credentials()


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(12)
def test_credential_canary_absent(tmp_path):
    """The registry password never appears in probe output, on success or failure."""
    tc = TC["oci_credential_canary"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)
    wrong = new_secret()

    registry = lab_registry(ca_cert_path=LAB_CA_FILE)
    failed = run_probe(tmp_path / "fail", "precheck", registry, acct, wrong)
    passed = run_probe(tmp_path / "pass", "session", registry, acct, secret)
    leaked = [name for name, text, value in (
        ("failure output", failed["output"], wrong),
        ("success output", passed["output"], secret),
    ) if find_leaks(text, value)]
    negative_control = find_leaks(f"auth failed for {wrong}", wrong)

    ok = not leaked and negative_control and LAB_HOST in failed["output"]
    if ok:
        tl.passed(LOG["oci_canary_ok"])
    else:
        found = ", ".join(leaked) or "control not detected"
        tl.failed(LOG["oci_canary_failed"].format(artifacts=found))
    assert ok, ASSERT["oci_canary_assert"].format(artifacts=", ".join(leaked) or "control")


def _is_protected(mode: str, owner: str) -> bool:
    return mode == "0600" and owner == "root"


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(13)
def test_session_configuration_protected(tmp_path):
    """The session regctl configuration is 0600, root-owned, and removed after the run."""
    tc = TC["oci_temp_config_lifecycle"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)

    result = run_probe(tmp_path, "session", lab_registry(ca_cert_path=LAB_CA_FILE), acct, secret)
    state = parse_session_state(result["output"]) or {}
    removed = session_removed(result["output"])
    ok = (result["success"] and _is_protected(state.get("mode", ""), state.get("owner", ""))
          and removed is True)
    if ok:
        tl.passed(LOG["oci_temp_config_ok"])
    else:
        tl.failed(LOG["oci_temp_config_failed"].format(state=state, removed=removed))
    assert ok, ASSERT["oci_temp_config_assert"].format(state=state, removed=removed)


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(14)
@pytest.mark.parametrize("field,value", [
    ("registry_hostname", "oim;reboot"),
    ("registry_hostname", "oim.omnia.cluster/../x"),
    ("namespace_name", "omnia/../other"),
    ("namespace_name", "omnia$(id)"),
], ids=["host_semicolon", "host_traversal", "namespace_traversal", "namespace_subshell"])
def test_unsafe_registry_input_rejected(tmp_path, field, value):
    """Unsafe host or namespace values are rejected by validation before any command runs."""
    tc = TC["oci_input_safety"]
    tl = TestLogger(f"{tc['title']} ({field}={value})", tc["id"])
    result = run_validate(tmp_path, {field: value})

    rejected = (not result["success"]) and field in result["output"]
    no_command = "regctl" not in result["output"]
    ok = rejected and no_command
    if ok:
        tl.passed(LOG["oci_input_ok"].format(field=field))
    else:
        tl.failed(LOG["oci_input_failed"].format(field=field))
    assert ok, ASSERT["oci_input_assert"].format(field=field)
