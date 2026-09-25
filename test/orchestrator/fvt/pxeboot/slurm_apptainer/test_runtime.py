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

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.apptainer, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(263)
def test_apptainer_runtime(host):
    """Verify the Apptainer executable and version on every compute node."""
    verify_pxeboot(host, "apptainer_runtime", check_apptainer_runtime)


@pytest.mark.sanity
@pytest.mark.order(264)
def test_apptainer_shared_artifacts(host):
    """Verify shared image directories and downloader artifacts."""
    verify_pxeboot(host, "apptainer_shared_artifacts", check_apptainer_shared_artifacts)


@pytest.mark.sanity
@pytest.mark.order(265)
def test_apptainer_pulp_policy(host):
    """Verify the generated downloader uses only the configured Pulp source."""
    verify_pxeboot(host, "apptainer_pulp_policy", check_apptainer_pulp_policy)


@pytest.mark.sanity
@pytest.mark.order(266)
def test_apptainer_shared_storage(host):
    """Verify /hpc_tools is a shared mounted filesystem on every compute."""
    verify_pxeboot(host, "apptainer_shared_storage", check_apptainer_shared_storage)


@pytest.mark.sanity
@pytest.mark.order(270)
def test_apptainer_image_inventory(host):
    """Verify every compute sees one consistent non-empty SIF inventory."""
    verify_pxeboot(host, "apptainer_image_inventory", check_apptainer_image_inventory)


@pytest.mark.sanity
@pytest.mark.order(271)
def test_apptainer_sif_format(host):
    """Verify each discovered image is a valid inspectable SIF."""
    verify_pxeboot(host, "apptainer_sif_format", check_apptainer_sif_format)


@pytest.mark.sanity
@pytest.mark.order(272)
def test_apptainer_sif_permissions(host):
    """Verify shared SIF files are non-empty and world-readable."""
    verify_pxeboot(host, "apptainer_sif_permissions", check_apptainer_sif_permissions)


@pytest.mark.sanity
@pytest.mark.order(273)
def test_apptainer_sif_integrity(host):
    """Verify the selected SIF has the same checksum on every compute."""
    verify_pxeboot(host, "apptainer_sif_integrity", check_apptainer_sif_integrity)


@pytest.mark.sanity
@pytest.mark.order(274)
def test_apptainer_ldap_readability(host):
    """Verify the LDAP test identity can read a shared SIF when enabled."""
    verify_pxeboot(host, "apptainer_ldap_readability", check_apptainer_ldap_readability)


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(275)
def test_apptainer_non_root_execution(host):
    """Verify an unprivileged local identity can execute a shared SIF."""
    verify_pxeboot(
        host, "apptainer_non_root_execution", check_apptainer_non_root_execution
    )
