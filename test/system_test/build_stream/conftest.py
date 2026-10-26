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
Pytest configuration for the BuildStream system (e2e) test suite.

Provides:
- omnia_auto configuration bound to this suite's test_config.yml
- host fixture (testinfra connection to the OIM)
- Global ordering by @pytest.mark.order(n), one band per scenario:
  prepare_base 1000, installation 2000, auto_cleanup 3000, cleanup 4000
- deploy tests run only in the runner exec phase (OMNIA_COMMAND_TYPE=exec)
- precheck gate: once a scenario's precheck test does not pass, the rest of
  that scenario is skipped in the same session
- --marker expressions: '+' for AND, ',' for OR (e.g., --marker sanity)
- JSON/HTML report and summary table
"""

import os
import re
import sys
from datetime import datetime

import pytest

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

# Load omnia.env before any imports (matches orchestrator pattern).
# This ensures OMNIA_DATA_PATH, OMNIA_PROJECT_NAME, and other domain paths
# are available to omnia_auto and library functions.
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

import omnia_auto  # noqa: E402 - configure after adding the module root

omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
    repository_root=os.path.dirname(os.path.dirname(os.path.dirname(_TEST_DIR))),
)

from omnia_auto import (  # noqa: E402 - configure omnia_auto before consumers
    TestReport,
    add_session_result,
    build_report_name,
    encrypt_test_credentials,
    get_current_report,
    get_last_detail_fields,
    get_test_output,
    get_testinfra_host,
    load_test_config,
    log,
    print_summary_table,
    set_current_report,
)

from library.functions.config_func import (  # noqa: E402 - configured import
    ConfigValidationError,
    validate_test_config,
)
from library.messages import TEST_LOG_MSGS  # noqa: E402 - configured import
from library.vars import TEST_CASES  # noqa: E402 - configured import
from library.vars.common_vars import DOMAIN_NAME, ORDER_UNSET  # noqa: E402
from library.vars.domain_vars import TAG_ROOT  # noqa: E402

_TC_ID_MAP = {f"test_{key}": tc["id"] for key, tc in TEST_CASES.items()}
_SCENARIO_ROOT = os.path.join(_TEST_DIR, TAG_ROOT)
_FAILED_PRECHECKS = set()


def pytest_addoption(parser):
    """Add --marker option for custom marker expression filtering."""
    parser.addoption(
        "--marker",
        action="store",
        default="",
        help=(
            "Marker filter expression. "
            "Use '+' for AND (both required): deploy+sanity. "
            "Use ',' for OR (either matches): sanity,pipeline."
        ),
    )


def pytest_configure(config):
    """Register suite markers and set verbose mode."""
    from omnia_auto import set_verbose_mode  # noqa: E402

    # Enable verbose logging when pytest -v is used or OMNIA_VERBOSE is set
    if config.option.verbose > 0 or os.environ.get("OMNIA_VERBOSE"):
        set_verbose_mode(True)
    config.addinivalue_line("filterwarnings", "ignore::pytest.PytestCollectionWarning")
    markers = {
        "order(n)": "Specify test execution order (lower first)",
        "sanity": "Baseline verification (must-pass)",
        "deploy": "Exec phase: scenario precheck or entry point (omnia.sh, playbook, pass)",
        "precheck": "Scenario precheck; a failure skips the rest of the scenario",
        "destructive": "Removes deployed state (cleanup)",
        "e2e": "End-to-end system test",
        "br_86010": "Traceability: TEST-BR-86010 (NERSC Backend Buildstream) system test plan",
        "prepare_base": "Base domain preparation (BuildStream prerequisites)",
        "installation": "BuildStream installation and pipeline flow",
        "pipeline": "Triggers or verifies a GitLab/BuildStream pipeline",
        "cadence": "Cadence trigger and pipeline",
        "cleanup": "Domain cleanup verification",
        "auto_cleanup": "Automated (retention) image cleanup pass",
    }
    for name, desc in markers.items():
        config.addinivalue_line("markers", f"{name}: {desc}")


def _parse_marker_expression(expr):
    """Parse a --marker expression into (mode, marker_list)."""
    expr = expr.strip()
    if not expr:
        return "none", []
    if "+" in expr:
        return "and", [m.strip() for m in expr.split("+")]
    if "," in expr:
        return "or", [m.strip() for m in expr.split(",")]
    return "single", [expr]


def _item_has_marker(item, marker_name):
    return item.get_closest_marker(marker_name) is not None


def _scenario(item) -> str:
    """Return the e2e scenario directory that owns ``item``."""
    relative = os.path.relpath(str(item.path), _SCENARIO_ROOT)
    return "" if relative.startswith(os.pardir) else relative.split(os.sep)[0]


def pytest_runtest_setup(item):
    """Skip a scenario's remaining tests once its precheck did not pass."""
    scenario = _scenario(item)
    if scenario in _FAILED_PRECHECKS and not _item_has_marker(item, "precheck"):
        pytest.skip(TEST_LOG_MSGS["precheck_gate"].format(scenario=scenario))


def pytest_collection_modifyitems(config, items):
    """Filter by --marker, gate deploy tests, and sort by the order marker.

    deploy-marked tests run an entry point (omnia.sh, a playbook or a cleanup
    pass). Without --marker they run only in the runner exec phase
    (OMNIA_COMMAND_TYPE=exec); in the exec phase they are always selected.
    """
    mode, markers = _parse_marker_expression(config.getoption("--marker", default=""))
    command_type = os.environ.get("OMNIA_COMMAND_TYPE", "")

    if mode == "none":
        for item in items:
            if _item_has_marker(item, "deploy") and command_type != "exec":
                item.add_marker(pytest.mark.skip(
                    "Deploy tests run only during the runner exec phase "
                    "(./run_validation.sh ... exec|test or OMNIA_COMMAND_TYPE=exec)"))
    else:
        selected, deselected = [], []
        for item in items:
            if command_type == "exec" and _item_has_marker(item, "deploy"):
                match = True
            elif mode == "and":
                match = all(_item_has_marker(item, m) for m in markers)
            elif mode == "or":
                match = any(_item_has_marker(item, m) for m in markers)
            else:
                match = _item_has_marker(item, markers[0])
            (selected if match else deselected).append(item)
        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    def _order(item):
        marker = item.get_closest_marker("order")
        return marker.args[0] if marker and marker.args else ORDER_UNSET

    items.sort(key=_order)


def pytest_sessionstart():
    """Validate configuration and initialize the session report."""
    try:
        validate_test_config(load_test_config())
    except ConfigValidationError as exc:
        log(str(exc), "FAIL")
        pytest.exit(str(exc), returncode=1)

    try:
        encrypt_test_credentials()
    except (ValueError, OSError):
        pass

    config = load_test_config()
    run_id = str(config.get("run_id") or "").strip() or datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    os.environ["RUN_ID"] = run_id
    set_current_report(
        TestReport(
            module_name=DOMAIN_NAME,
            report_path=os.path.expandvars(str(config["report_path"])),
            report_name=build_report_name(base_name=str(config["report_name"])),
            server_ip=str(config.get("oim_server_ip") or "localhost"),
            run_id=run_id,
        )
    )


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary():
    """Save the report and print the summary table."""
    report = get_current_report()
    if report and report.results:
        try:
            report.save()
        except OSError as exc:
            log(f"Report save failed: {exc}", "WARN")
    print_summary_table()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item):
    """Capture each result for the report and summary table."""
    outcome = yield
    result = outcome.get_result()
    # A precheck that ran and did not pass (or errored in setup) closes its
    # scenario. A precheck merely skipped by the deploy gate does not.
    if _item_has_marker(item, "precheck") and (
            (result.when == "call" and not result.passed)
            or (result.when == "setup" and result.failed)):
        _FAILED_PRECHECKS.add(_scenario(item))
    if result.when not in {"call", "setup"} or (
        result.when == "setup" and not result.skipped
    ):
        return

    status = "PASSED" if result.passed else ("SKIPPED" if result.skipped else "FAILED")
    tc_id = _TC_ID_MAP.get(item.name, "")
    duration = getattr(result, "duration", 0)
    add_session_result(test_name=item.name, status=status, duration=duration, tc_id=tc_id)

    report = get_current_report()
    if report:
        payload = {
            "tc_id": tc_id,
            "test_name": item.name,
            "status": status,
            "duration": duration,
            "details": get_test_output(item.name) or "",
            "error": str(result.longrepr) if result.failed else "",
        }
        detail_fields = get_last_detail_fields()
        if detail_fields:
            payload["detail_fields"] = detail_fields
        report.add_result(payload)


def pytest_report_teststatus(report):
    """Suppress pytest progress characters; TestLogger prints the detail."""
    if report.when == "call" and (report.passed or report.failed):
        return report.outcome, "", ""
    if report.skipped:
        return "skipped", "", ""
    return None


@pytest.fixture(scope="session")
def host():
    """Testinfra host connected to the OIM."""
    return get_testinfra_host()
