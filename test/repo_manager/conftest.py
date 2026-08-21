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
import subprocess

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# --- Load Omnia environment variables into the current Python process ---
# Ansible playbooks run by tests inherit this environment.
_OMNIA_ENV_FILE = "/etc/omnia/omnia.env"
if os.path.exists(_OMNIA_ENV_FILE):
    # nosec B602: shell=True is required to source bash env file and expand variables
    # The command is trusted (reads a local config file) and does not accept user input.
    _env_output = subprocess.run(  # nosec B602
        f"bash -c 'set -a; source {_OMNIA_ENV_FILE}; set +a; env'",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    for _line in _env_output.stdout.splitlines():
        if "=" in _line and not _line.startswith("_"):
            _key, _val = _line.split("=", 1)
            if _key not in os.environ:
                os.environ[_key] = _val

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
    encrypt_test_credentials,
    log,
    add_session_result,
    print_summary_table,
)

# --- Session-scoped test report ---
@pytest.fixture(scope="session", autouse=True)
def test_report():
    """Create a session-wide test report."""
    config = load_test_config()
    report_path = config.get("report_path", "/opt/omnia/reports")
    oim_ip = config.get("oim_server_ip", "127.0.0.1")
    report = TestReport(
        module_name="repo_manager",
        report_path=report_path,
        report_name="repo_manager_fvt",
        server_ip=oim_ip,
    )
    set_current_report(report)
    yield report
    print_summary_table()


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
@pytest.fixture(scope="session")
def host():
    """Return a testinfra host connection to the target."""
    return get_testinfra_host()
