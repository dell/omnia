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

"""Unit tests for _extract_bundle_name — regression for versioned filename parsing.

Commit 500ccde2 introduced this function to strip version suffixes from
config filenames. Previously, service_k8s used '-' as version separator
(service_k8s-1.35.1.json) which broke bundle matching. The fix uses '_'
(service_k8s_v1.35.1.json) and this function strips either format.
"""

import pytest

from generate_catalog import _extract_bundle_name


class TestExtractBundleName:
    """Tests for _extract_bundle_name version stripping."""

    def test_no_version_suffix(self):
        """Plain bundle name without version should return as-is."""
        assert _extract_bundle_name("slurm_custom") == "slurm_custom"
        assert _extract_bundle_name("default_packages") == "default_packages"
        assert _extract_bundle_name("nfs") == "nfs"

    def test_underscore_version_with_v_prefix(self):
        """service_k8s_v1.35.1 should strip to service_k8s."""
        assert _extract_bundle_name("service_k8s_v1.35.1") == "service_k8s"

    def test_underscore_version_without_v_prefix(self):
        """service_k8s_1.35.1 should strip to service_k8s."""
        assert _extract_bundle_name("service_k8s_1.35.1") == "service_k8s"

    def test_dash_version_separator(self):
        """service_k8s-1.35.1 should strip to service_k8s (legacy format)."""
        assert _extract_bundle_name("service_k8s-1.35.1") == "service_k8s"

    def test_dash_version_with_v_prefix(self):
        """service_k8s-v1.35.1 should strip to service_k8s."""
        assert _extract_bundle_name("service_k8s-v1.35.1") == "service_k8s"

    def test_multi_segment_version(self):
        """Versions with 3+ segments should be stripped."""
        assert _extract_bundle_name("service_k8s_v1.35.1") == "service_k8s"

    def test_single_segment_version(self):
        """Single-segment version should be stripped."""
        assert _extract_bundle_name("nfs_1") == "nfs"

    def test_known_bundle_exact_match(self):
        """Known bundle names should match exactly."""
        assert _extract_bundle_name("openldap") == "openldap"
        assert _extract_bundle_name("openmpi") == "openmpi"
        assert _extract_bundle_name("ucx") == "ucx"

    def test_csi_driver_with_version(self):
        """CSI driver bundle with version should strip correctly."""
        result = _extract_bundle_name("csi_driver_powerscale_2.16.0")
        assert result == "csi_driver_powerscale"
