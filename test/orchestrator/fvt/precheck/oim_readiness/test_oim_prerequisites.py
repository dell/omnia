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

"""OIM SSH, internet, and OS-version readiness contracts."""

import pytest
from library.functions import (
    check_oim_internet_reachability,
    check_oim_os_version,
    check_oim_ssh_preflight,
)

from fvt.result import verify_precheck

pytestmark = [pytest.mark.sanity]


# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.order(16)
def test_oim_ssh_preflight(host):
    """Require passwordless SSH from OIM to a mapped target node."""
    verify_precheck(host, "oim_ssh_preflight", check_oim_ssh_preflight)


@pytest.mark.order(18)
def test_oim_internet_reachability(host):
    """Require internet reachability when not in air-gapped mode."""
    verify_precheck(
        host, "oim_internet_reachability", check_oim_internet_reachability
    )


@pytest.mark.order(19)
def test_oim_os_version(host):
    """Require the OIM OS to match the expected distribution and version."""
    verify_precheck(host, "oim_os_version", check_oim_os_version)


# ── negative tests ──────────────────────────────────────────────────


@pytest.mark.negative
@pytest.mark.order(25)
def test_neg_internet_airgapped(host):
    """Verify air-gapped mode passes even without internet."""
    result = check_oim_internet_reachability(host, require_internet=False)
    assert result["success"], (
        "Air-gapped mode must pass regardless of internet availability"
    )


@pytest.mark.negative
@pytest.mark.order(27)
def test_neg_ssh_unreachable_target(host):
    """Detect SSH failure to a bogus target address."""
    from library.functions.oim_readiness_precheck_func import (
        OIM_READINESS_COMMANDS,
        run_on_host,
    )

    bogus_target = "192.0.2.1"  # RFC 5737 TEST-NET, guaranteed unreachable
    result = run_on_host(
        host, OIM_READINESS_COMMANDS["ssh_check"], bogus_target
    )
    assert result.rc != 0, (
        f"SSH to {bogus_target} should fail (unreachable TEST-NET address)"
    )


@pytest.mark.negative
@pytest.mark.order(28)
def test_neg_os_version_mismatch(host):
    """Detect failure when expected OS version does not match actual."""
    result = check_oim_os_version(
        host, expected_id="nonexistent_os", expected_version="0.0"
    )
    assert not result["success"], (
        "OS check should fail when expected ID/version do not match"
    )
    assert result["error"], "Failure must include an actionable message"
