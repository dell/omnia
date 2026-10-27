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

"""Orchestrator-suite messages exposed to test modules."""

from .cleanup_msgs import (
    TEST_ASSERT_MSGS as CLEANUP_TEST_ASSERT_MSGS,
)
from .cleanup_msgs import (
    TEST_LOG_MSGS as CLEANUP_TEST_LOG_MSGS,
)
from .precheck_msgs import (
    TEST_ASSERT_MSGS as PRECHECK_TEST_ASSERT_MSGS,
)
from .precheck_msgs import (
    TEST_LOG_MSGS as PRECHECK_TEST_LOG_MSGS,
)
from .prepare_msgs import (
    TEST_ASSERT_MSGS as PREPARE_TEST_ASSERT_MSGS,
)
from .prepare_msgs import (
    TEST_LOG_MSGS as PREPARE_TEST_LOG_MSGS,
)
from .provision_msgs import (
    TEST_ASSERT_MSGS as PROVISION_TEST_ASSERT_MSGS,
)
from .provision_msgs import (
    TEST_LOG_MSGS as PROVISION_TEST_LOG_MSGS,
)
from .pxeboot_msgs import (
    TEST_ASSERT_MSGS as PXEBOOT_TEST_ASSERT_MSGS,
)
from .pxeboot_msgs import (
    TEST_LOG_MSGS as PXEBOOT_TEST_LOG_MSGS,
)

__all__ = [
    "CLEANUP_TEST_ASSERT_MSGS",
    "CLEANUP_TEST_LOG_MSGS",
    "PRECHECK_TEST_ASSERT_MSGS",
    "PRECHECK_TEST_LOG_MSGS",
    "PREPARE_TEST_ASSERT_MSGS",
    "PREPARE_TEST_LOG_MSGS",
    "PROVISION_TEST_ASSERT_MSGS",
    "PROVISION_TEST_LOG_MSGS",
    "PXEBOOT_TEST_ASSERT_MSGS",
    "PXEBOOT_TEST_LOG_MSGS",
]
