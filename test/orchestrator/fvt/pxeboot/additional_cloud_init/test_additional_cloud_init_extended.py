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
- TC-C01 .. TC-C03: RHEL compatibility, multi-FG, upgrade mode

Tests skip automatically when additional_cloud_init_config_file is empty
or not configured in orchestrator_config.yml.
"""

import pytest
from library.functions import (
    check_additional_cloud_init_bss_common,
    check_additional_cloud_init_bss_per_fg,
    check_additional_cloud_init_common_template,
    check_additional_cloud_init_conditional_rendering,
    check_additional_cloud_init_merge_behavior,
    check_additional_cloud_init_multi_fg_compat,
    check_additional_cloud_init_per_fg_template,
    check_additional_cloud_init_rhel_compat,
    check_additional_cloud_init_upgrade_mode,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.additional_cloud_init,
    pytest.mark.non_disruptive,
]


# ── Template rendering (TC-F08 .. TC-F10) ──────────────────────────────


@pytest.mark.order(330)
def test_additional_cloud_init_common_template(host):
    """Verify common cloud-init template rendered with merge_how directive."""
    verify_pxeboot(
        host,
        "additional_cloud_init_common_template",
        check_additional_cloud_init_common_template,
    )


@pytest.mark.order(331)
def test_additional_cloud_init_per_fg_template(host):
    """Verify per-FG cloud-init templates rendered correctly."""
    verify_pxeboot(
        host,
        "additional_cloud_init_per_fg_template",
        check_additional_cloud_init_per_fg_template,
    )


@pytest.mark.order(332)
def test_additional_cloud_init_conditional_rendering(host):
    """Verify empty sections are omitted from rendered cloud-init templates."""
    verify_pxeboot(
        host,
        "additional_cloud_init_conditional_rendering",
        check_additional_cloud_init_conditional_rendering,
    )


# ── BSS registration (TC-F11 .. TC-F13) ────────────────────────────────


@pytest.mark.order(333)
def test_additional_cloud_init_bss_common(host):
    """Verify BSS registration for the common cloud-init group."""
    verify_pxeboot(
        host,
        "additional_cloud_init_bss_common",
        check_additional_cloud_init_bss_common,
    )


@pytest.mark.order(334)
def test_additional_cloud_init_bss_per_fg(host):
    """Verify BSS registration for per-functional-group cloud-init groups."""
    verify_pxeboot(
        host,
        "additional_cloud_init_bss_per_fg",
        check_additional_cloud_init_bss_per_fg,
    )


@pytest.mark.order(335)
def test_additional_cloud_init_merge_behavior(host):
    """Verify merge_how=no_replace preserves platform defaults."""
    verify_pxeboot(
        host,
        "additional_cloud_init_merge_behavior",
        check_additional_cloud_init_merge_behavior,
    )


# ── Compatibility (TC-C01 .. TC-C03) ───────────────────────────────────


@pytest.mark.order(336)
def test_additional_cloud_init_rhel_compat(host):
    """Verify additional cloud-init works on RHEL 10.x nodes."""
    verify_pxeboot(
        host,
        "additional_cloud_init_rhel_compat",
        check_additional_cloud_init_rhel_compat,
    )


@pytest.mark.order(337)
def test_additional_cloud_init_multi_fg_compat(host):
    """Verify additional cloud-init with multiple functional groups."""
    verify_pxeboot(
        host,
        "additional_cloud_init_multi_fg_compat",
        check_additional_cloud_init_multi_fg_compat,
    )


@pytest.mark.order(338)
def test_additional_cloud_init_upgrade_mode(host):
    """Verify additional cloud-init upgrade mode compatibility."""
    verify_pxeboot(
        host,
        "additional_cloud_init_upgrade_mode",
        check_additional_cloud_init_upgrade_mode,
    )
