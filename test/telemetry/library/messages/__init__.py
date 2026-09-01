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
Telemetry — Messages

Centralized log and assertion messages for telemetry FVT.
"""

from .telemetry_msgs import (
    TEST_LOG_MSGS,
    TEST_ASSERT_MSGS,
)

from .ome_msgs import (
    OME_TEST_NAMES,
    OME_LOG_MSGS,
    OME_ASSERT_MSGS,
)

from .sfm_msgs import (
    SFM_LOG_MSGS,
    SFM_ASSERT_MSGS,
    SFM_ERROR_MSGS,
    SFM_DETAIL_MSGS,
)
from .ufm_msgs import (
    UFM_LOG_MSGS,
    UFM_ASSERT_MSGS,
    UFM_ERROR_MSGS,
    UFM_DETAIL_MSGS,
)

__all__ = [
    "TEST_LOG_MSGS",
    "TEST_ASSERT_MSGS",
    "OME_TEST_NAMES",
    "OME_LOG_MSGS",
    "OME_ASSERT_MSGS",
    "SFM_LOG_MSGS",
    "SFM_ASSERT_MSGS",
    "SFM_ERROR_MSGS",
    "SFM_DETAIL_MSGS",
    "UFM_LOG_MSGS",
    "UFM_ASSERT_MSGS",
    "UFM_ERROR_MSGS",
    "UFM_DETAIL_MSGS",
]
