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
from datetime import datetime

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.abspath(os.path.join(_TEST_DIR, "..", "plugins"))
while _PLUGIN_DIR in sys.path:
    sys.path.remove(_PLUGIN_DIR)
sys.path.insert(0, _PLUGIN_DIR)
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
    clear_test_context,
    encrypt_test_credentials,
    build_report_name,
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
from library.vars import TEST_CASES, UT_TEST_CASE_IDS  # noqa: E402

# Build test-function-name -> TC ID map for deterministic report resolution.
_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}
_TC_ID_MAP.update(
    {
        "test_all_telemetry_pods_running": TEST_CASES["all_pods_running"]["id"],
        "test_python_packages_installed": TEST_CASES[
            "install_mode_python_packages"
        ]["id"],
        "test_idrac_deployment": TEST_CASES["install_mode_idrac_deployment"][
            "id"
        ],
        "test_idrac_pods": TEST_CASES["install_mode_idrac_pods"]["id"],
        "test_powerscale_dependencies": TEST_CASES[
            "install_mode_powerscale_deps"
        ]["id"],
        "test_powerscale_deployment": TEST_CASES[
            "install_mode_powerscale_deployment"
        ]["id"],
        "test_ome_telemetry_metrics_in_victoria": TEST_CASES[
            "ome_telemetry_metrics_in_vm"
        ]["id"],
        "test_ome_inventory_metrics_in_victoria": TEST_CASES[
            "ome_inventory_metrics_in_vm"
        ]["id"],
        "test_ome_health_metrics_in_victoria": TEST_CASES[
            "ome_health_metrics_in_vm"
        ]["id"],
        "test_ome_alerts_logs_in_victoria": TEST_CASES[
            "ome_alerts_logs_in_vl"
        ]["id"],
        "test_ome_auditlogs_logs_in_victoria": TEST_CASES[
            "ome_auditlogs_logs_in_vl"
        ]["id"],
        "test_ufm_external_service": TEST_CASES["ufm_external_svc"]["id"],
        "test_vast_external_service": TEST_CASES["vast_external_svc"]["id"],
        "test_deploy_idempotency": TEST_CASES["nft_deploy_idempotent"]["id"],
        "test_cleanup_idempotency": TEST_CASES["nft_cleanup_idempotent"]["id"],
        "test_cleanup_idempotency_no_pods": TEST_CASES[
            "nft_cleanup_no_pods"
        ]["id"],
        "test_cleanup_pvcs_preserved": TEST_CASES[
            "nft_cleanup_pvcs_preserved"
        ]["id"],
        "test_cleanup_with_volume_performance": TEST_CASES[
            "nft_cleanup_vol_perf"
        ]["id"],
        "test_cleanup_with_volume_idempotency": TEST_CASES[
            "nft_cleanup_vol_idempotent"
        ]["id"],
        "test_cleanup_with_volume_no_pods": TEST_CASES[
            "nft_cleanup_vol_no_pods"
        ]["id"],
        "test_cleanup_with_volume_no_pvcs": TEST_CASES[
            "nft_cleanup_no_pvcs"
        ]["id"],
        "test_validate_performance": TEST_CASES["nft_validate_perf"]["id"],
        "test_deploy_performance": TEST_CASES["nft_deploy_perf"]["id"],
        "test_cleanup_performance": TEST_CASES["nft_cleanup_perf"]["id"],
        "test_resilience_setup_deploy": TEST_CASES[
            "nft_resilience_setup"
        ]["id"],
        "test_sink_pod_deletion_recovery": TEST_CASES[
            "nft_sink_pod_recovery"
        ]["id"],
        "test_source_pod_deletion_recovery": TEST_CASES[
            "nft_source_pod_recovery"
        ]["id"],
        "test_sts_storage_pod_recovery": TEST_CASES["nft_sts_pod_recovery"][
            "id"
        ],
        "test_pvc_persistence_after_pod_deletion": TEST_CASES[
            "nft_pvc_persistence"
        ]["id"],
        "test_service_endpoints_after_restart": TEST_CASES[
            "nft_service_endpoints"
        ]["id"],
        "test_data_queryable_after_sink_restart": TEST_CASES[
            "nft_data_after_restart"
        ]["id"],
        "test_node_reboot_recovery": TEST_CASES["nft_node_reboot"]["id"],
        "test_idrac_data_lifecycle": TEST_CASES[
            "nft_idrac_data_lifecycle"
        ]["id"],
        "test_full_lifecycle": TEST_CASES["nft_full_lifecycle"]["id"],
        "test_operator_pod_recovery": TEST_CASES["nft_operator_recovery"][
            "id"
        ],
    }
)


def _ut_test_node_key(item):
    """Return the stable registry key for a Telemetry UT item."""
    normalized_node_id = item.nodeid.replace("\\", "/")
    if "ut/" not in normalized_node_id:
        return ""
    return normalized_node_id.split("ut/", 1)[1].split("[", 1)[0]


def _delete_sinks_volume_enabled(config):
    """Resolve the sink cleanup-volume mode without requesting a fixture."""
    cli_value = config.getoption("--delete-sinks-volume")
    if cli_value is not None:
        return cli_value.lower() in ("true", "1", "yes")
    return os.environ.get("DELETE_SINKS_VOLUME", "").lower() in (
        "true",
        "1",
        "yes",
    )


def _registered_test_case_id(item):
    """Resolve a testcase ID from the item rather than stale logger state."""
    ut_tc_id = UT_TEST_CASE_IDS.get(_ut_test_node_key(item), "")
    if ut_tc_id:
        return ut_tc_id

    if item.name == "test_deploy_telemetry":
        deploy_tag = os.environ.get("OMNIA_DEPLOY_TAG", "")
        deploy_key = "deploy_deploy" if deploy_tag else "deploy_telemetry"
        return TEST_CASES[deploy_key]["id"]

    if item.name == "test_no_pvcs_after_full_cleanup":
        case_key = (
            "no_pvcs_after_full_cleanup"
            if _delete_sinks_volume_enabled(item.config)
            else "pvcs_preserved_after_cleanup"
        )
        return TEST_CASES[case_key]["id"]

    return _TC_ID_MAP.get(item.name, "")


# =============================================================================
# CUSTOM CLI OPTIONS
# =============================================================================

def pytest_addoption(parser):
    """Add --marker and --delete-sinks-volume options."""
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
    parser.addoption(
        "--delete-sinks-volume",
        action="store",
        default=None,
        help=(
            "Control sink (Kafka, VictoriaMetrics, VictoriaLogs) PVC/volume deletion during cleanup. "
            "When 'true', cleanup deletes all PVCs including sink volumes. "
            "When 'false' or omitted (default), sink PVCs are preserved. "
            "Source volumes (currently iDRAC and PowerScale) are always deleted. "
            "Also accepts DELETE_SINKS_VOLUME environment variable."
        ),
    )


# =============================================================================
# MARKER REGISTRATION
# =============================================================================

def _redirect_stdin_to_devnull():
    """Redirect stdin for non-interactive playbooks and close the source."""
    source_fd = -1
    try:
        source_fd = os.open(os.devnull, os.O_RDONLY)
        if source_fd == 0:
            original_fd = source_fd
            source_fd = os.dup(original_fd)
            os.close(original_fd)
        os.dup2(source_fd, 0)
    except OSError:
        pass  # Continue when stdin cannot be redirected.
    finally:
        if source_fd > 0:
            try:
                os.close(source_fd)
            except OSError:
                pass


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
    _redirect_stdin_to_devnull()

    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestCollectionWarning"
    )
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "precheck": "Pre-deployment environment checks",
        "regression": "Regression tests",
        "deploy": "Playbook deployment tests",
        "sink": "Sink (VictoriaMetrics/VictoriaLogs/Kafka) tests",
        "source": "Source (iDRAC/LDMS/OME/SFM/UFM/VAST) tests",
        "ome": "OME (OpenManage Enterprise) specific tests",
        "ldms": "LDMS (Lightweight Distributed Metric Service) specific tests",
        "vast": "VAST Data storage telemetry specific tests",
        "sfm": "SFM (SmartFabric Manager) specific tests",
        "ufm": "UFM (Unified Fabric Manager) specific tests",
        "nft": "Non-functional tests (performance, idempotency, resilience)",
        "performance": "Performance tests (execution time thresholds)",
        "idempotency": "Idempotency tests (re-run verification)",
        "resilience": "Resilience tests (pod recovery, reboot, lifecycle)",
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
        selected = []
        deselected = []
        for item in items:
            if mode == "and":
                match = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                match = any(_item_has_marker(item, m) for m in markers)
            else:
                match = _item_has_marker(item, markers[0])

            if match:
                selected.append(item)
            else:
                deselected.append(item)
        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    def _get_order(item):
        marker = item.get_closest_marker("order")
        if marker and marker.args:
            return marker.args[0]
        return 999

    items.sort(key=_get_order)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol():
    """Reset TestLogger state before each test, including setup skips."""
    clear_test_context()


# =============================================================================
# SESSION STARTUP
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
        log(f"Dataset override: {config.get('dataset')} → {ds_override}", "INFO")
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
        sync_result = sync_telemetry_input(host, config)
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

    configured_id = str(config.get("run_id") or "").strip()
    run_id = configured_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    os.environ["RUN_ID"] = run_id
    base_name = str(config.get("report_name", "telemetry_test_report"))
    report_name = build_report_name(
        base_name=base_name,
    )
    report = TestReport(
        module_name=module_name,
        report_path=str(config.get("report_path", "/opt/omnia/reports")),
        report_name=report_name,
        server_ip=str(config.get("oim_server_ip", "localhost")),
        run_id=run_id,
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

    # Successful setup is not a test result. Setup failures and skips must be
    # retained so the affected test and its TC ID remain visible in reports.
    if result.when == "setup" and result.passed:
        return

    status = "PASSED" if result.passed else (
        "SKIPPED" if result.skipped else "FAILED"
    )

    ut_tc_id = UT_TEST_CASE_IDS.get(_ut_test_node_key(item), "")
    registered_tc_id = _registered_test_case_id(item)
    logger_tc_id = get_last_tc_id()
    tc_id = registered_tc_id or logger_tc_id
    output = (
        get_test_output(item.name)
        if not ut_tc_id and logger_tc_id == tc_id
        else ""
    )
    details = output if output else ""
    skip_reason = ""

    if result.skipped:
        if hasattr(result, "wasxfail"):
            status = "SKIPPED"
        if isinstance(result.longrepr, tuple) and len(result.longrepr) >= 3:
            skip_reason = str(result.longrepr[2]).strip()
        elif result.longrepr:
            skip_reason = str(result.longrepr).strip()
        reason_prefixes = ("Skipped:", "SKIPPED:", "SKIP:")
        while any(skip_reason.startswith(prefix) for prefix in reason_prefixes):
            for prefix in reason_prefixes:
                if skip_reason.startswith(prefix):
                    skip_reason = skip_reason[len(prefix):].strip()
                    break
        if not skip_reason and hasattr(result, "wasxfail"):
            skip_reason = str(result.wasxfail).strip()

    if status == "SKIPPED" and skip_reason:
        details = (
            (details + "\n" if details else "")
            + f"SKIPPED: {skip_reason}"
        )

    add_session_result(
        test_name=item.name,
        status=status,
        duration=getattr(result, "duration", 0),
        tc_id=tc_id,
    )

    report = get_current_report()
    if report:
        report.add_result({
            "tc_id": tc_id,
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


@pytest.fixture(scope="session")
def delete_sinks_volume(request):
    """Resolve delete_sinks_volume flag from CLI option or environment variable.

    Priority order:
      1. --delete-sinks-volume CLI option (if provided)
      2. DELETE_SINKS_VOLUME environment variable (if set)
      3. Default: false (Kafka and VictoriaMetrics/VictoriaLogs PVCs preserved)

    Returns:
        bool: True if delete_sinks_volume=true, False otherwise.
    """
    cli_value = request.config.getoption("--delete-sinks-volume")
    if cli_value is not None:
        return cli_value.lower() in ("true", "1", "yes")

    env_value = os.environ.get("DELETE_SINKS_VOLUME")
    if env_value is not None:
        return env_value.lower() in ("true", "1", "yes")

    return False



