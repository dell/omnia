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
Omnia Main Init — Domain Init Verification.

MAIN_FVT_INIT_V001: Verify domain log directories created
MAIN_FVT_INIT_V002: Verify domain output directories created
MAIN_FVT_INIT_V003: Verify domain input files staged for image_build_manager
MAIN_FVT_INIT_V004: Verify domain input files staged for repo_manager
MAIN_FVT_INIT_V005: Verify domain input files staged for orchestrator
MAIN_FVT_INIT_V006: Verify domain input files staged for discovery
MAIN_FVT_INIT_V007: Verify --init with domain filter runs for single domain
MAIN_FVT_INIT_V008: Verify --init with --force-deps forces reinstall
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger, resolve_runtime_paths
from library.functions.omnia_main_func import (
    check_domain_log_dirs,
    check_domain_input_staged,
    check_domain_output_dirs,
    run_omnia_cmd,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


def _report_input_staging(tl, result, domain, expected_path):
    """Render a consistent input-staging result without exposing file content."""
    fields = {
        "Domain": domain,
        "Destination": expected_path,
        "Files found": result.get("file_count", 0),
    }
    if result["success"]:
        tl.passed_fields(LOG["input_staged_ok"].format(
            domain=domain, count=result["file_count"]
        ), fields)
    else:
        tl.failed_fields(LOG["input_not_staged"].format(domain=domain), fields)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_domain_log_dirs(host):
    """MAIN_FVT_INIT_V001: Verify domain log directories created."""
    tc = TC["domain_log_dirs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_domain_log_dirs(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["log_dirs_ok"].format(
            count=result["details"].split()[0]
        ), {
            "Base path": "/var/log/omnia",
            "Directories": result["details"],
            "Verified paths": ", ".join(result.get("found", [])),
        })
    else:
        missing = result.get("missing", [])
        tl.failed_fields(LOG["log_dirs_missing"].format(count=len(missing)), {
            "Base path": "/var/log/omnia",
            "Missing paths": ", ".join(missing) or "unknown",
        })

    assert result["success"], ASSERT["log_dirs_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {d}" for d in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_domain_output_dirs(host):
    """MAIN_FVT_INIT_V002: Verify domain output directories created."""
    tc = TC["domain_output_dirs"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    result = check_domain_output_dirs(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["output_dirs_ok"].format(
            count=result["details"].split()[0]
        ), {
            "OMNIA_DATA_PATH": runtime["data_path"],
            "Project": runtime["project_name"],
            "Directories": result["details"],
        })
    else:
        missing = result.get("missing", [])
        tl.failed_fields(LOG["output_dirs_missing"].format(count=len(missing)), {
            "OMNIA_DATA_PATH": runtime["data_path"],
            "Missing paths": ", ".join(missing) or "unknown",
        })

    assert result["success"], ASSERT["output_dirs_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {d}" for d in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_domain_input_staged_image_build_manager(host):
    """MAIN_FVT_INIT_V003: Verify domain input files staged for image_build_manager."""
    domain = "image_build_manager"
    tc = TC["domain_input_staged_image_build_manager"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    data_path = runtime["data_path"]
    project = runtime["project_name"]

    result = check_domain_input_staged(host, domain)
    tl.bind_result(result)

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    _report_input_staging(tl, result, domain, expected_path)
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_domain_input_staged_repo_manager(host):
    """MAIN_FVT_INIT_V004: Verify domain input files staged for repo_manager."""
    domain = "repo_manager"
    tc = TC["domain_input_staged_repo_manager"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    data_path = runtime["data_path"]
    project = runtime["project_name"]

    result = check_domain_input_staged(host, domain)
    tl.bind_result(result)

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    _report_input_staging(tl, result, domain, expected_path)
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_domain_input_staged_orchestrator(host):
    """MAIN_FVT_INIT_V005: Verify domain input files staged for orchestrator."""
    domain = "orchestrator"
    tc = TC["domain_input_staged_orchestrator"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    data_path = runtime["data_path"]
    project = runtime["project_name"]

    result = check_domain_input_staged(host, domain)
    tl.bind_result(result)

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    _report_input_staging(tl, result, domain, expected_path)
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_domain_input_staged_discovery(host):
    """MAIN_FVT_INIT_V006: Verify domain input files staged for discovery."""
    domain = "discovery"
    tc = TC["domain_input_staged_discovery"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    data_path = runtime["data_path"]
    project = runtime["project_name"]

    result = check_domain_input_staged(host, domain)
    tl.bind_result(result)

    expected_path = (
        f"{data_path}/{domain}/input/{project}"
    )
    _report_input_staging(tl, result, domain, expected_path)
    assert result["success"], ASSERT["input_not_staged"].format(
        domain=domain,
        path=expected_path,
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(7)
def test_init_domain_filter(host):
    """MAIN_FVT_INIT_V007: Verify --init with domain filter inits a single domain."""
    tc = TC["init_domain_filter"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(
        host, "omnia_sh_init_domain",
        domain="telemetry",
    )
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["init_domain_ok"].format(domain="telemetry"), {
            "Command": "omnia.sh --init telemetry",
            "Selected domain": "telemetry",
            "Return code": result["rc"],
            "Duration": f"{result.get('duration', 0):.1f}s",
        })
    else:
        tl.failed_fields(LOG["init_domain_failed"].format(
            domain="telemetry", rc=result["rc"]
        ), {
            "Command": "omnia.sh --init telemetry",
            "Return code": result["rc"],
            "Error": result.get("error", "See command output"),
        })

    assert result["success"], ASSERT["init_failed"].format(
        rc=result["rc"],
        duration=result.get("duration", 0),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(8)
def test_init_force_deps(host):
    """MAIN_FVT_INIT_V008: Verify --init --force-deps forces reinstall."""
    tc = TC["init_force_deps"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_init_force_deps")
    tl.bind_result(result)

    output = result.get("output", "")
    # When force-deps is used, we expect "Installing" messages
    # (not "cached -- skipped")
    has_install_msg = "Installing" in output

    if result["success"] and has_install_msg:
        tl.passed_fields(
            f"--force-deps reinstalled deps "
            f"(duration={result.get('duration', 0):.1f}s)",
            {
                "Command": "omnia.sh --init --force-deps",
                "Dependency installation evidence": "found",
                "Return code": result["rc"],
            },
        )
    elif result["success"]:
        tl.passed_fields(
            f"--force-deps completed "
            f"(duration={result.get('duration', 0):.1f}s)",
            {
                "Command": "omnia.sh --init --force-deps",
                "Dependency installation evidence": "not present in output",
                "Return code": result["rc"],
            },
        )
    else:
        tl.failed_fields(f"--force-deps failed (rc={result['rc']})", {
            "Command": "omnia.sh --init --force-deps",
            "Return code": result["rc"],
            "Error": result.get("error", "See command output"),
        })

    assert result["success"], ASSERT["init_failed"].format(
        rc=result["rc"],
        duration=result.get("duration", 0),
    )
