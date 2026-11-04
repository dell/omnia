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
Pytest configuration for build_stream FVT.

Provides:
- host fixture (testinfra connection to target)
- Custom markers: library.vars.domain_vars.MARKERS (registered below)
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- precheck gate: the prepare_base entry point is skipped after its precheck fails
- Credential auto-encryption
- Remote clone and dataset sync on session startup
"""

import os
from datetime import datetime

import pytest

import omnia_auto
from omnia_auto import (
    get_testinfra_host,
    is_local_execution,
    load_test_config,
    TestReport,
    set_current_report,
    get_current_report,
    get_test_output,
    get_last_tc_id,
    get_last_detail_fields,
    encrypt_test_credentials,
    build_report_name,
    log,
    add_session_result,
    print_summary_table,
    TestLogger,
)

from library.functions.host_func import (
    check_target_connectivity,
    sync_project_to_remote,
    sync_build_stream_input,
)
from library.functions.validation_func import (
    validate_all,
    ConfigValidationError,
)
from library.functions.log_func import skip_test
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES

# pytest puts this directory on sys.path (rootdir conftest, prepend import
# mode). No library module uses omnia_auto at import time, so configuring it
# here, before any hook or fixture runs, is early enough.
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)

# Path parts that name the report module (scenario folders and NFT).
_REPORT_SCENARIOS = frozenset(
    {"prepare_base", "precheck", "prepare", "execute", "cleanup", "nft"}
)

_FVT_SCENARIO_ORDER = {
    "prepare_base": 0,
    "precheck": 1,
    "prepare": 2,
    "execute": 3,
    "cleanup": 4,
}

_FVT_SUITE_ORDER = {
    "prepare_base": {"": 0, "readiness": 1},
    "precheck": {"": 0, "environment": 1, "containers": 2, "credentials": 3},
    "prepare": {"": 0, "build_stream": 1},
    "execute": {
        "": 0, "gitlab_server": 1, "gitlab_runner": 2, "gitlab_project": 3,
        "build_automatic": 4, "build_manual": 5, "deploy_automatic": 6,
        "deploy_manual": 7, "cadence": 8, "auto_cleanup": 9, "pipeline_cleanup": 10,
    },
    "cleanup": {"": 0, "gitlab": 1, "build_stream": 2},
}

# Build test-function-name → TC ID map for summary table fallback.
_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}
_TC_BY_NAME = {f"test_{key}": tc for key, tc in TEST_CASES.items()}

# Entry tests (IDs ending in _E<nnn>) deploy the playbook a category verifies.
# When one fails, every later test of the same category (fvt/<category>/) is
# skipped with the reason instead of failing against a half-deployed system.
# Category -> (TC ID, title) of the first entry test that failed this session.
_ENTRY_FAILED = pytest.StashKey[dict]()


def _fvt_category(item) -> str:
    """Return the fvt/<category> an item belongs to ("" outside fvt/)."""
    parts = item.path.parts
    return parts[parts.index("fvt") + 1] if "fvt" in parts[:-1] else ""


def _is_entry_test(name: str) -> bool:
    """Return whether the test is a category entry test (TC ID ..._E<nnn>)."""
    tc_id = _TC_ID_MAP.get(name, "")
    return "_E" in tc_id and tc_id.rsplit("_E", 1)[-1].isdigit()


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
            "Use ',' for OR (either matches): sanity,deploy."
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
        "deploy": "Runs a build_stream.yml tag or omnia.sh (test_playbook.py)",
        "pipeline": "Triggers or verifies a real BuildStream pipeline",
        "build_pipeline": "Build pipeline (build_automatic, build_manual)",
        "deploy_pipeline": "Deploy pipeline (deploy_automatic, deploy_manual)",
        "cadence": "Cadence cycle, cadence pipeline and cadence enable/disable",
        "cleanup_pipeline": "PIPELINE_TYPE=cleanup pipeline (pipeline_cleanup)",
        "automatic_cleanup": "Automated cleanup pass on the cadence build image (auto_cleanup)",
        "automatic_execution": "Commit-triggered build and deploy pipelines",
        "manual_execution": "API-triggered (PIPELINE_TYPE) build and deploy pipelines",
        "nft": "BuildStream non-functional test",
        "resilience": "Service and pipeline recovery test",
        "security": "Authentication, authorization, and input security test",
        "disruptive": "Explicitly enabled test that changes live service state",
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


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """Filter by --marker expression and sort by order marker."""
    marker_expr = config.getoption("--marker", default="")
    mode, markers = _parse_marker_expression(marker_expr)

    if mode != "none" and markers:
        selected = []
        deselected = []
        for item in items:
            if mode == "and":
                matches = all(
                    _item_has_marker(item, marker) for marker in markers
                )
            elif mode == "or":
                matches = any(
                    _item_has_marker(item, marker) for marker in markers
                )
            else:
                matches = _item_has_marker(item, markers[0])

            if matches:
                selected.append(item)
            else:
                deselected.append(item)

        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    def _get_order(item):
        marker = item.get_closest_marker("order")
        local_order = marker.args[0] if marker and marker.args else 999
        node_parts = item.nodeid.replace("\\", "/").split("/")
        scenario = ""
        suite = ""
        if "fvt" in node_parts:
            index = node_parts.index("fvt")
            if len(node_parts) > index + 1:
                scenario = node_parts[index + 1]
            if len(node_parts) > index + 2:
                candidate = node_parts[index + 2]
                if not candidate.startswith("test_"):
                    suite = candidate
        return (
            _FVT_SCENARIO_ORDER.get(scenario, 999),
            _FVT_SUITE_ORDER.get(scenario, {}).get(suite, 999),
            local_order,
        )

    items.sort(key=_get_order)


# =============================================================================
# SESSION STARTUP — ENCRYPT, CLONE, SYNC
# =============================================================================

def _apply_dataset_overrides(config):
    """Apply dataset/sync overrides from environment variables.

    Environment variables (set by run_validation.sh --config mode):
      OMNIA_DATASET_OVERRIDE      — override config["dataset"]
      OMNIA_SYNC_INPUT_OVERRIDE   — override config["sync_build_stream_input"]

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
        config["sync_build_stream_input"] = si_override.lower() == "true"

    return config


def _exit_on_failure(result, label):
    """Log a sync/connectivity result, or stop the session when it failed."""
    if result["success"]:
        log(result["details"], "OK")
        return
    message = f"{label}: {result['error']}"
    log(message, "FAIL")
    pytest.exit(message, returncode=1)


def _prepare_target(config):
    """Check the target and run the selected project/input synchronization."""
    target = get_testinfra_host()
    execution_phase = os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec"
    if not is_local_execution():
        _exit_on_failure(check_target_connectivity(target), "Target unreachable")
        if execution_phase:
            _exit_on_failure(sync_project_to_remote(target), "Project sync failed")
    if execution_phase and config.get("sync_build_stream_input", False):
        _exit_on_failure(sync_build_stream_input(target), "Input sync failed")


def _init_report(session, config):
    """Create the session TestReport named after the selected scenario."""
    module_name = "build_stream"
    test_paths = session.config.args if hasattr(session.config, "args") else []
    for path in test_paths:
        for part in path.replace("\\", "/").split("/"):
            if part in _REPORT_SCENARIOS:
                module_name = part
                break

    configured_id = str(config.get("run_id") or "").strip()
    run_id = configured_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    os.environ["RUN_ID"] = run_id
    report = TestReport(
        module_name=module_name,
        report_path=os.path.expandvars(str(config["report_path"])),
        report_name=build_report_name(
            base_name=str(config.get("report_name", "build_stream_test_report")),
        ),
        server_ip=str(config.get("oim_server_ip", "localhost")),
        run_id=run_id,
    )
    set_current_report(report)


def pytest_sessionstart(session):
    """Session startup: validate config, encrypt creds, sync files, init report."""
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

    # Apply dataset/sync overrides from env vars (set by --config mode)
    config = _apply_dataset_overrides(load_test_config())
    _prepare_target(config)
    _init_report(session, config)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary():
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
def pytest_runtest_makereport(item):
    """Capture test results and output for the HTML report + summary."""
    outcome = yield
    result = outcome.get_result()

    if result.failed and result.when in {"setup", "call"} and _is_entry_test(item.name):
        category = _fvt_category(item)
        failed_entries = item.session.stash.get(_ENTRY_FAILED, {})
        if category and category not in failed_entries:
            entry = _TC_BY_NAME[item.name]
            failed_entries[category] = (entry["id"], entry["title"])
            item.session.stash[_ENTRY_FAILED] = failed_entries

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

    # Prefer the stable function-name registry. TestLogger state is process
    # global and can otherwise leak the preceding ID into a marker-filtered
    # test that was skipped before its logger was constructed.
    tc_id = _TC_ID_MAP.get(item.name, "") or get_last_tc_id()

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
        report_payload = {
            "tc_id": tc_id,
            "test_name": item.name,
            "status": status,
            "duration": getattr(result, "duration", 0),
            "details": details,
            "error": str(result.longrepr) if result.failed else "",
        }
        if detail_fields:
            report_payload["detail_fields"] = detail_fields
        report.add_result(report_payload)


def pytest_runtest_setup(item):
    """Skip a test whose category entry test already failed in this session.

    The skip is logged through the test's own TestLogger, so the console shows
    the test with the reason and the summary and report carry it too.
    """
    category = _fvt_category(item)
    failed = item.session.stash.get(_ENTRY_FAILED, {}).get(category)
    if not failed:
        return
    entry_id, entry_title = failed
    tc = _TC_BY_NAME.get(item.name, {"id": item.name, "title": item.name})
    message = LOG["entry_failed_skip"].format(
        entry_id=entry_id, entry_title=entry_title, category=category)
    pytest.skip(skip_test(TestLogger(tc["title"], tc["id"]), message))


# =============================================================================
# SUPPRESS PYTEST DOT OUTPUT (TestLogger already provides detail)
# =============================================================================

def pytest_report_teststatus(report):
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
