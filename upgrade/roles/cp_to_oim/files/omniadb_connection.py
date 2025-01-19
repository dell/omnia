# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import psycopg2 as pg
from cryptography.fernet import Fernet

key_file_path = '/opt/omnia/.postgres/.postgres_pass.key'
pass_file_path = '/opt/omnia/.postgres/.encrypted_pwd'

with open(key_file_path, 'rb') as passfile:
    key = passfile.read()
fernet = Fernet(key)

with open(pass_file_path, 'rb') as datafile:
    encrypted_file_data = datafile.read()
decrypted_pwd = fernet.decrypt(encrypted_file_data).decode()

def create_connection():
    # Create database connection
    conn = pg.connect(
        database="omniadb",
        user="postgres",
        password=decrypted_pwd,
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    return conn

def create_connection_xcatdb():
    # Create database connection
    conn = pg.connect(
        database="xcatdb",
        user="postgres",
        password=decrypted_pwd,
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    return conn

