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

"""PowerVault iSCSI and multipath infrastructure validation tests."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_powervault_iscsi_service,
    check_powervault_iscsi_initiator_name,
    check_powervault_iscsi_discovery,
    check_powervault_iscsi_sessions,
    check_powervault_iscsi_startup_automatic,
    check_powervault_portal_reachability,
    check_powervault_multipath_service,
    check_powervault_multipath_device,
    check_powervault_multipath_redundancy,
)


@pytest.mark.sanity
@pytest.mark.order(301)
@pytest.mark.powervault_infrastructure
def test_powervault_iscsi_service(host):
    """Verify iscsid is active and enabled on all PowerVault target nodes."""
    verify_pxeboot(host, "powervault_iscsi_service", check_powervault_iscsi_service)


@pytest.mark.sanity
@pytest.mark.order(302)
@pytest.mark.powervault_infrastructure
def test_powervault_iscsi_initiator_name(host):
    """Verify iSCSI initiator name matches config on all target nodes."""
    verify_pxeboot(host, "powervault_iscsi_initiator_name", check_powervault_iscsi_initiator_name)


@pytest.mark.sanity
@pytest.mark.order(303)
@pytest.mark.powervault_infrastructure
def test_powervault_iscsi_discovery(host):
    """Verify iSCSI target discovery succeeds from all portal IPs."""
    verify_pxeboot(host, "powervault_iscsi_discovery", check_powervault_iscsi_discovery)


@pytest.mark.sanity
@pytest.mark.order(304)
@pytest.mark.powervault_infrastructure
def test_powervault_iscsi_sessions(host):
    """Verify iSCSI sessions are active on all target nodes."""
    verify_pxeboot(host, "powervault_iscsi_sessions", check_powervault_iscsi_sessions)


@pytest.mark.sanity
@pytest.mark.order(305)
@pytest.mark.powervault_infrastructure
def test_powervault_iscsi_startup_automatic(host):
    """Verify iSCSI node startup is automatic on all target nodes."""
    verify_pxeboot(host, "powervault_iscsi_startup_automatic", check_powervault_iscsi_startup_automatic)


@pytest.mark.sanity
@pytest.mark.order(306)
@pytest.mark.powervault_infrastructure
def test_powervault_portal_reachability(host):
    """Verify iSCSI portal ports are reachable and sessions healthy."""
    verify_pxeboot(host, "powervault_portal_reachability", check_powervault_portal_reachability)


@pytest.mark.sanity
@pytest.mark.order(307)
@pytest.mark.powervault_infrastructure
def test_powervault_multipath_service(host):
    """Verify multipathd is active and enabled on all target nodes."""
    verify_pxeboot(host, "powervault_multipath_service", check_powervault_multipath_service)


@pytest.mark.sanity
@pytest.mark.order(308)
@pytest.mark.powervault_infrastructure
def test_powervault_multipath_device(host):
    """Verify multipath device exists and matches volume_id."""
    verify_pxeboot(host, "powervault_multipath_device", check_powervault_multipath_device)


@pytest.mark.sanity
@pytest.mark.order(309)
@pytest.mark.powervault_infrastructure
def test_powervault_multipath_redundancy(host):
    """Verify multipath device has multiple paths for redundancy."""
    verify_pxeboot(host, "powervault_multipath_redundancy", check_powervault_multipath_redundancy)
