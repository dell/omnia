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
- host fixture (testinfra connection to kube_vip target)
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
    sync_telemetry_input,
    get_dataset_input_dir,
)
from library.functions.validation_func import (
    validate_all,
    ConfigValidationError,
)
from library.vars import TEST_CASES

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
            "Use '+' for AND (both required): sanity+sink. "
            "Use ',' for OR (either matches): sink,source."
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
        "sink": "Sink (VictoriaMetrics/VictoriaLogs/Kafka) tests",
        "source": "Source (iDRAC/LDMS/DCGM/OME/etc.) tests",
        "nft": "Non-functional tests (performance, idempotency)",
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
        filtered = []
        for item in items:
            if mode == "and":
                match = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                match = any(_item_has_marker(item, m) for m in markers)
            else:
                match = _item_has_marker(item, markers[0])

            if not match:
                item.add_marker(pytest.mark.skip(
                    reason=f"Marker filter: {marker_expr}"
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
    """Apply dataset/sync overrides from environment variables.

    Environment variables (set by run_validation.sh --config mode):
      OMNIA_DATASET_OVERRIDE      — override config["dataset"]
      OMNIA_SYNC_INPUT_OVERRIDE   — override config["sync_telemetry_input"]

    Args:
        config: Test configuration dict from load_test_config().

    Returns:
        dict: Updated config dict (mutated in place).
    """
    ds_override = os.environ.get("OMNIA_DATASET_OVERRIDE", "")
    if ds_override:
        log(f"Dataset override: {config.get('dataset')} -> {ds_override}", "INFO")
        config["dataset"] = ds_override

    si_override = os.environ.get("OMNIA_SYNC_INPUT_OVERRIDE", "")
    if si_override:
        config["sync_telemetry_input"] = si_override.lower() == "true"

    return config


def pytest_sessionstart(session):
    """Session startup: validate config, encrypt credentials, clone repo, sync files, init report."""
    # Validate config first — fail fast with clear errors
    try:
        validate_all()
    except ConfigValidationError as exc:
        log(str(exc), "ERROR")
        pytest.exit(str(exc), returncode=1)

    config = load_test_config()
    config = _apply_dataset_overrides(config)

    # Auto-encrypt credentials
    encrypt_test_credentials()

    # Init report
    report_path = config.get("report_path", "reports")
    report_name = config.get("report_name", "telemetry_test_report")
    report = TestReport(
        report_dir=os.path.join(_TEST_DIR, report_path),
        report_name=report_name,
    )
    set_current_report(report)

    # Clone repo to target if configured
    if config.get("sync_project", False):
        host = get_testinfra_host()
        sync_project_to_remote(host)

    # Sync telemetry input files
    if config.get("sync_telemetry_input", False):
        host = get_testinfra_host()
        dataset = config.get("dataset", "")
        dataset_dir = get_dataset_input_dir(dataset) if dataset else ""
        sync_telemetry_input(host, dataset_dir or None)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def host():
    """Provide testinfra host connection to the kube_vip target."""
    return get_testinfra_host()


# =============================================================================
# TEST RESULT HOOKS
# =============================================================================

def pytest_runtest_makereport(item, call):
    """Capture test results for the summary table."""
    if call.when != "call":
        return

    func_name = item.name
    tc_id = _TC_ID_MAP.get(func_name, get_last_tc_id() or "")
    test_output = get_test_output()

    result = "PASS" if call.excinfo is None else "FAIL"
    if item.get_closest_marker("skip") or (
        call.excinfo and call.excinfo.typename == "Skipped"
    ):
        result = "SKIP"

    add_session_result(tc_id, func_name, result, test_output)


def pytest_sessionfinish(session, exitstatus):
    """Generate report and print summary at session end."""
    report = get_current_report()
    if report:
        report.generate()

    print_summary_table()
