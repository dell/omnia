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

"""Unit tests for the _generate_human_readable_id function."""
# pylint: disable=wrong-import-position

import unittest
import sys
from pathlib import Path

# Add parent directory to path to import generate_catalog
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from generate_catalog import _generate_human_readable_id


class TestGenerateHumanReadableId(unittest.TestCase):
    """Test cases for _generate_human_readable_id function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.used_ids = set()

    def test_basic_names(self):
        """Test that basic package names remain unchanged."""
        self.assertEqual(
            _generate_human_readable_id("apptainer", "rpm", None, self.used_ids),
            "apptainer"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "device-mapper-multipath", "rpm", None, self.used_ids
            ),
            "device-mapper-multipath"
        )

    def test_version_in_name_exact(self):
        """Test stripping exact version suffix."""
        self.assertEqual(
            _generate_human_readable_id(
                "external-snapshotter-v8.4.0", "git", "v8.4.0", self.used_ids
            ),
            "external-snapshotter"
        )

    def test_version_in_name_v_prefixed(self):
        """Test stripping version with 'v' prefix in name."""
        self.assertEqual(
            _generate_human_readable_id("app-v1.0.0", "rpm", "1.0.0", self.used_ids),
            "app"
        )

    def test_version_in_name_dots_replaced(self):
        """Test stripping version when dots are replaced by hyphens."""
        self.assertEqual(
            _generate_human_readable_id("helm-charts-2-16-0", "git", "2.16.0", self.used_ids),
            "helm-charts"
        )

    def test_pip_module_format(self):
        """Test pip module format with == version separator."""
        self.assertEqual(
            _generate_human_readable_id("PyMySQL==1.1.2", "pip_module", None, self.used_ids),
            "PyMySQL"
        )

    def test_regex_fallback_no_version(self):
        """Test regex version stripping without explicit pkg_version."""
        self.assertEqual(
            _generate_human_readable_id("calico-v3.31.4", "manifest", None, self.used_ids),
            "calico"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "cert-manager-v1-10-0", "tarball", None, self.used_ids
            ),
            "cert-manager"
        )
        self.assertEqual(
            _generate_human_readable_id("helm-v3-20-1-amd64", "tarball", None, self.used_ids),
            "helm-amd64"
        )
        self.assertEqual(
            _generate_human_readable_id("helm-v3-20-1-chart", "tarball", None, self.used_ids),
            "helm-chart"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "helm-v3-20-1-anything-suffixed", "tarball", None, self.used_ids
            ),
            "helm-anything-suffixed"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "metallb-native-v0-15-3", "manifest", None, self.used_ids
            ),
            "metallb-native"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "strimzi-kafka-operator-helm-3-chart-1-0-1", "tarball", None,
                self.used_ids
            ),
            "strimzi-kafka-operator-helm-3-chart"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "victoria-metrics-operator-0-59-3", "tarball", None, self.used_ids
            ),
            "victoria-metrics-operator"
        )
        self.assertEqual(
            _generate_human_readable_id("python3-PyMySQL-1.1.2", "rpm", None,
                                     self.used_ids),
            "python3-PyMySQL"
        )
        self.assertEqual(
            _generate_human_readable_id(
                "nfs-subdir-external-provisioner-4-0-18", "tarball", None,
                self.used_ids
            ),
            "nfs-subdir-external-provisioner"
        )

    def test_docker_image_without_tag_in_name(self):
        """Test docker images where tag is not in the name."""
        self.assertEqual(
            _generate_human_readable_id(
                "docker.io/library/python", "image", "3.12-slim", self.used_ids
            ),
            "docker.io/library/python"
        )

    def test_collision_handling(self):
        """Test collision handling with _1, _2 suffixes."""
        id1 = _generate_human_readable_id("calico", "rpm", None, self.used_ids)
        self.assertEqual(id1, "calico")

        # Second call with the same base name gets _1
        id2 = _generate_human_readable_id("calico-v1.0.0", "tarball", None, self.used_ids)
        self.assertEqual(id2, "calico_1")

        # Third call gets _2
        id3 = _generate_human_readable_id("calico-v2.0.0", "manifest", None, self.used_ids)
        self.assertEqual(id3, "calico_2")

        self.assertIn("calico", self.used_ids)
        self.assertIn("calico_1", self.used_ids)
        self.assertIn("calico_2", self.used_ids)

if __name__ == "__main__":
    unittest.main()
