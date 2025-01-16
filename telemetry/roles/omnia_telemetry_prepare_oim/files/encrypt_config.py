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

#!/usr/bin/env python3

'''
    This module contains tasks required for database update
    The query should be created along with timestamp before updating
    the database.
'''

from cryptography.fernet import Fernet


def encrypt_config_file():
    '''
    This module encrypts the config file
    '''
    with open('/opt/omnia/telemetry/.timescaledb/.config_pass.key', 'rb') as filekey:
        key = filekey.read()
    fernet = Fernet(key)

    with open('/opt/omnia/telemetry/.timescaledb/config.yml', 'rb') as file:
        original = file.read()
    encrypted = fernet.encrypt(original)

    with open('/opt/omnia/telemetry/.timescaledb/config.yml', 'wb') as encrypted_file:
        encrypted_file.write(encrypted)

def main():
    '''
    This module initiates config encryption
    '''
    encrypt_config_file()

if __name__ == '__main__':
    main()
