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

def validate_cidr(cidr):
    """
	Validates if the given CIDR is a valid IPv4 network.

	Parameters:
	    cidr (str): The CIDR to validate.

	Returns:
	    bool: True if the CIDR is valid, False otherwise.
	"""

    try:
        ipaddress.IPv4Network(cidr)
        return True
    except ValueError:
        return False

def main():
    """
	The main function that takes a single argument `cidr` from the command line and prints the result of the `validate_cidr` function.

	Parameters:
		None

	Returns:
		None
	"""

    cidr = sys.argv[1]
    print(validate_cidr(cidr))


if __name__ == "__main__":
    main()
