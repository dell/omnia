# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import sys
from netaddr import IPRange

first_start_range = sys.argv[1]
first_end_range = sys.argv[2]
second_start_range = sys.argv[3]
second_end_range = sys.argv[4]
ranges_overlap = False

try:
    first_ip_range = IPRange(first_start_range, first_end_range)
    second_ip_range = IPRange(second_start_range, second_end_range)

    if (first_ip_range.first <= second_ip_range.first <= first_ip_range.last) or (
            first_ip_range.first <= second_ip_range.last <= first_ip_range.last):
        ranges_overlap = True
    if (second_ip_range.first <= first_ip_range.first <= second_ip_range.last) or (
            second_ip_range.first <= first_ip_range.last <= second_ip_range.last):
        ranges_overlap = True
    print(ranges_overlap)

except:
    print("lower bound IP greater than upper bound!")
