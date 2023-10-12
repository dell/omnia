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

import sys
import psycopg2

dbuser = sys.argv[1]
dbpwd = sys.argv[2]
dbhost = sys.argv[3]
dbport = sys.argv[4]
dbtelemetry = sys.argv[5]

def db_connect():
    '''
    This module creates Database Connection
    '''
    conn = None
    connection_string = f"postgres://{dbuser}:{dbpwd}@{dbhost}:{dbport}/{dbtelemetry}".format(
        dbuser = dbuser, dbpwd = dbpwd, dbhost = dbhost, dbport = dbport, dbtelemetry = dbtelemetry)
    try:
        conn = psycopg2.connect(connection_string)
        if conn is not None:
            conn.autocommit = True
    except Exception as ex:
        sys.exit('Failed to connect to timescaledb')
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
