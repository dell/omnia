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
