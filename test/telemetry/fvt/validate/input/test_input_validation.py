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

"""
Telemetry Validate — Input Validation Verification Tests.

Verifies that telemetry_config.yml on the target is valid and parseable.
"""

import pytest

from library.functions import TestLogger

from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
)
from library.functions.telemetry_func import (
    load_telemetry_config_from_target,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_telemetry_config_parseable(host):
    """Verify telemetry_config.yml on target is valid YAML."""
    tl = TestLogger("Verify telemetry config parseable", "TC_VL_002")

    tl.check("Loading telemetry_config.yml from target")
    config = load_telemetry_config_from_target(host)

    valid = len(config) > 0

    if valid:
        source_count = len(config.get("telemetry_sources", {}))
        tl.passed(
            LOG_MSGS["health_ok"].format(
                component="telemetry_config.yml",
            ),
            f"Sources defined: {source_count}",
        )
    else:
        tl.failed(
            LOG_MSGS["health_failed"].format(
                component="telemetry_config.yml",
            ),
            "File is empty or invalid YAML",
        )

    assert valid, (
        "telemetry_config.yml on target is empty or invalid\n"
        "HOW TO FIX:\n"
        "  1. Check the file exists on the OIM server\n"
        "  2. Verify it is valid YAML\n"
    )
