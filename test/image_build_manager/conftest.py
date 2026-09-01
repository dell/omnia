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
Pytest configuration for image_build_manager FVT.

Provides:
- host fixture (testinfra connection to target)
- Custom markers: x86_64, aarch64, sanity, functional, deploy
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
import omnia_auto  # noqa: E402 - configure after adding the module root
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)

# --- Common functions from omnia_auto ---
from omnia_auto import (  # noqa: E402 - configure omnia_auto before consumers
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
from library.functions.host_func import (  # noqa: E402 - depends on configuration
    sync_project_to_remote,
    sync_image_build_input,
    sync_repo_manager_output,
)
from library.functions.build_image_func import (  # noqa: E402 - configured import
    check_target_connectivity,
)
from library.functions.validation_func import (  # noqa: E402 - configured import
    validate_all,
    ConfigValidationError,
)
from library.vars import TEST_CASES  # noqa: E402 - configured module import

# Build test-function-name → TC ID map for summary table fallback.
# Auto-generates from TEST_CASES keys (e.g. "deploy_build" → "test_deploy_build")
# plus explicit overrides where function name differs from key.
_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}
_TC_ID_MAP["test_deploy_image_build_manager"] = TEST_CASES["deploy_full"]["id"]


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
            "Use '+' for AND (both required): x86_64+sanity. "
            "Use ',' for OR (either matches): x86_64,aarch64."
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
        "x86_64": "Test applies to x86_64 architecture",
        "aarch64": "Test applies to aarch64 architecture",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "regression": "Regression tests",
        "deploy": "Playbook deployment tests",
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
                if all(_item_has_marker(item, m) for m in markers):
                    filtered.append(item)
                else:
                    item.add_marker(pytest.mark.skip(
                        reason=(
                            f"Missing marker(s) for AND expression: "
                            f"{'+'.join(markers)}"
                        )
                    ))
                    filtered.append(item)
            elif mode == "or":
                if any(_item_has_marker(item, m) for m in markers):
                    filtered.append(item)
                else:
                    item.add_marker(pytest.mark.skip(
                        reason=(
                            f"No matching marker for OR expression: "
                            f"{','.join(markers)}"
                        )
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
    """Apply dataset/sync overrides from environment variables.

    Environment variables (set by run_validation.sh --config mode):
      OMNIA_DATASET_OVERRIDE      — override config["dataset"]
      OMNIA_SYNC_INPUT_OVERRIDE   — override config["sync_image_build_input"]
      OMNIA_SYNC_OUTPUT_OVERRIDE  — override config["sync_output"]

    Args:
        config: Test configuration dict from load_test_config().

    Returns:
        dict: Updated config dict (mutated in place).
    """
    ds_override = os.environ.get("OMNIA_DATASET_OVERRIDE", "")
    if ds_override:
        log(f"Dataset override: {config.get('dataset')} → {ds_override}", "INFO")
        config["dataset"] = ds_override

    si_override = os.environ.get("OMNIA_SYNC_INPUT_OVERRIDE", "")
    if si_override:
        config["sync_image_build_input"] = si_override.lower() == "true"

    so_override = os.environ.get("OMNIA_SYNC_OUTPUT_OVERRIDE", "")
    if so_override:
        config["sync_output"] = so_override.lower() == "true"

    return config


def pytest_sessionstart(session):
    """Validate config, prepare the target, and initialize the test report."""
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
            log(
                f"Pre-flight: {conn_result['error']}",
                "FAIL",
            )
            pytest.exit(
                f"Target unreachable: {conn_result['error']}",
                returncode=1,
            )

    if not is_local_execution():
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            message = f"Project sync failed: {sync_result['error']}"
            log(message, "FAIL")
            pytest.exit(message, returncode=1)

    if config.get("sync_image_build_input", False):
        sync_result = sync_image_build_input(host, config)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            message = f"Input sync failed: {sync_result['error']}"
            log(message, "FAIL")
            pytest.exit(message, returncode=1)

    if config.get("sync_output", False):
        out_result = sync_repo_manager_output(host, config)
        if out_result["success"]:
            log(out_result["details"], "OK")
        else:
            message = f"Output sync failed: {out_result['error']}"
            log(message, "FAIL")
            pytest.exit(message, returncode=1)

    # Initialize test report
    # Detect scenario name from test paths (fvt/<scenario>/...)
    valid_scenarios = {
        "image_build_manager", "validate", "prepare",
        "build", "cleanup", "precheck",
    }
    module_name = "image_build_manager"
    test_paths = session.config.args if hasattr(session.config, 'args') else []
    for p in test_paths:
        for part in p.replace("\\", "/").split("/"):
            if part in valid_scenarios:
                module_name = part
                break

    report_id = os.environ.get("REPORT_ID")
    report = TestReport(
        module_name=module_name,
        report_path=str(config.get(
            "report_path",
            os.environ.get("OMNIA_DATA_PATH", "/opt/omnia") + "/reports",
        )),
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

    # Print summary table (from omnia_auto)
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

    # Get TC ID from TestLogger (set during test execution)
    tc_id = get_last_tc_id()

    # Fallback: look up TC ID from TEST_CASES if TestLogger didn't set it
    if not tc_id:
        tc_id = _TC_ID_MAP.get(item.name, "")

    # Accumulate for summary table (shared via omnia_auto)
    add_session_result(
        test_name=item.name,
        status=status,
        duration=getattr(result, "duration", 0),
        tc_id=tc_id,
    )

    # Store in HTML/JSON report
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
