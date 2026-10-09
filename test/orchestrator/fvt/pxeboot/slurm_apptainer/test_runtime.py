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

"""Read-only Apptainer runtime, storage, image, and access contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_apptainer_image_inventory,
    check_apptainer_ldap_readability,
    check_apptainer_non_root_execution,
    check_apptainer_pulp_policy,
    check_apptainer_runtime,
    check_apptainer_shared_artifacts,
    check_apptainer_shared_storage,
    check_apptainer_sif_format,
    check_apptainer_sif_integrity,
    check_apptainer_sif_permissions,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41901)
def test_apptainer_runtime(host):
    """Verify the Apptainer executable and version on every compute node."""
    tc = TC["apptainer_runtime"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_runtime)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41902)
def test_apptainer_shared_artifacts(host):
    """Verify shared image directories and downloader artifacts."""
    tc = TC["apptainer_shared_artifacts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_shared_artifacts)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41903)
def test_apptainer_pulp_policy(host):
    """Verify the generated downloader uses only the configured Pulp source."""
    tc = TC["apptainer_pulp_policy"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_pulp_policy)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41904)
def test_apptainer_shared_storage(host):
    """Verify /hpc_tools is a shared mounted filesystem on every compute."""
    tc = TC["apptainer_shared_storage"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_shared_storage)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41908)
def test_apptainer_image_inventory(host):
    """Verify every compute sees one consistent non-empty SIF inventory."""
    tc = TC["apptainer_image_inventory"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_image_inventory)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41909)
def test_apptainer_sif_format(host):
    """Verify each discovered image is a valid inspectable SIF."""
    tc = TC["apptainer_sif_format"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_sif_format)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41910)
def test_apptainer_sif_permissions(host):
    """Verify shared SIF files are non-empty and world-readable."""
    tc = TC["apptainer_sif_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_sif_permissions)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.order(41911)
def test_apptainer_sif_integrity(host):
    """Verify the selected SIF has the same checksum on every compute."""
    tc = TC["apptainer_sif_integrity"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_sif_integrity)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.sanity
@pytest.mark.order(41912)
def test_apptainer_ldap_readability(host):
    """Verify the LDAP test identity can read a shared SIF when enabled."""
    tc = TC["apptainer_ldap_readability"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_ldap_readability)


@pytest.mark.apptainer
@pytest.mark.non_disruptive
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(41913)
def test_apptainer_non_root_execution(host):
    """Verify an unprivileged local identity can execute a shared SIF."""
    tc = TC["apptainer_non_root_execution"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_non_root_execution)
