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
Omnia Main — Non-Functional Idempotency Tests.

Verifies that running omnia.sh commands twice produces no side effects:
  NFT_MA_003: --setup-venv is idempotent (venv and env file survive second run)
  NFT_MA_004: --init is idempotent (domain dirs survive second run)
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    check_venv_created,
    check_env_file_installed,
    check_domain_log_dirs,
    check_domain_input_staged,
)
from library.vars.common_vars import DOMAINS_WITH_INIT


@pytest.mark.nft
@pytest.mark.order(1)
def test_setup_venv_idempotent(host):
    """NFT_MA_003: Verify running --setup-venv twice produces no errors."""
    tl = TestLogger("NFT: setup-venv idempotency", "NFT_MA_003")

    # First run
    result1 = run_omnia_cmd(host, "omnia_sh_setup_venv")
    if not result1["success"]:
        output = result1.get("output", "")
        # Skip if env validation blocks setup (prerequisite not met)
        if (
            "SYSTEM_ADMIN_NIC_IPV4" in output
            or "validate" in output.lower()
        ):
            pytest.skip(
                "setup-venv requires a configured omnia.env "
                "(SYSTEM_ADMIN_NIC_IPV4 not set)"
            )
        tl.failed(
            f"First setup-venv failed (rc={result1['rc']})"
        )
        pytest.fail(
            f"First setup-venv failed (rc={result1['rc']}): "
            f"{result1.get('error', '')}"
        )

    # Second run
    result2 = run_omnia_cmd(host, "omnia_sh_setup_venv")

    # Post-check: venv and env file still intact
    venv_ok = check_venv_created(host)
    env_ok = check_env_file_installed(host)

    all_ok = (
        result2["success"]
        and venv_ok["success"]
        and env_ok["success"]
    )

    if all_ok:
        tl.passed(
            f"setup-venv idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"Venv and env file stable."
        )
    else:
        issues = []
        if not result2["success"]:
            issues.append(f"second run rc={result2['rc']}")
        if not venv_ok["success"]:
            issues.append("venv missing after second run")
        if not env_ok["success"]:
            issues.append("omnia.env missing after second run")
        tl.failed(f"setup-venv not idempotent: {'; '.join(issues)}")

    assert result2["success"], (
        f"Second setup-venv run failed (rc={result2['rc']}): "
        f"{result2.get('error', '')}"
    )
    assert venv_ok["success"], (
        "Python venv missing after second --setup-venv run"
    )
    assert env_ok["success"], (
        "omnia.env missing after second --setup-venv run"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_init_idempotent(host):
    """NFT_MA_004: Verify running --init twice leaves domain state unchanged."""
    tl = TestLogger("NFT: init idempotency", "NFT_MA_004")

    config = load_test_config()
    data_path = config.get("omnia_data_path", "/opt/omnia")
    project = config.get("project_name", "project_default")

    # First run
    result1 = run_omnia_cmd(host, "omnia_sh_init")
    if not result1["success"]:
        tl.failed(
            f"First init failed (rc={result1['rc']})"
        )
        pytest.fail(
            f"First init failed (rc={result1['rc']}): "
            f"{result1.get('error', '')}"
        )

    # Second run (should be no-prompt since dirs exist;
    # omnia.sh --init passes --force to each domain-init.sh)
    result2 = run_omnia_cmd(host, "omnia_sh_init")

    # Post-check: log dirs and at least one domain's input files still present
    logs_ok = check_domain_log_dirs(host)

    # Check a representative domain that always has input files
    input_ok = check_domain_input_staged(host, "image_build_manager")

    all_ok = (
        result2["success"]
        and logs_ok["success"]
        and input_ok["success"]
    )

    if all_ok:
        tl.passed(
            f"init idempotent: "
            f"run1={result1['duration']:.1f}s, "
            f"run2={result2['duration']:.1f}s. "
            f"Domain log dirs and input files stable."
        )
    else:
        issues = []
        if not result2["success"]:
            issues.append(f"second run rc={result2['rc']}")
        if not logs_ok["success"]:
            missing = logs_ok.get("missing", [])
            issues.append(
                f"log dirs missing after second run: {missing}"
            )
        if not input_ok["success"]:
            issues.append(
                "image_build_manager input files missing after second run"
            )
        tl.failed(f"init not idempotent: {'; '.join(issues)}")

    assert result2["success"], (
        f"Second --init run failed (rc={result2['rc']}): "
        f"{result2.get('error', '')}"
    )
    assert logs_ok["success"], (
        f"Domain log dirs missing after second --init: "
        f"{logs_ok.get('missing', [])}"
    )
    assert input_ok["success"], (
        f"image_build_manager input files missing after second --init "
        f"at {data_path}/image_build_manager/input/{project}"
    )
