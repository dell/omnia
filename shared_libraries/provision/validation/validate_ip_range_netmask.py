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

def is_static_range_within_netmask(start_ip, end_ip, netmask):
    """
	Check if a static IP range is within a given netmask.

	Parameters:
	- start_ip (str): The starting IP address of the range.
	- end_ip (str): The ending IP address of the range.
	- netmask (int): The netmask to check against.

	Returns:
	- bool: True if the IP range is within the netmask, False otherwise.
	"""

    network = ipaddress.ip_network(f"{start_ip}/{netmask}", strict=False)
    return ipaddress.ip_address(start_ip) in network and ipaddress.ip_address(end_ip) in network



def main():
    """
	Executes the main function.

	This function takes two command-line arguments: `ip_range` and `netmask`.
	It splits the `ip_range` argument by "-" and assigns the resulting values
	to `start_ip` and `end_ip`. It then calls the `is_static_range_within_netmask`
	function with the `start_ip`, `end_ip`, and `netmask` as arguments.
	
	If any exception occurs during the execution of the function, the `result`
	variable is set to False. Finally, the value of `result` is printed.

	Parameters:
	- None

	Returns:
	- None
	"""

    try:
        ip_range = sys.argv[1]
        netmask = sys.argv[2]

        start_ip = ip_range.split("-")[0]
        end_ip = ip_range.split("-")[1]
    
        result = is_static_range_within_netmask(start_ip, end_ip, int(netmask))
    except:
        result = False
    print(result)

if __name__ == "__main__":
    main()
