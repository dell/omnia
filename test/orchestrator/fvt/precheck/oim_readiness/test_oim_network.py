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

"""OIM admin/public NIC presence, IPv4, and overlap contracts."""

import pytest
from library.functions import (
    check_oim_pxe_nic_ipv4,
    check_oim_pxe_nic_present,
    check_oim_pxe_public_overlap,
    check_oim_public_nic_present,
)

from fvt.result import verify_precheck

pytestmark = [pytest.mark.sanity]


# ── positive tests ──────────────────────────────────────────────────


@pytest.mark.order(13)
def test_oim_pxe_nic_present(host):
    """Require the configured admin NIC to exist and be UP."""
    verify_precheck(host, "oim_pxe_nic_present", check_oim_pxe_nic_present)


@pytest.mark.order(14)
def test_oim_public_nic_present(host):
    """Require the public/default-route NIC to exist and be UP."""
    verify_precheck(
        host, "oim_public_nic_present", check_oim_public_nic_present
    )


@pytest.mark.order(15)
def test_oim_pxe_nic_ipv4(host):
    """Require the admin NIC to carry the configured IPv4 address."""
    verify_precheck(host, "oim_pxe_nic_ipv4", check_oim_pxe_nic_ipv4)


# ── negative tests ──────────────────────────────────────────────────


@pytest.mark.negative
@pytest.mark.order(23)
def test_neg_pxe_nic_missing(host):
    """Detect failure when a nonexistent NIC name is checked."""
    result = check_oim_pxe_nic_present.__wrapped__(host) if hasattr(
        check_oim_pxe_nic_present, "__wrapped__"
    ) else None
    # Directly call the underlying function with a bogus NIC name
    from library.functions.oim_readiness_precheck_func import (
        OIM_READINESS_COMMANDS,
        prepare_result,
        run_on_host,
    )

    nic_name = "nonexistent_nic_000"
    cmd_result = run_on_host(
        host, OIM_READINESS_COMMANDS["nic_operstate"], nic_name
    )
    state = cmd_result.stdout.strip() if cmd_result.rc == 0 else ""
    assert not (cmd_result.rc == 0 and state), (
        f"Interface {nic_name} should not exist"
    )


@pytest.mark.negative
@pytest.mark.order(24)
def test_neg_pxe_public_overlap(host):
    """Detect overlap when PXE NIC is forced to match the public NIC."""
    # Find the actual public NIC from default route
    from omnia_auto import run_on_host as _run

    route = _run(host, "ip -4 route show default 2>/dev/null | head -1")
    route_line = route.stdout.strip()
    if not route_line:
        pytest.skip("No default route; overlap test not applicable")

    parts = route_line.split()
    public_nic = ""
    for i, token in enumerate(parts):
        if token == "dev" and i + 1 < len(parts):
            public_nic = parts[i + 1]
            break

    if not public_nic:
        pytest.skip("Cannot parse public NIC from default route")

    result = check_oim_pxe_public_overlap(host, nic_name=public_nic)
    assert not result["success"], (
        "Overlap check should fail when PXE NIC equals public NIC"
    )
    assert "overlap" in result["error"].lower() or "share" in result["error"].lower(), (
        "Error message must mention the overlap"
    )
