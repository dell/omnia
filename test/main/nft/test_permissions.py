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
Omnia Main — Non-Functional File Permission Tests.

Verifies that installed files have correct permissions:
  NFT_MA_006: Installed env file is 0644
  NFT_MA_008: omnia.sh is executable
  NFT_MA_009: omnia-cli is executable
  NFT_MA_010: domain-init.sh scripts are executable
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    _resolve_clone_path,
)
from library.vars.common_vars import (
    SYSTEM_ENV_FILE,
    PROFILE_DROP_IN,
    OMNIA_SH_PATH,
    OMNIA_CLI_PATH,
    DOMAINS_WITH_INIT,
)

from omnia_auto import run_on_host


@pytest.mark.nft
@pytest.mark.order(1)
def test_env_file_permissions(host):
    """NFT_MA_006: Verify /etc/omnia/omnia.env has 0644 permissions."""
    tl = TestLogger(
        "NFT: env file permissions", "NFT_MA_006"
    )

    result = run_on_host(
        host,
        f"stat -c '%a' {SYSTEM_ENV_FILE} 2>/dev/null",
    )
    perms = result.stdout.strip()

    ok = perms == "644"

    if ok:
        tl.passed(
            f"{SYSTEM_ENV_FILE} has correct permissions (644)"
        )
    else:
        tl.failed(
            f"{SYSTEM_ENV_FILE} has permissions {perms},"
            f" expected 644"
        )

    assert ok, (
        f"{SYSTEM_ENV_FILE} should have permissions 644,"
        f" got {perms}"
    )


@pytest.mark.nft
@pytest.mark.order(2)
def test_omnia_sh_executable(host):
    """NFT_MA_008: Verify omnia.sh source file is executable in repo."""
    tl = TestLogger(
        "NFT: omnia.sh executable", "NFT_MA_008"
    )
    clone_path = _resolve_clone_path()

    sh_path = f"{clone_path}/{OMNIA_SH_PATH}"
    result = run_on_host(
        host,
        f"test -x {sh_path} && echo executable",
    )
    ok = "executable" in result.stdout

    if ok:
        tl.passed(f"{OMNIA_SH_PATH} is executable")
    else:
        tl.failed(f"{OMNIA_SH_PATH} is NOT executable")

    assert ok, (
        f"{OMNIA_SH_PATH} must be executable"
        f" (chmod +x or git update-index --chmod=+x)"
    )


@pytest.mark.nft
@pytest.mark.order(3)
def test_omnia_cli_executable(host):
    """NFT_MA_009: Verify omnia-cli source file is executable in repo."""
    tl = TestLogger(
        "NFT: omnia-cli executable", "NFT_MA_009"
    )
    clone_path = _resolve_clone_path()

    cli_path = f"{clone_path}/{OMNIA_CLI_PATH}"
    result = run_on_host(
        host,
        f"test -x {cli_path} && echo executable",
    )
    ok = "executable" in result.stdout

    if ok:
        tl.passed(f"{OMNIA_CLI_PATH} is executable")
    else:
        tl.failed(f"{OMNIA_CLI_PATH} is NOT executable")

    assert ok, (
        f"{OMNIA_CLI_PATH} must be executable"
        f" (chmod +x or git update-index --chmod=+x)"
    )


@pytest.mark.nft
@pytest.mark.order(4)
def test_domain_init_scripts_executable(host):
    """NFT_MA_010: Verify all domain-init.sh scripts are executable."""
    tl = TestLogger(
        "NFT: domain-init.sh permissions", "NFT_MA_010"
    )
    clone_path = _resolve_clone_path()

    not_executable = []
    for domain in DOMAINS_WITH_INIT:
        script = (
            f"{clone_path}/src/{domain}/domain-init.sh"
        )
        result = run_on_host(
            host,
            f"test -x {script} && echo executable",
        )
        if "executable" not in result.stdout:
            not_executable.append(
                f"src/{domain}/domain-init.sh"
            )

    ok = len(not_executable) == 0

    if ok:
        tl.passed(
            f"All {len(DOMAINS_WITH_INIT)} "
            f"domain-init.sh scripts are executable"
        )
    else:
        tl.failed(
            f"{len(not_executable)} domain-init.sh "
            f"script(s) not executable: "
            f"{', '.join(not_executable)}"
        )

    assert ok, (
        f"domain-init.sh scripts must be executable: "
        f"{', '.join(not_executable)}"
    )
