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

#!/usr/bin/python

"""
Ansible custom module to append 'ip=<ip>' to each relevant line in the inventory file.
It reads the `src` file, appends `ip=` for matching IPs or ansible_host values,
and writes the result to `dest`.
"""

import hashlib
import base64
import os
import sys
from passlib.hash import ldap_sha1 as lsm

from ansible.module_utils.basic import AnsibleModule

def generate_ssha(password):
    """
    Generate a SSHA password from a given password.

    Parameters:
        password (str): The password to be converted into SSHA format.

    Returns:
        str: The SSHA password.
    """
    salt = os.urandom(4)
    sha = hashlib.sha1(password.encode('utf-8'))
    sha.update(salt)
    return '{SSHA}' + base64.b64encode(sha.digest() + salt).decode('utf-8')

def get_hash(passwd):
    """
    Get the hash of a given password.

    Parameters:
        passwd (str): The password to be hashed.

    Returns:
        str: The hashed password.
    """
    hashed = lsm.hash(passwd)
    return hashed

def main():
    """
    This function is the main entry point of the Ansible module.
    It takes in a password as a parameter and generates an SSHA password from it.
    The password is required and must be a string.
    The function returns the SSHA password as a string.
    """
    module_args = dict(
        password=dict(type="str", required=True)
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    try:
        pswd_plain_txt = module.params["password"]
        #pswd_ssha = generate_ssha(pswd_plain_txt)
        pswd_ssha = get_hash(pswd_plain_txt)
        module.exit_json(changed=True, pswd_ssha=pswd_ssha)
    except Exception as e:
        module.fail_json(msg=str(e).replace('\n', ' '))


if __name__ == "__main__":
    main()

