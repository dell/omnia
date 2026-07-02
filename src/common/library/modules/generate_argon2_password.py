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

#!/usr/bin/python

"""
Ansible custom module to generate Argon2 password hash.
This module uses the argon2-cffi library to generate secure Argon2 password hashes.
"""

import sys
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import HashingError
except ImportError:
    print(
        "ERROR: argon2-cffi package is not installed. "
        "Please install it with: pip install argon2-cffi"
    )
    sys.exit(1)

from ansible.module_utils.basic import AnsibleModule

def generate_argon2_hash(password):
    """
    Generate an Argon2 password hash from a given password.

    Parameters:
        password (str): The password to be converted into Argon2 format.

    Returns:
        str: The Argon2 password hash.
    """
    ph = PasswordHasher()
    try:
        hash_result = ph.hash(password)
        return hash_result
    except HashingError as e:
        raise RuntimeError(f"Failed to generate Argon2 hash: {str(e)}") from e

def main():
    """
    This function is the main entry point of the Ansible module.
    It takes in a password as a parameter and generates an Argon2 password hash from it.
    The password is required and must be a string.
    The function returns the Argon2 password hash as a string.
    """
    module_args = {"password": {"type": "str", "required": True, "no_log": True}}
    module = AnsibleModule(
        argument_spec=module_args, supports_check_mode=True
    )

    try:
        password = module.params["password"]
        if not password:
            module.fail_json(msg="Password cannot be empty")

        argon2_hash = generate_argon2_hash(password)
        module.exit_json(changed=True, pswd_argon2=argon2_hash)

    except RuntimeError as e:
        module.fail_json(msg=str(e).replace("\n", " "))


if __name__ == "__main__":
    main()
