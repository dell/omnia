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
import pandas
from psycopg2.extensions import AsIs

dbuser = sys.argv[1]
dbpwd = sys.argv[2]
dbhost = sys.argv[3]
dbport = sys.argv[4]
dbtelemetry = sys.argv[5]
column_name = sys.argv[6]
column_value = sys.argv[7]
start_time = sys.argv[8]
stop_time = sys.argv[9]
filename= sys.argv[10]

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

def get_data_by_timerange_and_column(conn):
    try:
        # Query the database to retrieve the data based on the time range, column name, and column value
        sql_query_case1 = '''
                          SELECT * FROM omnia_telemetry.metrics
                          WHERE time BETWEEN %s AND %s AND %s = %s
                          '''
        sql_query_case2 = '''
                          SELECT * FROM omnia_telemetry.metrics WHERE %s = %s
                          '''
        sql_query_case3 = '''
                          SELECT * FROM omnia_telemetry.metrics
                          WHERE time BETWEEN %s AND %s
                          '''
        sql_query_case4 = '''
                          SELECT * FROM omnia_telemetry.metrics
                          '''
        if column_name == 'None' and column_value == 'None' and start_time == 'None' and stop_time == 'None':
            dataframe = pandas.read_sql(sql_query_case4, conn)
        elif column_name == 'None' and column_value == 'None' and start_time != 'None' and stop_time != 'None':
            dataframe = pandas.read_sql(sql_query_case3, conn, params=(start_time, stop_time))
        elif column_name != 'None' and column_value != 'None' and start_time == 'None' and stop_time == 'None':
            dataframe = pandas.read_sql(sql_query_case2, conn, params=(AsIs(column_name), column_value))
        else:
            print(start_time + stop_time)
            dataframe = pandas.read_sql(sql_query_case1, conn, params= (start_time, stop_time, AsIs(column_name), column_value))
        return dataframe
    except Exception as ex:
        sys.exit('Failed to fetch data from timescaledb.'+ str(ex))

def main():
    '''
    This module initiates db connection and creates table
    '''
    db_conn = db_connect()
    if db_conn is not None:
        dataframe = get_data_by_timerange_and_column(db_conn)
        dataframe.to_csv(filename)
        db_conn.close()

if __name__ == '__main__':
    main()