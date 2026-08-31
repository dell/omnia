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
Pytest configuration for orchestrator FVT.

Provides:
- host fixture (testinfra connection to OIM target)
- Custom markers: sanity, functional, regression, deploy
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
    sync_orchestrator_input,
    sync_repo_manager_output,
)
from library.functions.validation_func import (  # noqa: E402
    validate_all,
    ConfigValidationError,
)


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
            "Use '+' for AND (both required): sanity+functional. "
            "Use ',' for OR (either matches): sanity,functional."
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
    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestCollectionWarning"
    )
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "regression": "Regression tests",
        "deploy": "Playbook deployment tests (requires full environment)",
        "slurm": "Slurm-specific tests (requires Slurm enabled)",
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
    """Filter by --marker expression, apply smart skips only when no marker specified, and sort by order marker."""
    marker_expr = config.getoption("--marker", default="")
    mode, markers = _parse_marker_expression(marker_expr)

    # Only apply auto-skips if no marker expression is provided
    if mode == "none":
        # Auto-skip deploy tests (require full environment setup)
        for item in items:
            if _item_has_marker(item, "deploy"):
                item.add_marker(pytest.mark.skip("Deploy tests require full environment setup - use --marker deploy to enable"))

        # Auto-skip cleanup status tests (require prior cleanup execution)
        for item in items:
            test_name = item.name
            if "test_containers_removed" in test_name or "test_services_removed" in test_name or "test_firewall_ports_closed" in test_name:
                item.add_marker(pytest.mark.skip("Cleanup status tests require prior cleanup playbook execution"))

        # Auto-skip API test (requires fully operational OpenCHAMI services)
        for item in items:
            if "test_openchami_api_reachable" in item.name:
                item.add_marker(pytest.mark.skip("API test requires fully operational OpenCHAMI services"))
                
        # Auto-skip SLURM tests if SLURM is not enabled in config
        for item in items:
            if _item_has_marker(item, "slurm"):
                # Check if SLURM is enabled in the config
                try:
                    config = load_test_config()
                    project = config.get("project_name", "project_default")
                    orchestrator_config_path = f"/opt/omnia/orchestrator/input/{project}/orchestrator_config.yml"
                    
                    # Read config file to check for SLURM
                    if os.path.exists(orchestrator_config_path):
                        with open(orchestrator_config_path, 'r') as f:
                            config_content = f.read().lower()
                        slurm_keywords = ["slurm_control", "slurm_node", "slurm_login"]
                        has_slurm = any(keyword in config_content for keyword in slurm_keywords)
                        
                        if not has_slurm:
                            item.add_marker(pytest.mark.skip("SLURM is not enabled in orchestrator config"))
                except Exception:
                    # If we can't check, don't auto-skip - let the test run and fail if needed
                    pass
    else:
        # When marker is specified, only apply the marker filtering
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
        config["sync_orchestrator_input"] = si_override.lower() == "true"

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

    if not is_local_execution():
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Project sync failed: {sync_result['error']}", "WARN")

    if config.get("sync_orchestrator_input", False):
        sync_result = sync_orchestrator_input(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Input sync failed: {sync_result['error']}", "ERROR")

    if config.get("sync_repo_manager_output", False):
        out_result = sync_repo_manager_output(host)
        if out_result["success"]:
            log(out_result["details"], "OK")
        else:
            log(f"Output sync failed: {out_result['error']}", "WARN")

    # Initialize test report
    valid_scenarios = {
        "orchestrator", "validate", "prepare",
        "provision", "cleanup",
    }
    module_name = "orchestrator"
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
        report_name=str(config.get("report_name", "orchestrator_test_report")),
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
        doc = getattr(item.obj, "__doc__", "") or ""
        if doc.strip().startswith("TC_"):
            tc_id = doc.strip().split(":", 1)[0].strip()

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
