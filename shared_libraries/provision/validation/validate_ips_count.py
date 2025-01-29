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

import ipaddress
import sys

start_ip=sys.argv[1]
end_ip=sys.argv[2]

start_ip = ipaddress.ip_address(start_ip)
end_ip = ipaddress.ip_address(end_ip)
if start_ip and end_ip:
    ip_range = ipaddress.summarize_address_range(start_ip, end_ip)
    count = 0
    for subnet in ip_range:
        count += subnet.num_addresses
    print(count)
