# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import sys
import argparse
import psycopg2

def parse_arguments():
    parser = argparse.ArgumentParser(description="Dump data from the database to a CSV file.")
    parser.add_argument("user", type=str, help="Username for the database")
    parser.add_argument("password", type=str, help="Password for the database")
    parser.add_argument("host", type=str, help="Hostname for the database")
    parser.add_argument("port", type=str, help="Port number for the database")
    parser.add_argument("dbname", type=str, help="Name of the database")
    args = parser.parse_args()
    return args

def validate_inputs(value):

    if value.strip():
        return value
    else:
        raise ValueError("Value cannot be empty")

def db_connect():
    """Creates a secure database connection."""
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname
        )
        if conn is not None:
            conn.autocommit = True
    except Exception as ex:
        sys.exit(f"Failed to connect to timescaledb: {ex}")
    return conn

def db_schema(conn):
    '''
    This module is used to create omnia telemetry schema

    Args:
       conn (Connection Object): It accepts connection object as input
    '''
    sql_query = '''CREATE SCHEMA IF NOT EXISTS omnia_telemetry;'''
    cursor = conn.cursor()
    cursor.execute(sql_query)
    cursor.close()

def db_table(conn):
    '''
    This module creates a table for omnia telemetry metrics

    Args:
       conn (Connection Object): It accepts connection object as input
    '''
    sql_query = '''CREATE TABLE IF NOT EXISTS omnia_telemetry.metrics (
                       id       TEXT NOT NULL,
                       context  TEXT NOT NULL,
                       label    TEXT NOT NULL,
                       value    TEXT NOT NULL,
                       unit     TEXT,
                       system   TEXT,
                       hostname TEXT,
                       time     TIMESTAMPTZ NOT NULL
                  );
                  SELECT create_hypertable('omnia_telemetry.metrics', 'time', if_not_exists => TRUE);
                  SELECT add_retention_policy('omnia_telemetry.metrics', INTERVAL '2 months', if_not_exists => TRUE);
                  '''
    cursor = conn.cursor()
    cursor.execute(sql_query)
    cursor.close()

args = parse_arguments()

try:
    user = validate_inputs(args.user)
    password = validate_inputs(args.password)
    host = validate_inputs(args.host)
    port = validate_inputs(args.port)
    dbname = validate_inputs(args.dbname)
except Exception as ex:
    sys.exit(f"Failed to parse arguments: {ex}")

def main():
    '''
    This module initiates db connection and creates table
    '''
    db_conn = db_connect()
    if db_conn is not None:
        db_schema(db_conn)
        db_table(db_conn)
        db_conn.close()

if __name__ == '__main__':
    main()
