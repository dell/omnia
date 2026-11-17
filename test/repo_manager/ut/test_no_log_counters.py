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

"""Unit tests: no_log must not mask the package counters of a sync result."""

import unittest

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.basic import remove_values
from plugins.modules import process_rpm_config

MASKED = "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"


class NoLogCounterTests(unittest.TestCase):
    """The counters the cadence reads must stay integers."""

    def test_counter_containing_a_numeric_no_log_string_is_masked_by_ansible(self):
        """Documents the Ansible behavior that broke the cadence cycle."""
        result = {"packages_added": 26}
        self.assertEqual(remove_values(result, {"6"})["packages_added"], MASKED)

    def test_short_numeric_values_are_dropped(self):
        """Numeric strings of up to 6 digits are removed from the masked set."""
        values = {"6", "26", "443", "580", "999999"}
        process_rpm_config.drop_numeric_no_log_values(values)
        self.assertEqual(values, set())

    def test_counters_survive_after_the_filter(self):
        """Package counters stay integers once the filter has run."""
        values = {"6", "26", "35", "13", "580"}
        process_rpm_config.drop_numeric_no_log_values(values)
        result = {"packages_added": 26, "packages_removed": 6, "new_version": 13}
        self.assertEqual(remove_values(result, values), result)

    def test_secrets_are_still_masked(self):
        """Tokens, URLs and longer numbers are still masked."""
        values = {"6", "s3cr3t-token", "https://repo/ssl.key", "1234567", "12ab"}
        process_rpm_config.drop_numeric_no_log_values(values)
        self.assertEqual(
            values, {"s3cr3t-token", "https://repo/ssl.key", "1234567", "12ab"}
        )
        masked = remove_values({"note": "token s3cr3t-token", "packages_added": 6}, values)
        self.assertEqual(masked["packages_added"], 6)
        self.assertNotIn("s3cr3t-token", masked["note"])


if __name__ == "__main__":
    unittest.main()
