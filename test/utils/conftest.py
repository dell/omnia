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
Pytest configuration for utils domain FVT.

Provides:
- host fixture (testinfra connection to target)
- Custom markers: sanity, functional, deploy
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- Credential auto-encryption
- Remote clone and dataset sync on session startup
"""

import sys
import os

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# --- Initialize omnia_auto BEFORE any imports that use it ---
import omnia_auto
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)

# --- Common functions from omnia_auto ---
from omnia_auto import (
    get_testinfra_host,
    is_local_execution,
    load_test_config,
    TestReport,
    set_current_report,
    get_current_report,
    get_test_output,
    get_last_tc_id,
    encrypt_test_credentials,
    log,
    add_session_result,
    print_summary_table,
)

# --- Module-specific functions ---
from library.functions.host_func import (
    sync_project_to_remote,
    sync_utils_input,
    sync_install_os_credentials,
)
from library.functions.utils_func import (
    check_target_connectivity,
)
from library.functions.validation_func import (
    validate_all,
    ConfigValidationError,
)
from library.vars import TEST_CASES

# Build test-function-name → TC ID map for summary table fallback.
_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}


# =============================================================================
# CUSTOM CLI OPTIONS
# =============================================================================

def pytest_addoption(parser):
    """Add --marker option for custom marker expression filtering."""
    parser.addoption(
        "--marker",
        action="store",
        default="",
        help=(
            "Marker filter expression. "
            "Use '+' for AND (both required): sanity+deploy. "
            "Use ',' for OR (either matches): collect,pxe."
        ),
    )


# =============================================================================
# MARKER REGISTRATION
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestCollectionWarning"
    )
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "regression": "Regression tests",
        "deploy": "Playbook deployment tests",
        "collect": "Log collector tests",
        "pxe": "PXE boot tests",
        "install_os": "OS installation tests",
    }
    for name, desc in markers.items():
        config.addinivalue_line("markers", f"{name}: {desc}")


# =============================================================================
# MARKER EXPRESSION FILTERING
# =============================================================================

def _parse_marker_expression(expr):
    """Parse marker expression into (mode, marker_list)."""
    expr = expr.strip()
    if not expr:
        return ("none", [])
    if "+" in expr:
        return ("and", [m.strip() for m in expr.split("+")])
    if "," in expr:
        return ("or", [m.strip() for m in expr.split(",")])
    return ("single", [expr])


def _item_has_marker(item, marker_name):
    """Check if a test item has a specific marker."""
    return item.get_closest_marker(marker_name) is not None


def pytest_collection_modifyitems(session, config, items):
    """Filter by --marker expression and sort by order marker."""
    marker_expr = config.getoption("--marker", default="")
    mode, markers = _parse_marker_expression(marker_expr)

    if mode != "none" and markers:
        filtered = []
        for item in items:
            if mode == "and":
                if all(_item_has_marker(item, m) for m in markers):
                    filtered.append(item)
                else:
                    item.add_marker(pytest.mark.skip(
                        reason=f"Missing marker(s) for AND expression: {'+'.join(markers)}"
                    ))
                    filtered.append(item)
            elif mode == "or":
                if any(_item_has_marker(item, m) for m in markers):
                    filtered.append(item)
                else:
                    item.add_marker(pytest.mark.skip(
                        reason=f"No matching marker for OR expression: {','.join(markers)}"
                    ))
                    filtered.append(item)
            elif mode == "single":
                if _item_has_marker(item, markers[0]):
                    filtered.append(item)
                else:
                    item.add_marker(pytest.mark.skip(
                        reason=f"Missing marker: {markers[0]}"
                    ))
                    filtered.append(item)
        items[:] = filtered

    def _get_order(item):
        marker = item.get_closest_marker("order")
        if marker and marker.args:
            return marker.args[0]
        return 999

    items.sort(key=_get_order)


# =============================================================================
# SESSION STARTUP — ENCRYPT, CLONE, SYNC
# =============================================================================

def _apply_dataset_overrides(config):
    """Apply dataset/sync overrides from environment variables."""
    ds_override = os.environ.get("OMNIA_DATASET_OVERRIDE", "")
    if ds_override:
        log(f"Dataset override: {config.get('dataset')} → {ds_override}", "INFO")
        config["dataset"] = ds_override

    si_override = os.environ.get("OMNIA_SYNC_INPUT_OVERRIDE", "")
    if si_override:
        config["sync_utils_input"] = si_override.lower() == "true"

    return config


def pytest_sessionstart(session):
    """Session startup: validate config, encrypt credentials, clone repo, sync files, init report."""
    # Validate config first — fail fast with clear errors
    try:
        result = validate_all()
        for warn in result.get("warnings", []):
            log(f"Config warning: {warn}", "WARN")
    except ConfigValidationError as exc:
        log(str(exc), "FAIL")
        pytest.exit(str(exc), returncode=1)

    try:
        encrypt_test_credentials()
    except (ValueError, OSError):
        pass

    config = load_test_config()

    # Apply dataset/sync overrides from env vars (set by --config mode)
    config = _apply_dataset_overrides(config)

    host = get_testinfra_host()

    # Pre-flight connectivity check (remote mode only)
    if not is_local_execution():
        conn_result = check_target_connectivity(host)
        if conn_result["success"]:
            log("Pre-flight: target is reachable", "OK")
        else:
            log(f"Pre-flight: {conn_result['error']}", "FAIL")
            pytest.exit(f"Target unreachable: {conn_result['error']}", returncode=1)

    if not is_local_execution():
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Project sync failed: {sync_result['error']}", "WARN")

    if config.get("sync_utils_input", False):
        sync_result = sync_utils_input(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Input sync failed: {sync_result['error']}", "ERROR")

    # Sync install_os credentials (if applicable)
        install_os_cred_result = sync_install_os_credentials(host)
        if install_os_cred_result["success"]:
            if install_os_cred_result["details"]:
                level = "WARN" if "skipping sync" in install_os_cred_result["details"] else "OK"
                log(install_os_cred_result["details"], level)
        else:
            log(f"Install OS credential sync failed: {install_os_cred_result['error']}", "WARN")

    # Initialize test report
    valid_scenarios = {"utils", "collect", "install_os", "precheck"}
    module_name = "utils"
    test_paths = session.config.args if hasattr(session.config, 'args') else []
    for p in test_paths:
        for part in p.replace("\\", "/").split("/"):
            if part in valid_scenarios:
                module_name = part
                break

    report_id = os.environ.get("REPORT_ID")
    report = TestReport(
        module_name=module_name,
        report_path=str(config.get("report_path", "/opt/omnia/reports")),
        report_name=str(config.get("report_name", "test_report")),
        server_ip=str(config.get("oim_server_ip", "localhost")),
        report_id=report_id,
    )
    set_current_report(report)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print report saved box and summary table AFTER pytest failure output."""
    report = get_current_report()
    if report and report.results:
        try:
            report.save()
        except (OSError, IOError) as exc:
            log(f"Report save failed: {exc}", "WARN")

    print_summary_table()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture test results and output for the HTML report + summary."""
    outcome = yield
    result = outcome.get_result()

    if result.when not in {"call", "setup"}:
        return

    if result.when == "setup" and not result.skipped:
        return

    status = "PASSED" if result.passed else (
        "SKIPPED" if result.skipped else "FAILED"
    )

    output = get_test_output(item.name)
    details = output if output else ""
    skip_reason = ""

    if result.skipped:
        if hasattr(result, "wasxfail"):
            status = "SKIPPED"
        rep_text = str(result.longrepr) if result.longrepr else ""
        if "Skipped:" in rep_text:
            skip_reason = rep_text.split("Skipped:", 1)[-1].strip()
        elif "SKIP" in rep_text:
            skip_reason = rep_text.split("SKIP", 1)[-1].strip()

    if status == "SKIPPED" and skip_reason:
        details = (details + "\n" if details else "") + f"SKIPPED: {skip_reason}"

    tc_id = get_last_tc_id()
    if not tc_id:
        tc_id = _TC_ID_MAP.get(item.name, "")

    add_session_result(
        test_name=item.name,
        status=status,
        duration=getattr(result, "duration", 0),
        tc_id=tc_id,
    )

    report = get_current_report()
    if report:
        report.add_result({
            "test_name": item.name,
            "status": status,
            "duration": getattr(result, "duration", 0),
            "details": details,
            "error": str(result.longrepr) if result.failed else "",
        })


# =============================================================================
# SUPPRESS PYTEST DOT OUTPUT
# =============================================================================

def pytest_report_teststatus(report, config):
    """Replace pytest's default . s F characters with empty strings."""
    if report.when == "call":
        if report.passed:
            return "passed", "", ""
        elif report.failed:
            return "failed", "", ""
    if report.skipped:
        return "skipped", "", ""


# =============================================================================
# HOST FIXTURE
# =============================================================================

@pytest.fixture(scope="session")
def host():
    """Testinfra host connected to the target server."""
    return get_testinfra_host()
