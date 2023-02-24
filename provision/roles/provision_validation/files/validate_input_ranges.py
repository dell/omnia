# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import pexpect
import sys
from netaddr import IPRange

bmc_dynamic_start_range = sys.argv[1]
bmc_dynamic_end_range = sys.argv[2]
bmc_static_start_range = sys.argv[3]
bmc_static_end_range = sys.argv[4]
omnia_exclusive_static_start_range = sys.argv[5]
omnia_exclusive_static_end_range = sys.argv[6]
ranges_overlap = False

try:
    bmc_dynamic_range = IPRange(bmc_dynamic_start_range, bmc_dynamic_end_range)
    bmc_static_range = IPRange(bmc_static_start_range, bmc_static_end_range)
    omnia_exclusive_static_range = IPRange(omnia_exclusive_static_start_range, omnia_exclusive_static_end_range)

    if (bmc_static_range.first <= bmc_dynamic_range.first <= bmc_static_range.last) or (
            bmc_static_range.first <= bmc_dynamic_range.last <= bmc_static_range.last):
        ranges_overlap = True
    if (omnia_exclusive_static_range.first <= bmc_dynamic_range.first <= omnia_exclusive_static_range.last) or (
            omnia_exclusive_static_range.first <= bmc_dynamic_range.last <= omnia_exclusive_static_range.last):
        ranges_overlap = True
    if (bmc_dynamic_range.first <= bmc_static_range.first <= bmc_dynamic_range.last) or (
            bmc_dynamic_range.first <= bmc_static_range.last <= bmc_dynamic_range.last):
        ranges_overlap = True
    if (omnia_exclusive_static_range.first <= bmc_static_range.first <= omnia_exclusive_static_range.last) or (
            omnia_exclusive_static_range.first <= bmc_static_range.last <= omnia_exclusive_static_range.last):
        ranges_overlap = True
    print(ranges_overlap)


except:
    print("lower bound IP greater than upper bound!")
