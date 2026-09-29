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
Pytest configuration for Orchestrator functional and non-functional tests.

Provides:
- host fixture (testinfra connection to OIM target)
- Registered lifecycle, capability, and risk-selection markers
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- Credential auto-encryption
- Remote clone and dataset sync on session startup
"""

import os
import re
import sys
from datetime import UTC, datetime

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# Match the runtime contract used by newer domain test frameworks. Explicit
# shell values win; otherwise load the target Omnia environment before any
# path resolver or playbook wrapper is imported.
_OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
if os.path.exists(_OMNIA_ENV_FILE):
    try:
        with open(_OMNIA_ENV_FILE, "r", encoding="utf-8") as _env_file:
            for _line in _env_file:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _value = _line.split("=", 1)
                _key = _key.strip()
                _value = _value.strip()
                if (
                    len(_value) >= 2
                    and _value[0] == _value[-1]
                    and _value[0] in {"'", '"'}
                ):
                    _value = _value[1:-1]
                _value = re.sub(
                    r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)",
                    lambda match: os.environ.get(
                        match.group(1) or match.group(2), match.group(0)
                    ),
                    _value,
                )
                if _key and _key not in os.environ:
                    os.environ[_key] = _value
    except OSError:
        pass

# --- Initialize omnia_auto BEFORE any imports that use it ---
import omnia_auto

omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)

# --- Common functions from omnia_auto ---
# --- Module-specific functions ---
from library.functions.host_func import (
    sync_image_build_manager_output,
    sync_orchestrator_input,
    sync_project_to_remote,
    sync_repo_manager_output,
)
from library.functions.project_func import (
    resolve_project_name,
)
from library.functions.validation_func import (
    ConfigValidationError,
    validate_all,
)
from library.vars import TEST_CASES
from omnia_auto import (
    TestReport,
    add_session_result,
    build_report_name,
    encrypt_test_credentials,
    get_current_report,
    get_last_tc_id,
    get_test_output,
    get_testinfra_host,
    is_local_execution,
    load_test_config,
    log,
    print_summary_table,
    set_current_report,
    set_verbose_mode,
)

# Build the function-name to test-case-ID map from the canonical registry.
# Keep explicit overrides only where a test function intentionally differs
# from its registry key.
_TC_ID_MAP = {f"test_{key}": test_case["id"] for key, test_case in TEST_CASES.items()}
_TC_ID_MAP.update(
    {
        "test_openchami_containers_running": TEST_CASES["openchami_containers"]["id"],
        "test_openchami_services_ready": TEST_CASES["openchami_services"]["id"],
        "test_openchami_apis_ready": TEST_CASES["openchami_apis"]["id"],
        "test_openchami_persistent_storage_and_tls": TEST_CASES["openchami_storage"][
            "id"
        ],
        "test_openchami_packages_and_artifacts": TEST_CASES["openchami_artifacts"][
            "id"
        ],
        "test_firewall_and_podman_network_policy": TEST_CASES["firewall_network"]["id"],
        "test_coredhcp_and_coredns_configuration": TEST_CASES["coredhcp_network"]["id"],
        "test_smd_group_membership": TEST_CASES["smd_groups"]["id"],
        "test_boot_service_configurations": TEST_CASES["boot_configurations"]["id"],
        "test_boot_service_node_identity": TEST_CASES["boot_nodes"]["id"],
        "test_metadata_service_groups": TEST_CASES["metadata_groups"]["id"],
        "test_metadata_service_instances": TEST_CASES["metadata_instances"]["id"],
        "test_coredhcp_and_coredns_inventory": TEST_CASES["network_inventory"]["id"],
        "test_kubernetes_node_services": TEST_CASES["kubernetes_services"]["id"],
        "test_kubernetes_version_compatibility": TEST_CASES["kubernetes_versions"][
            "id"
        ],
        "test_kubernetes_default_storage_class": TEST_CASES[
            "kubernetes_default_storage"
        ]["id"],
        "test_kubernetes_workload_scheduling": TEST_CASES["kubernetes_workload"]["id"],
        "test_kubernetes_nfs_dynamic_provisioning": TEST_CASES[
            "kubernetes_nfs_dynamic"
        ]["id"],
        "test_kubernetes_csi_dynamic_provisioning": TEST_CASES[
            "kubernetes_csi_dynamic"
        ]["id"],
        "test_kubernetes_control_plane_recovery": TEST_CASES["kubernetes_recovery"][
            "id"
        ],
        "test_slurm_cross_node_ssh": TEST_CASES["slurm_cross_ssh"]["id"],
        "test_slurm_control_ldap_authentication": TEST_CASES["slurm_control_ldap_auth"][
            "id"
        ],
        "test_slurm_login_ldap_authentication": TEST_CASES["slurm_login_ldap_auth"][
            "id"
        ],
        "test_slurm_compiler_ldap_authentication": TEST_CASES[
            "slurm_compiler_ldap_auth"
        ]["id"],
        "test_slurm_pam_no_job_access": TEST_CASES["slurm_pam_no_job"]["id"],
        "test_slurm_pam_policy": TEST_CASES["slurm_pam"]["id"],
        "test_slurm_control_node_jobs": TEST_CASES["slurm_basic_jobs"]["id"],
        "test_slurm_login_node_jobs": TEST_CASES["slurm_login_jobs"]["id"],
        "test_slurm_drain_queue_recovery": TEST_CASES["slurm_drain_queue"]["id"],
        "test_slurm_invalid_ldap_identity": TEST_CASES["slurm_invalid_ldap"]["id"],
        "test_slurm_infiniband_configuration": TEST_CASES["slurm_ib_configuration"][
            "id"
        ],
        "test_slurm_infiniband_connectivity": TEST_CASES["slurm_ib_connectivity"]["id"],
        "test_slurm_configuration_consistency": TEST_CASES["slurm_config_consistency"][
            "id"
        ],
        "test_slurm_configless_mode": TEST_CASES["slurm_configless"]["id"],
        "test_slurm_cluster_recovery": TEST_CASES["slurm_recovery"]["id"],
        "test_slurm_gpu_memory_stress": TEST_CASES["slurm_gpu_memory"]["id"],
        "test_slurm_compiler_node_jobs": TEST_CASES["slurm_compiler_jobs"]["id"],
        "test_openchami_removed": TEST_CASES["cleanup_openchami"]["id"],
        "test_openldap_removed": TEST_CASES["cleanup_openldap"]["id"],
        "test_slurm_cleanup": TEST_CASES["cleanup_slurm"]["id"],
        "test_kubernetes_cleanup": TEST_CASES["cleanup_kubernetes"]["id"],
        "test_artifacts_removed_and_inputs_preserved": TEST_CASES["cleanup_artifacts"][
            "id"
        ],
        "test_credentials_follow_selected_policy": TEST_CASES["cleanup_credentials"][
            "id"
        ],
    }
)


def _registered_test_case_id(item) -> str:
    """Return a deterministic TC ID without relying on logger state."""
    return _TC_ID_MAP.get(item.name, "")


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
            "Use '+' for AND (both required): slurm+functional. "
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
    config.addinivalue_line("filterwarnings", "ignore::pytest.PytestCollectionWarning")
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "functional": "Functional verification",
        "deploy": "Playbook deployment tests (requires full environment)",
        "openldap": "OpenLDAP service, endpoint, TLS, and data tests",
        "connectivity": "OIM-to-node network and SSH checks",
        "cloudinit": "Node cloud-init completion checks",
        "kubernetes": "Kubernetes post-boot checks",
        "slurm": "Slurm post-boot checks",
        "apptainer": "Apptainer runtime, image, and Slurm integration checks",
        "image_download": "Explicitly authorized Apptainer image download checks",
        "negative": "Expected-failure and rejection behavior checks",
        "non_disruptive": "Checks that do not reboot or drain cluster nodes",
        "disruptive": "Explicitly enabled reboot or scheduler-state checks",
        "reboot": "Node reboot and post-reboot recovery checks",
        "scheduler_state": "Scheduler drain, queue, and resume checks",
        "destructive": "Explicitly selected destructive cleanup checks",
        "nft": "Non-functional quality-contract checks",
        "performance": "Lifecycle duration checks",
        "idempotency": "Repeated lifecycle execution checks",
        "security": "Credential, key, log, and vault protection checks",
        "lifecycle": "Clean-baseline and fresh-install lifecycle checks",
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
    """Filter markers, apply safe defaults, and sort by order marker."""
    marker_expr = config.getoption("--marker", default="")
    mode, markers = _parse_marker_expression(marker_expr)
    command_type = os.environ.get("OMNIA_COMMAND_TYPE", "")

    explicitly_enabled = set(markers)
    functional_authorized = bool(
        explicitly_enabled
        & {
            "sanity",
            "functional",
            "slurm",
            "kubernetes",
            "openldap",
            "non_disruptive",
            "negative",
        }
    )
    disruptive_authorized = bool(
        explicitly_enabled & {"disruptive", "reboot", "scheduler_state"}
    )

    # Only apply the normal deploy auto-skip if no marker expression is given.
    if mode == "none":
        for item in items:
            if _item_has_marker(item, "deploy") and command_type != "exec":
                item.add_marker(
                    pytest.mark.skip(
                        "Deploy tests run only during the runner exec phase"
                    )
                )
            elif _item_has_marker(item, "disruptive"):
                item.add_marker(
                    pytest.mark.skip(
                        "Select a disruptive, reboot, or scheduler_state marker "
                        "to authorize this test"
                    )
                )
            elif _item_has_marker(item, "functional") and not _item_has_marker(
                item, "sanity"
            ):
                item.add_marker(
                    pytest.mark.skip(
                        "Select a functional or workload capability marker "
                        "to authorize this test"
                    )
                )
    else:
        # Feature filters apply to verification cases. The execution phase
        # still needs its one deploy test to create the state being verified.
        selected = []
        deselected = []
        for item in items:
            if command_type == "exec" and _item_has_marker(item, "deploy"):
                match = True
            elif mode == "and":
                match = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                match = any(_item_has_marker(item, m) for m in markers)
            else:
                match = _item_has_marker(item, markers[0])

            if match and _item_has_marker(item, "disruptive"):
                match = disruptive_authorized
            elif match and _item_has_marker(item, "functional"):
                match = functional_authorized
            if (
                match
                and _item_has_marker(item, "image_download")
                and "image_download" not in explicitly_enabled
                and not (
                    _item_has_marker(item, "sanity") and "sanity" in explicitly_enabled
                )
            ):
                match = False

            (selected if match else deselected).append(item)

        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    def _get_order(item):
        marker = item.get_closest_marker("order")
        if marker and marker.args:
            return marker.args[0]
        return 999

    items.sort(key=_get_order)


def pytest_runtest_setup(item):
    """Expose only explicitly selected mutation markers to runtime helpers."""
    marker_expr = item.config.getoption("--marker", default="")
    _mode, markers = _parse_marker_expression(marker_expr)
    selected = set(markers)
    sanity_authorized = _item_has_marker(item, "sanity") and (
        not selected or "sanity" in selected
    )
    authorized = set()
    if _item_has_marker(item, "functional") and (
        sanity_authorized
        or selected
        & {
            "functional",
            "slurm",
            "kubernetes",
            "openldap",
            "non_disruptive",
            "negative",
        }
    ):
        authorized.add("functional")
    if _item_has_marker(item, "disruptive") and selected & {
        "disruptive",
        "reboot",
        "scheduler_state",
    }:
        authorized.add("disruptive")
    if _item_has_marker(item, "image_download") and (
        "image_download" in selected or sanity_authorized
    ):
        authorized.add("image_download")
    if authorized:
        os.environ["OMNIA_FVT_AUTHORIZED_MARKERS"] = ",".join(sorted(authorized))
    else:
        os.environ.pop("OMNIA_FVT_AUTHORIZED_MARKERS", None)


def pytest_runtest_teardown(item, nextitem):
    """Clear per-test mutation authorization after every test."""
    os.environ.pop("OMNIA_FVT_AUTHORIZED_MARKERS", None)


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

    so_override = os.environ.get("OMNIA_SYNC_OUTPUT_OVERRIDE", "")
    if so_override:
        config["sync_repo_manager_output"] = so_override.lower() == "true"

    sio_override = os.environ.get("OMNIA_SYNC_IMAGE_OUTPUT_OVERRIDE", "")
    if sio_override:
        config["sync_image_build_manager_output"] = sio_override.lower() == "true"

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
    os.environ["OMNIA_PROJECT_NAME"] = resolve_project_name(config)

    host = get_testinfra_host()

    if not is_local_execution() and os.environ.get("OMNIA_COMMAND_TYPE") == "exec":
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            pytest.exit(f"Project sync failed: {sync_result['error']}", returncode=1)

    if config.get("sync_orchestrator_input", False):
        sync_result = sync_orchestrator_input(host, config)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            pytest.exit(f"Input sync failed: {sync_result['error']}", returncode=1)

    if config.get("sync_repo_manager_output", False):
        out_result = sync_repo_manager_output(host, config)
        if out_result["success"]:
            log(out_result["details"], "OK")
        else:
            pytest.exit(f"Output sync failed: {out_result['error']}", returncode=1)

    if config.get("sync_image_build_manager_output", False):
        image_result = sync_image_build_manager_output(host, config)
        if image_result["success"]:
            log(image_result["details"], "OK")
        else:
            pytest.exit(
                f"Image build output sync failed: {image_result['error']}",
                returncode=1,
            )

    # Initialize test report
    valid_scenarios = {
        "orchestrator",
        "precheck",
        "prepare",
        "provision",
        "pxeboot",
        "cleanup",
    }
    module_name = "orchestrator"
    test_paths = session.config.args if hasattr(session.config, "args") else []
    for path in test_paths:
        for part in path.replace("\\", "/").split("/"):
            if part in valid_scenarios:
                module_name = part
                break

    configured_id = str(config.get("run_id") or "").strip()
    run_id = configured_id or datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    os.environ["RUN_ID"] = run_id
    base_name = str(config.get("report_name", "orchestrator_test_report"))
    report_name = build_report_name(
        base_name=base_name,
    )
    report_path = str(config.get("report_path", "/opt/omnia/reports"))
    # Only override to local reports for unit tests, not for local FVT execution
    if os.environ.get("OMNIA_COMMAND_TYPE") == "ut":
        report_path = os.path.join(_TEST_DIR, "reports")
    report = TestReport(
        module_name=module_name,
        report_path=report_path,
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
        except OSError as exc:
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

    status = "PASSED" if result.passed else ("SKIPPED" if result.skipped else "FAILED")

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

    doc = getattr(item.obj, "__doc__", "") or ""
    tc_id = _registered_test_case_id(item)
    doc_id = re.match(
        r"(ORCH_(?:FVT_[A-Z0-9_]+_[EV]\d{3}|NFT_\d{3}|UT_\d{3})"
        r"|TC_K8_\d{3})\s*:",
        doc.strip(),
    )
    if doc_id and not tc_id:
        tc_id = doc_id.group(1)
    if not tc_id:
        tc_id = get_last_tc_id()

    add_session_result(
        test_name=item.name,
        status=status,
        duration=getattr(result, "duration", 0),
        tc_id=tc_id,
    )

    report = get_current_report()
    if report:
        report.add_result(
            {
                "tc_id": tc_id,
                "test_name": item.name,
                "status": status,
                "duration": getattr(result, "duration", 0),
                "details": details,
                "error": str(result.longrepr) if result.failed else "",
            }
        )


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
