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
Pytest configuration for telemetry FVT.

Provides:
- host fixture (testinfra connection to OIM target)
- Custom markers: sanity, functional, deploy, sink, source
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
import omnia_auto  # noqa: E402
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)

# --- Common functions from omnia_auto ---
from omnia_auto import (  # noqa: E402
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
    set_verbose_mode,
    add_session_result,
    print_summary_table,
)

# --- Module-specific functions ---
from library.functions.host_func import (  # noqa: E402
    sync_project_to_remote,
    sync_telemetry_input,
)
from library.functions.telemetry_func import (  # noqa: E402
    check_target_connectivity,
)
from library.functions.validation_func import (  # noqa: E402
    validate_all,
    ConfigValidationError,
)
from library.vars import TEST_CASES  # noqa: E402

# Build test-function-name -> TC ID map for summary table fallback
_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}
_TC_ID_MAP["test_deploy_telemetry"] = TEST_CASES["deploy_telemetry"]["id"]


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
            "Use '+' for AND (both required): source+sanity. "
            "Use ',' for OR (either matches): sink,source."
        ),
    )


# =============================================================================
# MARKER REGISTRATION
# =============================================================================

def pytest_configure(config):
    """Register custom markers and set verbose mode."""
    # Enable verbose logging when pytest -v is used or OMNIA_VERBOSE is set
    if config.option.verbose > 0 or os.environ.get("OMNIA_VERBOSE"):
        set_verbose_mode(True)
    
    # Set environment variables for Ansible non-interactive execution
    # This prevents ansible.builtin.pause from failing in pytest
    os.environ["ANSIBLE_NOCOLOR"] = "1"
    os.environ["ANSIBLE_FORCE_COLOR"] = "0"
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "default"
    
    # Redirect stdin to /dev/null to prevent pause module from blocking
    # This is safe because Ansible playbooks should not require interactive input
    import subprocess
    try:
        devnull = open(os.devnull, 'r')
        os.dup2(devnull.fileno(), 0)  # Redirect stdin (fd 0) to /dev/null
    except Exception:
        pass  # If it fails, continue anyway
    
    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestCollectionWarning"
    )
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "regression": "Regression tests",
        "deploy": "Playbook deployment tests",
        "sink": "Sink (VictoriaMetrics/VictoriaLogs/Kafka) tests",
        "source": "Source (iDRAC/LDMS/OME/SFM/UFM) tests",
        "ome": "OME (OpenManage Enterprise) specific tests",
        "ldms": "LDMS (Lightweight Distributed Metric Service) specific tests",
        "sfm": "SFM (SmartFabric Manager) specific tests",
        "ufm": "UFM (Unified Fabric Manager) specific tests",
        "nft": "Non-functional tests (performance, idempotency)",
        "performance": "Performance tests (execution time thresholds)",
        "idempotency": "Idempotency tests (re-run verification)",
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
                match = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                match = any(_item_has_marker(item, m) for m in markers)
            else:
                match = _item_has_marker(item, markers[0])

            if not match:
                reason = (
                    f"Marker filter: "
                    f"{'+'.join(markers) if mode == 'and' else ','.join(markers)}"
                )
                item.add_marker(pytest.mark.skip(reason=reason))
            filtered.append(item)
        items[:] = filtered

    def _get_order(item):
        marker = item.get_closest_marker("order")
        if marker and marker.args:
            return marker.args[0]
        return 999

    items.sort(key=_get_order)


# =============================================================================
# SESSION STARTUP
# =============================================================================

def _apply_dataset_overrides(config):
    """Apply dataset/sync overrides from environment variables."""
    ds_override = os.environ.get("OMNIA_DATASET_OVERRIDE", "")
    if ds_override:
        log(f"Dataset override: {config.get('dataset')} -> {ds_override}", "INFO")
        config["dataset"] = ds_override

    si_override = os.environ.get("OMNIA_SYNC_INPUT_OVERRIDE", "")
    if si_override:
        config["sync_telemetry_input"] = si_override.lower() == "true"

    return config


def pytest_sessionstart(session):
    """Session startup: validate, encrypt, clone, sync, init report."""
    # Validate config first
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
    config = _apply_dataset_overrides(config)

    host = get_testinfra_host()

    # Pre-flight connectivity check (remote mode only)
    if not is_local_execution():
        conn_result = check_target_connectivity(host)
        if conn_result["success"]:
            log("Pre-flight: target is reachable", "OK")
        else:
            log(f"Pre-flight: {conn_result['error']}", "FAIL")
            pytest.exit(
                f"Target unreachable: {conn_result['error']}",
                returncode=1,
            )

    if not is_local_execution():
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Project sync failed: {sync_result['error']}", "WARN")

    if config.get("sync_telemetry_input", False):
        sync_result = sync_telemetry_input(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Input sync failed: {sync_result['error']}", "ERROR")

    # Initialize test report
    valid_scenarios = {
        "telemetry", "deploy", "cleanup", "precheck", "validate",
    }
    module_name = "telemetry"
    test_paths = session.config.args if hasattr(session.config, 'args') else []
    for path in test_paths:
        for part in path.replace("\\", "/").split("/"):
            if part in valid_scenarios:
                module_name = part
                break

    report_id = os.environ.get("REPORT_ID")
    report = TestReport(
        module_name=module_name,
        report_path=str(config.get("report_path", "/opt/omnia/reports")),
        report_name=str(config.get("report_name", "telemetry_test_report")),
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
        details = (
            (details + "\n" if details else "")
            + f"SKIPPED: {skip_reason}"
        )

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
# SUPPRESS PYTEST DOT OUTPUT (TestLogger already provides detail)
# =============================================================================

def pytest_report_teststatus(report, config):
    """Replace pytest's default . s F characters with empty strings."""
    if report.when == "call":
        if report.passed:
            return "passed", "", ""
        if report.failed:
            return "failed", "", ""
    if report.skipped:
        return "skipped", "", ""


# =============================================================================
# HOST FIXTURE
# =============================================================================

@pytest.fixture(scope="session")
def host():
    """Testinfra host connected to the OIM target server."""
    return get_testinfra_host()
