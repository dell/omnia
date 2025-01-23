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
"""
This module performs the task of dumping data from the database to a CSV file.
It securely connects to the database, validates input parameters, fetches valid
column names from the database, and retrieves data based on column names and timestamps.

- We are fetching username, password from telemetry_config.yml
- host as localhost, port - kubectl get svc commands, and dbname - from vars file through ansible
- column_name, column_value, start_time, stop_time - from timescaledb_utility_config.yml
"""

import sys
import ipaddress
import re
import psycopg2
import pandas as pd
from psycopg2.extensions import AsIs
import argparse

# Patterns for validation - 'YYYY-MM-DD HH:MM:SS+TZ'
TIMESTAMP_PATTERN = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\+\d{2}:\d{2})?$'


def parse_arguments():
    parser = argparse.ArgumentParser(description="Dump data from the database to a CSV file.")
    parser.add_argument("user", type=str, help="Username for the database")
    parser.add_argument("password", type=str, help="Password for the database")
    parser.add_argument("host", type=str, help="Hostname for the database")
    parser.add_argument("port", type=str, help="Port number for the database")
    parser.add_argument("dbname", type=str, help="Name of the database")
    parser.add_argument("column_name", type=str, help="Name of the column to update")
    parser.add_argument("column_value", type=str, help="Value to set for the column")
    parser.add_argument("start_time", type=str, help="Start timestamp for the data range")
    parser.add_argument("stop_time", type=str, help="Stop timestamp for the data range")
    parser.add_argument("filename", type=str, help="Name of the output CSV file")
    args = parser.parse_args()
    return args


def validate_inputs(value, obj):
    if value.strip():
        return value
    else:
        raise ValueError(f"{obj} value cannot be empty")

def validate_timestamp(timestamp):
    """Validates the timestamp format or checks for 'None'."""
    if timestamp != "None" and not re.fullmatch(TIMESTAMP_PATTERN, timestamp):
        raise ValueError("Invalid timestamp format. Use 'YYYY-MM-DD HH:MM:SS+TZ' format.")
    return timestamp

def validate_column_value(column_value):
    """
    Validate the column value to prevent SQL injection.
    Allows all characters for flexibility as per PostgreSQL text field constraints.
    """
    if column_value:
        return column_value
    else:
        raise ValueError("Invalid column value")

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

def fetch_valid_columns():
    """Fetches valid column names from the database."""
    query = "SELECT column_name FROM information_schema.columns WHERE table_name='metrics'"
    conn = db_connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception as ex:
        raise ValueError(f"Failed to fetch valid columns from the database: {ex}")

def validate_column_name(column_name, valid_columns):
    """Validates the column name against available columns in the database."""
    if column_name != "None" and column_name not in valid_columns:
        raise ValueError(f"Invalid column name '{column_name}'. Available columns: {', '.join(valid_columns)}")
    return column_name

def get_data_by_timerange_and_column(conn):
    """
    Retrieves data from the database based on the given time range and column name/value.
    """
    query = "SELECT * FROM omnia_telemetry.metrics WHERE true"
    params = []

    if start_time != "None" and stop_time != "None":
        query += " AND time BETWEEN %s AND %s"
        params.extend([start_time, stop_time])

    if column_name != "None" and column_value != "None":
        query += " AND %s = %s"
        params.extend([AsIs(column_name), column_value])

    try:
        return pd.read_sql(query, conn, params=params)
    except Exception as ex:
        sys.exit(f"Failed to fetch data from the database: {ex}")


args = parse_arguments()

try:
    user = validate_inputs(args.user, 'user')
    password = validate_inputs(args.password, 'password')
    host = validate_inputs(args.host, 'host')
    port = validate_inputs(args.port, 'port')
    dbname = validate_inputs(args.dbname, 'dbname')

    column_name = validate_column_name(args.column_name, fetch_valid_columns())
    column_value = validate_column_value(args.column_value)
    start_time = validate_timestamp(args.start_time)
    stop_time = validate_timestamp(args.stop_time)
    filename = args.filename
except Exception as ex:
    sys.exit(f"Failed to parse arguments: {ex}")

def main():
    '''
    This module initiates db connection and creates table
    '''
    db_conn = db_connect()
    if db_conn is not None:
        dataframe = get_data_by_timerange_and_column(db_conn)
        dataframe.to_csv(filename, index=False)
        db_conn.close()

if __name__ == '__main__':
    main()