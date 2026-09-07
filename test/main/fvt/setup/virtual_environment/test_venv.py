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
Omnia Main Setup — Venv Verification.

MAIN_FVT_SETUP_V007: Verify Python venv created at OMNIA_VENV_PATH
MAIN_FVT_SETUP_V008: Verify ansible is available in venv
MAIN_FVT_SETUP_V009: Verify all Python requirements installed in venv
MAIN_FVT_SETUP_V010: Verify installed Galaxy collections and versions
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import (
    TestLogger,
    check_galaxy_collections,
    check_pip_packages,
)
from library.functions.omnia_main_func import (
    check_venv_created,
    check_ansible_available,
    resolve_runtime_paths,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(7)
def test_venv_created(host):
    """MAIN_FVT_SETUP_V007: Verify Python venv created at OMNIA_VENV_PATH."""
    tc = TC["venv_created"]
    tl = TestLogger(tc["title"], tc["id"])
    venv_path = resolve_runtime_paths(host)["venv_path"]

    result = check_venv_created(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["venv_ok"].format(path=venv_path), {
            "Virtual environment": venv_path,
            "Python executable": f"{venv_path}/bin/python3",
        })
    else:
        tl.failed_fields(LOG["venv_missing"].format(path=venv_path), {
            "Virtual environment": venv_path,
            "Status": result.get("error", "missing"),
        })

    assert result["success"], ASSERT["venv_missing"].format(
        path=venv_path,
    )


@pytest.mark.sanity
@pytest.mark.order(8)
def test_ansible_available(host):
    """MAIN_FVT_SETUP_V008: Verify ansible is available in venv."""
    tc = TC["ansible_available"]
    tl = TestLogger(tc["title"], tc["id"])
    venv_path = resolve_runtime_paths(host)["venv_path"]

    result = check_ansible_available(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["ansible_ok"].format(version=result["details"]), {
            "Virtual environment": venv_path,
            "Ansible": result["details"],
        })
    else:
        tl.failed_fields(LOG["ansible_missing"], {
            "Virtual environment": venv_path,
            "Expected executable": f"{venv_path}/bin/ansible",
        })

    assert result["success"], ASSERT["ansible_missing"].format(
        path=venv_path,
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_pip_packages_installed(host):
    """MAIN_FVT_SETUP_V009: Verify all Python requirements installed in venv."""
    tc = TC["pip_packages_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    venv_path = resolve_runtime_paths(host)["venv_path"]
    result = check_pip_packages(host)
    tl.bind_result(result)
    issues = (
        result.get("missing_files", [])
        + result.get("invalid_requirements", [])
        + result.get("missing", [])
        + result.get("version_mismatches", [])
    )

    if result["success"]:
        fields = {
            "Virtual environment": venv_path,
            "Requirement files": (
                f"{result['requirement_file_count']}/"
                f"{result['required_file_count']} processed"
            ),
        }
        for index, package in enumerate(result["core_packages"], start=1):
            fields[f"Core package {index:02d}"] = package
        for index, package in enumerate(result["domain_packages"], start=1):
            fields[f"Domain package {index:02d}"] = package
        tl.passed_fields(LOG["pip_ok"].format(
            count=result["required_count"]
        ), fields)
    else:
        fields = {
            "Virtual environment": venv_path,
            "Requirement files": (
                f"{result.get('requirement_file_count', 0)}/"
                f"{result.get('required_file_count', 7)} processed"
            ),
        }
        reported_issues = issues or [result.get("error", "unknown")]
        for index, issue in enumerate(reported_issues, start=1):
            fields[f"Issue {index:02d}"] = issue
        tl.failed_fields(
            f"{len(issues)} Python requirement issue(s) found", fields
        )

    assert result["success"], ASSERT["pip_packages_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {issue}" for issue in issues
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(10)
def test_galaxy_collections_installed(host):
    """MAIN_FVT_SETUP_V010: Verify installed Galaxy collections and versions."""
    tc = TC["galaxy_collections_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    venv_path = resolve_runtime_paths(host)["venv_path"]

    result = check_galaxy_collections(host)
    tl.bind_result(result)

    if result["success"]:
        fields = {
            "Virtual environment": venv_path,
        }
        for index, collection in enumerate(result["collections"], start=1):
            fields[f"Collection {index:02d}"] = collection
        tl.passed_fields(
            LOG["galaxy_ok"].format(count=result["details"]), fields
        )
    else:
        tl.failed_fields(LOG["galaxy_missing"], {
            "Virtual environment": venv_path,
            "Expected command": "ansible-galaxy collection list",
        })

    assert result["success"], ASSERT["galaxy_missing"].format(
        path=venv_path,
    )
