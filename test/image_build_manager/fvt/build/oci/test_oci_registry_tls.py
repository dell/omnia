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
Image Build Build — external OCI registry TLS and secret verification.

Runs against the disposable TLS and auth lab registry (OMNIA_OCI_LAB_* settings):
  TC-FVT-013: TLS is verified by default, a custom CA is used by the precheck and the
              session push configuration, and tls_verify false is an explicit opt-out
  TC-FVT-012: a robot acct with '$' and '+' is used exactly, a rejected secret fails
              without leaking, and the session configuration is removed after the run
"""

import pytest

from library.functions import TestLogger
from library.functions.oci_registry_probe_func import (
    LAB_HOST,
    LAB_PORT,
    lab_available,
    lab_credentials,
    lab_registry,
    LAB_CA_FILE,
    new_secret,
    parse_session_state,
    run_probe,
    run_validate,
    session_removed,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

ROBOT_NAME = "robot$omnia+buildstream"


def _lab_or_skip(tl: TestLogger):
    if not lab_available():
        tl.skipped(LOG["oci_probe_skipped"])
        pytest.skip(LOG["oci_probe_skipped"])
    creds = lab_credentials()
    if creds is None:
        tl.skipped(LOG["oci_probe_skipped"])
        pytest.skip(LOG["oci_probe_skipped"])
    return creds


def _report(tl: TestLogger, ok: bool, ok_detail: str, expected: str, observed: str) -> None:
    if ok:
        tl.passed(LOG["oci_probe_ok"].format(detail=ok_detail))
    else:
        tl.failed(LOG["oci_probe_failed"].format(expected=expected, observed=observed))


@pytest.mark.sanity
@pytest.mark.order(7)
def test_tls_default_rejects_untrusted_certificate(tmp_path):
    """TLS verification is enforced by default and names the registry host."""
    tc = TC["oci_tls_default_verify"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)

    result = run_probe(tmp_path, "precheck", lab_registry(), acct, secret)
    expected = f"TLS verification failed for https://{LAB_HOST}:{LAB_PORT}"
    ok = (not result["success"]) and expected in result["output"]
    _report(tl, ok, "untrusted certificate rejected with a TLS error", expected,
            "precheck passed" if result["success"] else "failure without the TLS message")
    assert ok, ASSERT["oci_probe_assert"].format(detail=expected)


@pytest.mark.sanity
@pytest.mark.order(8)
def test_custom_ca_used_by_precheck_and_push(tmp_path):
    """The configured CA is trusted by the precheck and by the session push configuration."""
    tc = TC["oci_tls_custom_ca"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)

    result = run_probe(tmp_path, "session", lab_registry(ca_cert_path=LAB_CA_FILE), acct, secret)
    state = parse_session_state(result["output"]) or {}
    ok = (result["success"] and state.get("regctl_rc") == 0
          and state.get("user_exact") is True)
    _report(tl, ok, "custom CA accepted by the precheck and the session regctl read",
            "precheck passes and regctl reads the registry with the CA",
            f"success={result['success']} state={state}")
    assert ok, ASSERT["oci_probe_assert"].format(detail=str(state))


@pytest.mark.sanity
@pytest.mark.order(9)
def test_tls_disabled_is_explicit_opt_out(tmp_path):
    """tls_verify false skips verification and the validation log records the warning."""
    tc = TC["oci_tls_disabled_warns"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)

    probe = run_probe(
        tmp_path / "probe", "precheck", lab_registry(tls_verify=False), acct, secret
    )
    validate = run_validate(tmp_path / "validate", lab_registry(tls_verify=False))
    ok = (probe["success"] and validate["success"]
          and "TLS verification is disabled" in validate["logged"])
    _report(tl, ok, "verification skipped with the warning logged",
            "untrusted certificate accepted with tls_verify false and the validation log warns",
            f"probe={probe['success']} validate={validate['success']} "
            f"warning_logged={'TLS verification is disabled' in validate['logged']}")
    assert ok, ASSERT["oci_probe_assert"].format(detail="tls_verify false opt-out")


@pytest.mark.sanity
@pytest.mark.order(10)
def test_robot_account_name_used_exactly(tmp_path):
    """A robot acct name with '$' and '+' is stored and used exactly as configured."""
    tc = TC["oci_robot_account_exact"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)
    if acct != ROBOT_NAME:
        tl.skipped(LOG["oci_probe_skipped"])
        pytest.skip(LOG["oci_probe_skipped"])

    result = run_probe(tmp_path, "session", lab_registry(ca_cert_path=LAB_CA_FILE), acct, secret)
    state = parse_session_state(result["output"]) or {}
    ok = result["success"] and state.get("user_exact") is True and state.get("regctl_rc") == 0
    _report(tl, ok, "robot acct name matches the configuration and authenticates",
            "user_exact True and regctl reads the registry",
            f"success={result['success']} state={state}")
    assert ok, ASSERT["oci_probe_assert"].format(detail=str(state))


@pytest.mark.sanity
@pytest.mark.order(11)
def test_rejected_secret_fails_without_leak(tmp_path):
    """A rejected secret fails with the auth error class and never appears in the output."""
    tc = TC["oci_wrong_secret_auth_error"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, _ = _lab_or_skip(tl)
    wrong = new_secret()

    result = run_probe(tmp_path, "precheck", lab_registry(ca_cert_path=LAB_CA_FILE), acct, wrong)
    expected = f"authentication failed (phase: precheck) for acct {acct} at https://{LAB_HOST}:{LAB_PORT}"
    ok = (not result["success"]) and expected in result["output"] and wrong not in result["output"]
    _report(tl, ok, "auth error class reported and no secret in output",
            expected + " without the secret",
            "output missing the auth message or leaked the secret")
    assert ok, ASSERT["oci_probe_assert"].format(detail=expected)


@pytest.mark.sanity
@pytest.mark.order(12)
def test_session_configuration_removed_after_run(tmp_path):
    """The temporary regctl configuration is deleted when the session run ends."""
    tc = TC["oci_session_config_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    acct, secret = _lab_or_skip(tl)

    result = run_probe(tmp_path, "session", lab_registry(ca_cert_path=LAB_CA_FILE), acct, secret)
    removed = session_removed(result["output"])
    ok = result["success"] and removed is True
    _report(tl, ok, "session regctl configuration removed",
            "PROBE_REMOVED exists=False", f"success={result['success']} removed={removed}")
    assert ok, ASSERT["oci_probe_assert"].format(detail="session configuration removal")
