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
Pytest configuration for omnia main FVT.

Provides:
- host fixture (testinfra connection to target)
- Custom markers: sanity, functional, deploy, cleanup, nft
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- Credential auto-encryption
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
    load_test_config,
    TestReport,
    set_current_report,
    get_current_report,
    get_test_output,
    get_last_detail_fields,
    get_last_tc_id,
    encrypt_test_credentials,
    log,
    add_session_result,
    print_summary_table,
)

# --- Module-specific functions ---
from library.functions.validation_func import (  # noqa: E402
    validate_all,
    ConfigValidationError,
)
from library.vars import FVT_TAGS, TEST_CASES  # noqa: E402


_TC_ID_MAP = {
    f"test_{key}": test_case["id"]
    for key, test_case in TEST_CASES.items()
}

_FVT_SCENARIO_ORDER = {
    scenario: position
    for position, scenario in enumerate(FVT_TAGS)
}


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
            "Use ',' for OR (either matches): sanity,functional."
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
        "deploy": "Script execution tests (setup, init, run)",
        "cleanup": "Teardown tests (run after verify, may destroy state)",
        "nft": "Non-functional tests (performance, idempotency, permissions)",
    }
    for name, desc in markers.items():
        config.addinivalue_line("markers", f"{name}: {desc}")


# =============================================================================
# MARKER EXPRESSION FILTERING
# =============================================================================

def _parse_marker_expression(expr):
    """Parse marker expression into (mode, marker_list).

    '+' => AND (all markers must be present)
    ',' => OR  (any marker must be present)
    Single marker => exact match

    Returns:
        Tuple of ('and'|'or'|'single', list_of_markers)
    """
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
        selected = []
        deselected = []
        for item in items:
            if mode == "and":
                matched = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                matched = any(_item_has_marker(item, m) for m in markers)
            else:
                matched = _item_has_marker(item, markers[0])
            (selected if matched else deselected).append(item)
        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    def _get_order(item):
        marker = item.get_closest_marker("order")
        local_order = marker.args[0] if marker and marker.args else 999
        parts = item.nodeid.replace("\\", "/").split("/")
        scenario = next(
            (part for part in parts if part in _FVT_SCENARIO_ORDER),
            "",
        )
        return (
            _FVT_SCENARIO_ORDER.get(scenario, 999),
            local_order,
            item.nodeid,
        )

    items.sort(key=_get_order)


# =============================================================================
# SESSION STARTUP
# =============================================================================

def pytest_sessionstart(session):
    """Session startup: validate config, encrypt credentials, init report."""
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

    # Initialize test report
    valid_scenarios = {
        "setup", "init", "cli", "omnia_cli",
        "precheck", "validate", "cleanup", "nft",
    }
    test_paths = (
        session.config.args if hasattr(session.config, "args") else []
    )
    selected_scenarios = []
    for path in test_paths:
        for part in path.replace("\\", "/").split("/"):
            if part in valid_scenarios and part not in selected_scenarios:
                selected_scenarios.append(part)
                break
    module_name = (
        selected_scenarios[0]
        if len(selected_scenarios) == 1
        else "main_fvt"
    )

    report_id = os.environ.get("REPORT_ID")
    report = TestReport(
        module_name=module_name,
        report_path=str(
            config.get("report_path", "/opt/omnia/reports")
        ),
        report_name=str(
            config.get("report_name", "test_report")
        ),
        server_ip=str(
            config.get("oim_server_ip", "localhost")
        ),
        report_id=report_id,
    )
    set_current_report(report)


def pytest_sessionfinish(session, exitstatus):
    """Save report and print summary table after all tests complete."""
    report = get_current_report()
    if report and report.results:
        # Ensure report directory exists (may have been removed by cleanup)
        os.makedirs(report.report_path, exist_ok=True)
        report.save()

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
    detail_fields = get_last_detail_fields()
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

    tc_id = _TC_ID_MAP.get(item.name, "") or get_last_tc_id()

    add_session_result(
        test_name=item.name,
        status=status,
        duration=getattr(result, "duration", 0),
        tc_id=tc_id,
    )

    report = get_current_report()
    if report:
        report_payload = {
            "tc_id": tc_id,
            "test_name": item.name,
            "status": status,
            "duration": getattr(result, "duration", 0),
            "details": details,
            "error": (
                str(result.longrepr) if result.failed else ""
            ),
        }
        if detail_fields:
            report_payload["detail_fields"] = detail_fields
        report.add_result(report_payload)


# =============================================================================
# SUPPRESS PYTEST DOT OUTPUT
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
    return None


# =============================================================================
# HOST FIXTURE
# =============================================================================

@pytest.fixture(scope="session")
def host():
    """Testinfra host connected to the target server."""
    return get_testinfra_host()
