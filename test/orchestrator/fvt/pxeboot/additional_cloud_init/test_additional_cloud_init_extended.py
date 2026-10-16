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

"""Extended additional cloud-init verification — templates, BSS, compatibility.

Covers 2.2 baseline gaps:
- TC-F08 .. TC-F13: template rendering and BSS registration
- TC-C01 .. TC-C02: RHEL compatibility, multi-FG

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    TestLogger,
    check_additional_cloud_init_bss_common,
    check_additional_cloud_init_bss_per_fg,
    check_additional_cloud_init_common_template,
    check_additional_cloud_init_conditional_rendering,
    check_additional_cloud_init_merge_behavior,
    check_additional_cloud_init_multi_fg_compat,
    check_additional_cloud_init_per_fg_template,
    check_additional_cloud_init_rhel_compat,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

# ── Template rendering (TC-F08 .. TC-F10) ──────────────────────────────


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40305)
def test_additional_cloud_init_common_template(host):
    """Verify common cloud-init template rendered with merge_how directive."""
    tc = TC["additional_cloud_init_common_template"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_common_template)


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40306)
def test_additional_cloud_init_per_fg_template(host):
    """Verify per-FG cloud-init templates rendered correctly."""
    tc = TC["additional_cloud_init_per_fg_template"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_per_fg_template)


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40307)
def test_additional_cloud_init_conditional_rendering(host):
    """Verify empty sections are omitted from rendered cloud-init templates."""
    tc = TC["additional_cloud_init_conditional_rendering"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(
        test_log, tc, host, check_additional_cloud_init_conditional_rendering,
    )


# ── BSS registration (TC-F11 .. TC-F13) ────────────────────────────────


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40308)
def test_additional_cloud_init_bss_common(host):
    """Verify BSS registration for the common cloud-init group."""
    tc = TC["additional_cloud_init_bss_common"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_bss_common)


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40309)
def test_additional_cloud_init_bss_per_fg(host):
    """Verify BSS registration for per-functional-group cloud-init groups."""
    tc = TC["additional_cloud_init_bss_per_fg"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_bss_per_fg)


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40310)
def test_additional_cloud_init_merge_behavior(host):
    """Verify merge_how=no_replace preserves platform defaults."""
    tc = TC["additional_cloud_init_merge_behavior"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_merge_behavior)


# ── Compatibility (TC-C01 .. TC-C02) ───────────────────────────────────


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40311)
def test_additional_cloud_init_rhel_compat(host):
    """Verify additional cloud-init works on RHEL 10.x nodes."""
    tc = TC["additional_cloud_init_rhel_compat"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_rhel_compat)


@pytest.mark.sanity
@pytest.mark.additional_cloud_init
@pytest.mark.non_disruptive
@pytest.mark.order(40312)
def test_additional_cloud_init_multi_fg_compat(host):
    """Verify additional cloud-init with multiple functional groups."""
    tc = TC["additional_cloud_init_multi_fg_compat"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_additional_cloud_init_multi_fg_compat)
