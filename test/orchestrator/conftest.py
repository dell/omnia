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
Pytest configuration for orchestrator FVT and NFT.

Provides:
- host fixture (testinfra connection to OIM target)
- Custom markers: sanity, functional, deploy, slurm, nft, performance, idempotency, security, negative
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- Credential auto-encryption
- Remote clone and dataset sync on session startup
"""

import sys
import os
import re

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
    build_report_name,
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
    sync_image_build_manager_output,
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
        "deploy": "Playbook deployment tests (requires full environment)",
        "slurm": "Slurm-specific tests (requires Slurm enabled)",
        "kubernetes": "Kubernetes-specific tests (requires Kubernetes enabled)",
        "nft": "Non-functional tests (performance, idempotency, security)",
        "performance": "Performance and timing tests",
        "idempotency": "Idempotency",
        "security": "Security and permission tests",
        "negative": "Negative test cases for error scenarios",
        "buildstream": "BuildStream pipeline validation (post-provision sanity)",
        "destructive": "Explicit opt-in state-changing or cleanup tests",
        "additional_cloud_init": "Additional cloud-init feature tests",
        "hpc_benchmarks": "HPC benchmark staging and execution tests",
        "apptainer": "Apptainer installation and workload tests",
        "gpu": "GPU, CUDA, GRES, and DCGM tests",
        "openldap": "OpenLDAP service, endpoint, TLS, and data tests",
        "storage": "Shared storage configuration and runtime tests",
        "vast": "VAST NFS, client, and RDMA tests",
        "powervault": "PowerVault iSCSI and multipath tests",
        "recovery": "Retry, recovery, and interrupted-run tests",
        "unit": "Deterministic unit and source-contract tests",
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
    selected_tag = os.environ.get("OMNIA_DEPLOY_TAG", "")

    # Only apply auto-skips if no marker expression is provided
    if mode == "none":
        for item in items:
            if _item_has_marker(item, "deploy") and command_type != "exec":
                item.add_marker(pytest.mark.skip(
                    "Deploy tests run only during the runner exec phase"
                ))
            if _item_has_marker(item, "nft") and command_type != "nft":
                item.add_marker(pytest.mark.skip(
                    "NFT tests run only through nft_orchestrator"
                ))
            if _item_has_marker(item, "negative") and selected_tag != "negative":
                item.add_marker(pytest.mark.skip(
                    "Negative tests require the explicit negative tag"
                ))
    else:
        # When marker is specified, only apply the marker filtering
        filtered = []
        for item in items:
            # The runner already scopes execution to ``-m deploy``.  A feature
            # marker belongs to the verification cases and must not silently
            # skip the lifecycle trigger that creates the state under test.
            if command_type == "exec" and _item_has_marker(item, "deploy"):
                match = True
            elif mode == "and":
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

    # Destructive tests always require an explicit opt-in, even when another
    # marker (for example ``nft`` or ``sanity``) was selected.  This prevents
    # broad marker runs from tearing down an installed environment.
    if "destructive" not in markers:
        for item in items:
            if _item_has_marker(item, "destructive"):
                item.add_marker(pytest.mark.skip(
                    "Destructive tests require --marker destructive"
                ))

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

    so_override = os.environ.get("OMNIA_SYNC_OUTPUT_OVERRIDE", "")
    if so_override:
        config["sync_repo_manager_output"] = so_override.lower() == "true"

    sio_override = os.environ.get("OMNIA_SYNC_IMAGE_OUTPUT_OVERRIDE", "")
    if sio_override:
        config["sync_image_build_manager_output"] = (
            sio_override.lower() == "true"
        )

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

    if not is_local_execution() and os.environ.get("OMNIA_COMMAND_TYPE") == "exec":
        sync_result = sync_project_to_remote(host)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            pytest.exit(
                f"Project sync failed: {sync_result['error']}", returncode=1
            )

    if config.get("sync_orchestrator_input", False):
        sync_result = sync_orchestrator_input(host, config)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            pytest.exit(
                f"Input sync failed: {sync_result['error']}", returncode=1
            )

    if config.get("sync_repo_manager_output", False):
        out_result = sync_repo_manager_output(host, config)
        if out_result["success"]:
            log(out_result["details"], "OK")
        else:
            pytest.exit(
                f"Output sync failed: {out_result['error']}", returncode=1
            )

    if config.get("sync_image_build_manager_output", False):
        image_result = sync_image_build_manager_output(host, config)
        if image_result["success"]:
            log(image_result["details"], "OK")
        else:
            pytest.exit(
                "Image build output sync failed: "
                f"{image_result['error']}",
                returncode=1,
            )

    # Initialize test report
    valid_scenarios = {
        "orchestrator", "precheck", "validate", "prepare", "deploy",
        "provision", "execute", "pxeboot", "check", "cleanup",
        "rollback", "nft", "negative", "playbooks", "slurm",
        "kubernetes",
    }
    module_name = "orchestrator"
    test_paths = session.config.args if hasattr(session.config, 'args') else []
    for path in test_paths:
        for part in path.replace("\\", "/").split("/"):
            if part in valid_scenarios:
                module_name = part
                break

    report_id = os.environ.get("REPORT_ID")
    base_name = str(config.get("report_name", "orchestrator_test_report"))
    report_name = build_report_name(
        domain_name="orchestrator",
        base_name=base_name,
    )
    report_path = str(config.get("report_path", "/opt/omnia/reports"))
    if (
        os.environ.get("OMNIA_COMMAND_TYPE") == "ut"
        or is_local_execution()
    ):
        report_path = os.path.join(_TEST_DIR, "reports")
    report = TestReport(
        module_name=module_name,
        report_path=report_path,
        report_name=report_name,
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

    doc = getattr(item.obj, "__doc__", "") or ""
    tc_id = ""
    doc_id = re.match(
        r"(ORCH_(?:FVT_[A-Z0-9_]+_[EV]\d{3}|NFT_\d{3}|UT_\d{3})"
        r"|TC_K8_\d{3})\s*:",
        doc.strip(),
    )
    if doc_id:
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
