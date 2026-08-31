# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not this file except in compliance with the License.
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
Orchestrator Validate — Slurm SSH Connectivity Validation.

TC_SL_017-TC_SL_028: Passwordless SSH between all node type pairs
"""

import pytest

from library.functions import TestLogger
from library.functions.slurm_func import (
    check_slurm_enabled,
    check_passwordless_ssh,
)
from library.messages import (
    SLURM_TEST_LOG_MSGS as LOG,
    SLURM_TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.slurm_vars import TEST_CASES as TC


def _skip_if_slurm_disabled(host):
    """Skip test if Slurm is not enabled in catalog."""
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(1)
def test_ssh_control_to_compute(host):
    """TC_SL_017: Passwordless SSH from control to compute nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_control_to_compute"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from control to compute nodes")
    result = check_passwordless_ssh(host, "control", "compute")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="control", to_node="compute"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="control", to_node="compute"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="control", to_node="compute")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(2)
def test_ssh_control_to_login(host):
    """TC_SL_018: Passwordless SSH from control to login nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_control_to_login"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from control to login nodes")
    result = check_passwordless_ssh(host, "control", "login")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="control", to_node="login"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="control", to_node="login"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="control", to_node="login")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(3)
def test_ssh_control_to_login_compiler(host):
    """TC_SL_019: Passwordless SSH from control to login compiler nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_control_to_login_compiler"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from control to login compiler nodes")
    result = check_passwordless_ssh(host, "control", "login_compiler")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="control", to_node="login_compiler"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="control", to_node="login_compiler"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="control", to_node="login_compiler")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(4)
def test_ssh_compute_to_control(host):
    """TC_SL_020: Passwordless SSH from compute to control nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_compute_to_control"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from compute to control nodes")
    result = check_passwordless_ssh(host, "compute", "control")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="compute", to_node="control"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="compute", to_node="control"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="compute", to_node="control")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(5)
def test_ssh_compute_to_login(host):
    """TC_SL_021: Passwordless SSH from compute to login nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_compute_to_login"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from compute to login nodes")
    result = check_passwordless_ssh(host, "compute", "login")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="compute", to_node="login"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="compute", to_node="login"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="compute", to_node="login")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(6)
def test_ssh_compute_to_login_compiler(host):
    """TC_SL_022: Passwordless SSH from compute to login compiler nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_compute_to_login_compiler"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from compute to login compiler nodes")
    result = check_passwordless_ssh(host, "compute", "login_compiler")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="compute", to_node="login_compiler"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="compute", to_node="login_compiler"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="compute", to_node="login_compiler")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(7)
def test_ssh_login_to_control(host):
    """TC_SL_023: Passwordless SSH from login to control nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_to_control"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login to control nodes")
    result = check_passwordless_ssh(host, "login", "control")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login", to_node="control"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login", to_node="control"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login", to_node="control")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(8)
def test_ssh_login_to_compute(host):
    """TC_SL_024: Passwordless SSH from login to compute nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_to_compute"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login to compute nodes")
    result = check_passwordless_ssh(host, "login", "compute")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login", to_node="compute"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login", to_node="compute"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login", to_node="compute")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(9)
def test_ssh_login_to_login_compiler(host):
    """TC_SL_025: Passwordless SSH from login to login compiler nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_to_login_compiler"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login to login compiler nodes")
    result = check_passwordless_ssh(host, "login", "login_compiler")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login", to_node="login_compiler"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login", to_node="login_compiler"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login", to_node="login_compiler")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(10)
def test_ssh_login_compiler_to_control(host):
    """TC_SL_026: Passwordless SSH from login compiler to control nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_compiler_to_control"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login compiler to control nodes")
    result = check_passwordless_ssh(host, "login_compiler", "control")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login_compiler", to_node="control"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login_compiler", to_node="control"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login_compiler", to_node="control")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(11)
def test_ssh_login_compiler_to_compute(host):
    """TC_SL_027: Passwordless SSH from login compiler to compute nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_compiler_to_compute"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login compiler to compute nodes")
    result = check_passwordless_ssh(host, "login_compiler", "compute")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login_compiler", to_node="compute"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login_compiler", to_node="compute"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login_compiler", to_node="compute")


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(12)
def test_ssh_login_compiler_to_login(host):
    """TC_SL_028: Passwordless SSH from login compiler to login nodes."""
    _skip_if_slurm_disabled(host)

    tc = TC["ssh_login_compiler_to_login"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing SSH from login compiler to login nodes")
    result = check_passwordless_ssh(host, "login_compiler", "login")

    if result["success"]:
        tl.passed(LOG["ssh_ok"].format(from_node="login_compiler", to_node="login"), result["details"])
    else:
        tl.failed(LOG["ssh_failed"].format(from_node="login_compiler", to_node="login"), result["error"])

    assert result["success"], ASSERT["ssh_failed"].format(from_node="login_compiler", to_node="login")
