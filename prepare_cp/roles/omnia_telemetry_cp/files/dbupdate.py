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

import psycopg2
import common_parser
import common_logging
import common_security
import time
import datetime

filepath = "/opt/omnia/telemetry/.timescaledb/config.yml"
keypath = "/opt/omnia/telemetry/.timescaledb/.config_pass.key"

class DatabaseClient:

    def __init__(self):
        self.db_conn = None

    def db_connect(self, dbdata):
        '''
        This module creates Database Connection
        '''

        dbuser = dbdata['username']
        dbpwd = dbdata['password']
        dbhost = dbdata['host']
        dbport = dbdata['port']
        dbtelemetry = dbdata['database']
        dbgssencmode = dbdata['gssencmode']
        #Create connection string for connecting to db
        connection_string = f"postgres://{dbuser}:{dbpwd}@{dbhost}:{dbport}/{dbtelemetry}?gssencmode={dbgssencmode}".format(
            dbuser = dbuser, dbpwd = dbpwd, dbhost = dbhost, dbport = dbport, dbtelemetry = dbtelemetry, dbgssencmode = dbgssencmode)
        try:
            self.db_conn = psycopg2.connect(connection_string)
            if self.db_conn is not None:
                self.db_conn.autocommit = True
        except Exception as ex:
            # Log the error message with the error output
            common_logging.log_error("dbupdate:db_connect",
                                    "Error in connecting to timescaledb" + str(ex))

    def db_close(self):
        '''
        This module closes the database connection object
        '''

        self.db_conn.close()

    def create_db_query(self, combined_result_dict,combined_unit_dict, service_tag, hostname):
        '''
        Database query creation
        :param combined_result_dict: Combined metrics data dictionary
        :param service_tag: System serial number/service tag
        '''
        if service_tag is not None:
            db_query_list=[]
            timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            for metric, metric_dict in combined_result_dict.items():
                if metric_dict:
                    for key,value in metric_dict.items():
                        if value!="":
                            if value in ["No data", "Unknown"]:
                                unit=""
                            else:
                                unit = common_parser.get_unit(key,combined_unit_dict)
                            label = key+" "+metric
                            db_data_tuple = (key,metric,label,value,unit,service_tag,hostname,timestamp)
                            db_query_list.append(db_data_tuple)
            return db_query_list
        else:
            common_logging.log_error("dbupdate:create_db_query","Service Tag is empty.")

    def db_insert(self, db_query):
        '''
        This module inserts data into database
        '''

        try:
            db_cursor = self.db_conn.cursor()
            sql_insert_query = """INSERT INTO omnia_telemetry.metrics \
                            (id, context, label, value, unit, system, hostname, time )\
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
            db_cursor.executemany(sql_insert_query, db_query)
            self.db_conn.commit()
            db_cursor.close()
        except Exception as ex:
            # Log the error message with the error output
            common_logging.log_error("dbupdate:db_insert",
                                    "Error in inserting data to Database" + str(ex))
            self.db_close()

    def update_db(self, combined_result_dict,combined_unit_dict, service_tag, hostname):
        '''
        This module updates the Timescaledb on the control plane with telemetry data

        Args:
        Combined metric dictionary {dict}
        '''

        #Fetch the db connect info from config file
        dbdata = common_parser.parse_yaml_file(common_security.get_config_data(filepath,keypath))

        #Connect to the database
        self.db_connect(dbdata)

        if self.db_conn is not None:
            #Create sql query
            db_query = self.create_db_query(combined_result_dict,combined_unit_dict,service_tag,hostname)

            #Insert into database
            self.db_insert(db_query)

            self.db_close()
