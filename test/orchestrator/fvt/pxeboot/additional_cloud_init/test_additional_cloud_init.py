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

"""Additional cloud-init verification for stateless node provisioning.

Checks that additional_cloud_init configuration (common and per-FG sections)
was deployed correctly:
- SMD groups created for common and per-functional-group cloud-init
- Metadata-service templates registered and valid
- write_files entries produced files on provisioned nodes
- runcmd entries executed as part of cloud-init final stage

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    TestLogger,
    check_additional_cloud_init_metadata_groups,
    check_additional_cloud_init_runcmd,
    check_additional_cloud_init_smd_groups,
    check_additional_cloud_init_write_files,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40301)
def test_additional_cloud_init_smd_groups(host):
    """Verify SMD groups exist for additional cloud-init configuration."""
    tc = TC["additional_cloud_init_smd_groups"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_smd_groups)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40302)
def test_additional_cloud_init_metadata_groups(host):
    """Verify metadata-service groups and templates for additional cloud-init."""
    tc = TC["additional_cloud_init_metadata_groups"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_metadata_groups)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40303)
def test_additional_cloud_init_write_files(host):
    """Verify write_files entries were applied on provisioned nodes."""
    tc = TC["additional_cloud_init_write_files"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_write_files)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40304)
def test_additional_cloud_init_runcmd(host):
    """Verify runcmd entries executed during cloud-init on provisioned nodes."""
    tc = TC["additional_cloud_init_runcmd"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_runcmd)
