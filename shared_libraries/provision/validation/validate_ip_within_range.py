

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

def ip_range_check(ip_range, ip):
    """
	Check if an IP address is within a given IP range.

	Parameters:
	- ip_range (str): The IP range in the format "start_ip-end_ip".
	- ip (str): The IP address to check.

	Returns:
	- bool: True if the IP address is within the IP range, False otherwise.
	"""

    start_range = ip_range.split('-')[0].strip().split('.')
    end_range = ip_range.split('-')[1].split('.')
    check_ip = ip.split('.')
    for i in range(4):
        if int(check_ip[i]) < int(start_range[i]) or int(check_ip[i]) > int(end_range[i]):
            return False
    return True

def main():
    """
	Executes the main function of the program.

	This function takes two command line arguments, `ip_range` and `ip`, and performs an IP range check using the `ip_range_check` function. If the IP is within the range, the function returns `True`, otherwise it returns `False`. The result is then printed to the console.

	Parameters:
	- `ip_range` (str): The IP range to check against.
	- `ip` (str): The IP address to check.

	Returns:
	- `bool`: The result of the IP range check, either `True` or `False`.
	"""

    try:
        ip_range = sys.argv[1]
        ip = sys.argv[2]
    
        result = ip_range_check(ip_range, ip)
    except:
        result = False
    print(result)

if __name__ == "__main__":
    main()
