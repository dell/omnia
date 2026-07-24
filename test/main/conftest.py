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
Main Module — Pytest Configuration (Self-Contained).

Provides the ``host`` fixture, test ordering, report hooks, and marker
registration for the FVT (Functional Verification Testing) tests.

Directory layout:
    fvt/                                (Functional Verification Tests)
    ├── omnia_sh_install/               (scenario)
    │   ├── container/                  (functional area: container lifecycle)
    │   │   ├── test_deploy.py          deploy — build + install
    │   │   └── test_verify.py          verify — container, service, metadata
    │   └── security/                   (functional area: SSH/auth)
    │       └── test_ssh.py             verify — SSH connectivity
    ├── omnia_sh_reinstall/             (scenario)
    │   └── container/                  (functional area: container lifecycle)
    │       └── test_deploy.py          deploy — reinstall overwrite
    ├── omnia_sh_uninstall/             (scenario)
    │   └── cleanup/                    (functional area: cleanup)
    │       ├── test_deploy.py          deploy — uninstall
    │       └── test_verify.py          verify — cleanup checks
    nft/                                (Non-Functional Tests — parallel to fvt/)

Suites = functional area folders (container, security, cleanup).
Markers = validation quality categories (IEEE 829 / SDD aligned):
- sanity: Baseline verification after deployment (must-pass gate)
- smoke: Minimal critical-path subset (CI gate)
- regression: Full regression coverage
- functional: Feature-level functional verification
- negative: Invalid input, error handling, boundary conditions
- security: Authentication, authorization, credential tests
- performance: Timing, throughput, resource usage benchmarks

Deploy/verify separation is file-based (handled by run_validation.sh),
not marker-based.  test_deploy.py = execution, others = verification.
"""

import os
import sys
import io
import pytest

# Ensure main/ is importable as a package
_MAIN_ROOT = os.path.dirname(os.path.abspath(__file__))
_TEST_ROOT = os.path.dirname(_MAIN_ROOT)
if _TEST_ROOT not in sys.path:
    sys.path.insert(0, _TEST_ROOT)
if _MAIN_ROOT not in sys.path:
    sys.path.insert(0, _MAIN_ROOT)

from main.library import (
    get_testinfra_host,
    is_local_execution,
    load_test_config,
    encrypt_test_credentials,
    TestReport,
    set_current_report,
    get_current_report,
    get_test_output,
)
from main.library.validation import validate_all, ConfigValidationError


# =============================================================================
# TEE STREAM (capture + print simultaneously)
# =============================================================================

class _TeeStream:
    """Tee stream that writes to both a primary stream and a buffer."""

    def __init__(self, primary, buffer):
        self._primary = primary
        self._buffer = buffer

    def write(self, data):
        """Write to both primary stream and buffer."""
        self._buffer.write(data)
        return self._primary.write(data)

    def flush(self):
        """Flush both streams."""
        try:
            self._buffer.flush()
        except OSError:
            pass
        return self._primary.flush()

    def isatty(self):
        """Check if primary stream is a TTY."""
        isatty_fn = getattr(self._primary, "isatty", None)
        return bool(isatty_fn and isatty_fn())

    @property
    def encoding(self):
        return getattr(self._primary, "encoding", "utf-8")


# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestCollectionWarning"
    )
    config.addinivalue_line(
        "markers",
        "order(n): specify test execution order (lower first)",
    )
    config.addinivalue_line(
        "markers",
        "sanity: Baseline verification after deployment (must-pass)",
    )
    config.addinivalue_line("markers", "smoke: Minimal critical-path subset (CI gate)")
    config.addinivalue_line("markers", "regression: Full regression coverage")
    config.addinivalue_line("markers", "functional: Feature-level functional verification")
    config.addinivalue_line("markers", "negative: Invalid input, error handling, boundary conditions")
    config.addinivalue_line("markers", "security: Authentication, authorization, credential tests")
    config.addinivalue_line("markers", "performance: Timing, throughput, resource usage benchmarks")
    config.addinivalue_line("markers", "stress: Sustained load, concurrency, resource exhaustion")
    config.addinivalue_line("markers", "integration: Cross-component interaction verification")
    config.addinivalue_line("markers", "acceptance: End-to-end user acceptance criteria")


@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(report, _config):
    """Suppress default single-char test status (. s F E)."""
    if report.when == "call":
        if report.passed:
            return "passed", "", "PASSED"
        if report.failed:
            return "failed", "", "FAILED"
    if report.when == "setup" and report.skipped:
        return "skipped", "", "SKIPPED"


def pytest_collection_modifyitems(_session, _config, items):
    """Order tests by @pytest.mark.order(n) then file then function name."""
    def get_order_key(item):
        order_marker = item.get_closest_marker("order")
        if order_marker and order_marker.args:
            return (0, order_marker.args[0], item.fspath.basename, item.name)
        return (1, 0, item.fspath.basename, item.name)

    items.sort(key=get_order_key)


def pytest_sessionstart(_session):
    """Validate config, encrypt credentials, initialize report at session start."""
    # --- Config validation (runs once before any test) ---
    try:
        validate_all()
    except ConfigValidationError as e:
        pytest.exit(str(e), returncode=3)

    try:
        encrypt_test_credentials()
    except (ValueError, OSError):
        pass

    # --- Report ID: env var > test_config.yml > timestamp ---
    module_name = "main"
    report_id = os.environ.get("OMNIA_REPORT_ID")
    if not report_id:
        config = load_test_config()
        report_id = str(config.get("report_id", "")).strip() or None
    report = TestReport(module_name, report_id)
    set_current_report(report)


def pytest_sessionfinish(_session, _exitstatus):
    """Save report at session end."""
    report = get_current_report()
    if report and report.results:
        report.save()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item):
    """Tee stdout/stderr during test execution for report capture."""
    buf = io.StringIO()
    orig_out, orig_err = sys.stdout, sys.stderr
    sys.stdout = _TeeStream(orig_out, buf)
    sys.stderr = _TeeStream(orig_err, buf)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = orig_out, orig_err
        item._omnia_captured_output = buf.getvalue()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, _call):
    """Capture test results and output for the report."""
    outcome = yield
    result = outcome.get_result()

    report = get_current_report()
    if not report:
        return

    if result.when not in {"call", "setup"}:
        return
    if result.when == "setup" and result.outcome != "skipped":
        return

    duration = result.duration if hasattr(result, "duration") else 0
    output = getattr(item, "_omnia_captured_output", None) or get_test_output(item.name)

    skip_reason = None
    if result.outcome == "skipped":
        longrepr = getattr(result, "longrepr", None)
        if isinstance(longrepr, tuple) and len(longrepr) >= 3:
            skip_reason = longrepr[2]
        else:
            skip_reason = str(longrepr) if longrepr else "Skipped"

    if result.outcome == "passed":
        status = "PASSED"
    elif result.outcome == "failed":
        status = "FAILED"
    else:
        status = "SKIPPED"

    error = None
    if status == "FAILED":
        error = str(result.longrepr) if result.longrepr else None

    details = output if output else None
    if status == "SKIPPED" and skip_reason:
        details = (details + "\n" if details else "") + f"SKIPPED: {skip_reason}"

    # Categorize by source file for report grouping
    fspath = str(item.fspath.basename) if hasattr(item, "fspath") else ""
    if "test_deploy" in fspath or "test_reinstall" in fspath:
        category = "deploy"
    else:
        category = "verify"

    # Extract marker names (exclude internal markers like order, parametrize)
    _internal = {
        "order", "parametrize", "usefixtures",
        "filterwarnings", "skip", "skipif", "xfail",
    }
    markers = [
        m.name for m in item.iter_markers()
        if m.name not in _internal
    ]

    # Build full test path for folder breakdown
    test_path = (
        str(item.fspath.relto(item.session.config.rootdir))
        if hasattr(item.fspath, "relto")
        else str(item.fspath)
    )

    report.add_result(
        {
            "test_name": f"{test_path}::{item.name}",
            "status": status,
            "duration": duration,
            "details": details,
            "error": error,
            "category": category,
            "markers": markers,
        },
    )


# =============================================================================
# HOST FIXTURE
# =============================================================================

@pytest.fixture(scope="module")
def host():
    """Testinfra host fixture — connects to OIM server.

    When running on the OIM itself (oim_ip is empty or matches a local IP),
    returns a local testinfra host — no SSH credentials required.
    When running remotely, validates SSH connectivity before returning the host.
    """
    import shutil
    import subprocess as _sp

    config = load_test_config()
    oim_ip = config.get("oim_server_ip", "")

    # Local execution mode
    if is_local_execution():
        h = get_testinfra_host()
        try:
            result = h.run("echo ok")
            if result.rc != 0 or "ok" not in result.stdout:
                pytest.fail(
                    "Local command execution failed. "
                    "Verify that the test user has proper permissions."
                )
        except Exception as e:
            pytest.fail(f"Local command execution failed: {e}")
        return h

    # Remote execution mode
    if not shutil.which("sshpass"):
        pytest.fail(
            "sshpass is not installed. Required for SSH password authentication.\n"
            "Install: dnf install -y sshpass (RHEL) or apt install -y sshpass (Ubuntu)"
        )

    ssh_port = config.get("oim_ssh_port", 22)
    try:
        _sp.run(
            ["bash", "-c", f"echo > /dev/tcp/{oim_ip}/{ssh_port}"],
            capture_output=True, timeout=5, check=True
        )
    except (_sp.CalledProcessError, _sp.TimeoutExpired, OSError):
        pytest.fail(
            f"OIM server {oim_ip}:{ssh_port} is not reachable.\n"
            f"Check oim_ip and oim_ssh_port in test_config.yml"
        )

    h = get_testinfra_host()
    try:
        result = h.run("echo ok")
        if result.rc != 0 or "ok" not in result.stdout:
            stderr = result.stderr.strip() if result.stderr else ""
            pytest.fail(
                f"SSH to OIM server {oim_ip} failed (rc={result.rc}).\n"
                f"Error: {stderr}\n"
                f"Check oim_ssh_user and oim_password in test_config.yml / test_creds.yml"
            )
    except Exception as e:
        pytest.fail(
            f"SSH connection to OIM server {oim_ip} failed: {e}\n"
            f"Check oim_ip, oim_ssh_user, oim_password in test_config.yml / test_creds.yml"
        )

    return h
