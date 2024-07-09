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

import ipaddress
import sys

def validate_cidr(cidr):
    """
    Validates if a given CIDR is a valid IPv4 network.

    :param cidr: A string representing a CIDR.
    :type cidr: str
    :return: Returns True if the CIDR is valid, False otherwise.
    :rtype: bool
    """
    try:
        ipaddress.IPv4Network(cidr)
        return True
    except ValueError:
        return False

def main():
    """
    A function that takes a CIDR as an argument and prints the result of validating the CIDR.

    Parameters:
        None

    Returns:
        None
    """

    cidr = sys.argv[1]
    print(validate_cidr(cidr))


if __name__ == "__main__":
    main()
