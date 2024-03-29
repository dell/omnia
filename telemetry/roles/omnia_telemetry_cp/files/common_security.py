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

'''
    This module contains tasks which handle secuity implementaions
'''
from cryptography.fernet import Fernet

def get_config_data(filepath, keypath):
    '''
    This module decrypts the config file and returns file data
    '''
    with open(keypath, 'rb') as passfile:
        key = passfile.read()
    fernet = Fernet(key)

    with open(filepath, 'rb') as datafile:
        encrypted_file_data = datafile.read()

    decrypted_file_data = fernet.decrypt(encrypted_file_data)
    return decrypted_file_data.decode()
