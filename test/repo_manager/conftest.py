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
Pytest configuration for repo_manager FVT.

Provides:
- host fixture (testinfra connection to target)
- Custom markers: sanity, functional, deploy, positive, negative
- Marker expression: '+' for AND, ',' for OR
- Test ordering via @pytest.mark.order(n)
- Credential auto-encryption
"""

import sys
import os
import re

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# Add plugins directory to path for omnia_auto
_PLUGINS_DIR = os.path.join(os.path.dirname(_TEST_DIR), "plugins")
if _PLUGINS_DIR not in sys.path:
    sys.path.insert(0, _PLUGINS_DIR)

# --- Load Omnia environment variables into the current Python process ---
# Ansible playbooks run by tests inherit this environment.
_OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
if os.path.exists(_OMNIA_ENV_FILE):
    try:
        with open(_OMNIA_ENV_FILE, "r") as _f:
            for _line in _f:
                _line = _line.strip()
                # Skip comments and empty lines
                if not _line or _line.startswith("#"):
                    continue
                # Parse KEY=VALUE pairs
                if "=" in _line and not _line.startswith("_"):
                    _key, _val = _line.split("=", 1)
                    _key = _key.strip()
                    _val = _val.strip()
                    # Remove quotes if present
                    if _val.startswith('"') and _val.endswith('"'):
                        _val = _val[1:-1]
                    elif _val.startswith("'") and _val.endswith("'"):
                        _val = _val[1:-1]
                    # Expand environment variables in the value (e.g., ${OMNIA_DATA_PATH})
                    # This handles simple ${VAR} and $VAR expansions
                    def _expand_vars(match):
                        var_name = match.group(1) or match.group(2)
                        return os.environ.get(var_name, match.group(0))
                    _val = re.sub(r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)', _expand_vars, _val)
                    # Only set if not already in environment
                    if _key and _key not in os.environ:
                        os.environ[_key] = _val
    except (IOError, OSError):
        # If file cannot be read, skip silently
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
    build_report_name,
    log,
    add_session_result,
    print_summary_table,
)

# --- Module-specific functions ---
from library.functions import host_func


# =============================================================================
# DATASET OVERRIDES
# =============================================================================

def _apply_dataset_overrides(config):
    """Apply dataset/sync overrides from environment variables.

    Environment variables (set by run_validation.sh --config mode):
      OMNIA_DATASET_OVERRIDE      — override config["dataset"]
      OMNIA_SYNC_INPUT_OVERRIDE   — override config["sync_repo_manager_input"]

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
        log(f"Sync input override: {config.get('sync_repo_manager_input')} -> {si_override}", "INFO")
        config["sync_repo_manager_input"] = si_override.lower() == "true"

    return config


# =============================================================================
# SESSION STARTUP — ENCRYPT, CLONE, SYNC
# =============================================================================

def pytest_sessionstart(session):
    """Session startup: validate config, encrypt creds, sync files, init report."""
    config = load_test_config()

    # Apply dataset/sync overrides from env vars (set by --config mode)
    config = _apply_dataset_overrides(config)

    host = get_testinfra_host()

    if not is_local_execution():
        sync_result = host_func.sync_project_to_remote()
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Project sync failed: {sync_result['error']}", "WARN")

    if config.get("sync_repo_manager_input", False):
        sync_result = host_func.sync_repo_manager_input(host, config)
        if sync_result["success"]:
            log(sync_result["details"], "OK")
        else:
            log(f"Input sync failed: {sync_result['error']}", "ERROR")


# --- Session-scoped test report ---
@pytest.fixture(scope="session", autouse=True)
def test_report():
    """Create a session-wide test report."""
    config = load_test_config()
    report_path = config.get("report_path", "/opt/omnia/reports")
    oim_ip = config.get("oim_server_ip", "127.0.0.1")
    report_name = build_report_name(
        domain_name="repo_manager",
        base_name="repo_manager_fvt",
    )
    report = TestReport(
        module_name="repo_manager",
        report_path=report_path,
        report_name=report_name,
        server_ip=oim_ip,
    )
    set_current_report(report)
    yield report


# =============================================================================
def pytest_addoption(parser):
    """Add --marker option for custom marker expression filtering."""
    parser.addoption(
        "--marker",
        action="store",
        default="",
        help=(
            "Marker filter expression. "
            "Use '+' for AND (all required): sanity+positive. "
            "Use ',' for OR (any match): sanity,positive. "
            "Example: sanity+positive+negative or sanity,positive"
        ),
    )


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
        "positive": "Positive test cases",
        "negative": "Negative test cases",
        "deploy": "Playbook deployment tests",
        "x86_64": "x86_64 architecture tests",
        "aarch64": "aarch64 architecture tests",
    }
    for name, desc in markers.items():
        config.addinivalue_line("markers", f"{name}: {desc}")


# =============================================================================
def pytest_collection_modifyitems(config, items):
    """Apply custom marker expression filtering."""
    marker_expr = config.getoption("--marker")
    if not marker_expr:
        return

    # Translate expression into a nodeid-style deselect set:
    #   'sanity+positive' => keep items marked with BOTH sanity AND positive
    #   'sanity,positive' => keep items marked with sanity OR positive
    selected = []
    deselected = []

    for item in items:
        item_markers = {m.name for m in item.iter_markers()}
        or_groups = marker_expr.split(",")
        matched = False
        for group in or_groups:
            required = {m.strip() for m in group.split("+") if m.strip()}
            if required and required.issubset(item_markers):
                matched = True
                break
        if matched:
            selected.append(item)
        else:
            deselected.append(item)

    config.hook.pytest_deselected(items=deselected)
    items[:] = selected


# =============================================================================
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
            "tc_id": tc_id,
            "test_name": item.name,
            "status": status,
            "duration": getattr(result, "duration", 0),
            "details": details,
            "error": (
                str(result.longrepr) if result.failed else ""
            ),
        })


@pytest.fixture(scope="session")
def host():
    """Return a testinfra host connection to the target."""
    return get_testinfra_host()
