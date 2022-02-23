"""
MIT License
Copyright (c) 2022 Texas Tech University
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is part of MonSter.
Author:
    Jie Li, jie.li@ttu.edu
"""

import utils
import logger
from pgcopy import CopyManager
from datetime import datetime

log = logger.get_logger(__name__)


def generate_metric_table_sqls(table_schemas: dict,
                               schema_name: str):
    """generate_metric_table_sqls General Metric Table Sqls

    Generate sqls for creating metric tables

    Args:
        table_schemas (dict): table schemas
        schema_name (str): schema name

    Returns:
        dict: sql statements
    """
    sql_statements = {}
    try:
        schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
        sql_statements.update({
            'schema_sql': schema_sql
        })
        
        tables_sql = []
        for table, column in table_schemas.items():
            column_names = column['column_names']
            column_types = column['column_types']
            
            column_str = ''
            for i, column in enumerate(column_names):
                column_str += f'{column} {column_types[i]}, '

            table_sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{table} \
                ({column_str}FOREIGN KEY (NodeID) REFERENCES nodes (NodeID));"
            tables_sql.append(table_sql)

        sql_statements.update({
            'tables_sql': tables_sql,
        })

    except Exception as err:
        log.error(f'Cannot Genrerate Metric Table Sqls: {err}')
    
    return sql_statements


def generate_slurm_job_table_sql(schema_name: str):
    """generate_slurm_job_table_sql Generate Slurm Job Table Sql

    Generate sqls for creating the table that stores the jobs info

    Args:
        schema_name (str): schema name

    Returns:
        dict: sql statements
    """
    
    sql_statements = {}
    table = 'jobs'
    try:
        schema_sql = f"CREATE SCHEMA if NOT EXISTS {schema_name}"
        sql_statements.update({
            'schema_sql': schema_sql
        })
        tables_sql = []
        column_names = ['job_id', 'array_job_id', 'array_task_id', 'name', 
                        'job_state', 'user_id', 'user_name', 'group_id', 
                        'cluster', 'partition', 'command', 
                        'current_working_directory', 'batch_flag', 'batch_host',
                        'nodes', 'node_count', 'cpus', 'tasks', 
                        'tasks_per_node', 'cpus_per_task', 'memory_per_node', 
                        'memory_per_cpu', 'priority', 'time_limit', 'deadline', 
                        'submit_time', 'preempt_time', 'suspend_time', 
                        'eligible_time', 'start_time', 'end_time', 
                        'resize_time', 'restart_cnt', 'exit_code', 
                        'derived_exit_code']
        column_types = ['INT PRIMARY KEY', 'INT', 'INT', 'TEXT', 'TEXT', 'INT', 
                        'TEXT', 'INT', 'TEXT', 'TEXT', 'TEXT', 'TEXT', 
                        'BOOLEAN', 'TEXT', 'TEXT[]', 'INT', 'INT', 'INT', 'INT', 
                        'INT', 'INT', 'INT', 'INT', 'INT', 'INT', 'INT', 'INT', 
                        'INT', 'INT', 'INT', 'INT', 'INT', 'INT', 'INT', 'INT']
        column_str = ''
        for i, column in enumerate(column_names):
            column_str += f'{column} {column_types[i]}, '

        table_sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{table} \
            ({column_str[:-2]});"
        tables_sql.append(table_sql)

        sql_statements.update({
            'tables_sql': tables_sql,
        })
    except Exception as err:
        print(err)
        log.error(f'Cannot Genrerate Job Table Sqls: {err}')
    
    return sql_statements


def generate_metric_def_table_sql():
    """generate_metrics_def_table_sql Generate Metrics Definition Table Sql

    Generate a sql for creating the metrics definition table

    Returns:
        str: sql string
    """
    metric_def_table_sql = "CREATE TABLE IF NOT EXISTS metrics_definition \
            (id SERIAL PRIMARY KEY, metric_id TEXT NOT NULL, metric_name TEXT, \
            description TEXT, metric_type TEXT,  metric_data_type TEXT, \
            units TEXT, accuracy REAL, sensing_interval TEXT, \
            discrete_values TEXT[], data_type TEXT, UNIQUE (id));"
    return metric_def_table_sql


def generate_metadata_table_sql(nodes_metadata: list, table_name: str):
    """generate_metadata_table_sql Generate Metadata Table Sql

    Generate a sql for creating the node metadata table

    Args:
        nodes_metadata (list): nodes metadata list
        table_name (str): table name 

    Returns:
        str: sql string
    """
    column_names = list(nodes_metadata[0].keys())
    column_str = ""
    for i, column in enumerate(column_names):
        column_str += column + " TEXT, "
    column_str = column_str[:-2]
    metadata_table_sql = f" CREATE TABLE IF NOT EXISTS {table_name} \
        ( NodeID SERIAL PRIMARY KEY, {column_str}, UNIQUE (NodeID));"
    return metadata_table_sql


def update_nodes_metadata(conn: object, nodes_metadata: list, table_name: str):
    """update_nodes_metadata Update Nodes Metadata

    Update nodes metadata table

    Args:
        conn (object): database connection
        nodes_metadata (list): nodes metadata list
        table_name (str): table name
    """    
    cur = conn.cursor()
    for record in nodes_metadata:
        col_sql = ""
        os_ip_addr = record['Os_Ip_Addr']
        for col, value in record.items():
            if col != 'Os_Ip_Addr' and col != 'servicetag':
                col_value = col.lower() + " = '" + str(value) + "', "
                col_sql += col_value
        col_sql = col_sql[:-2]
        sql =  "UPDATE " + table_name + " SET " + col_sql \
            + " WHERE os_ip_addr = '" + os_ip_addr + "';"
        cur.execute(sql)
    
    conn.commit()
    cur.close()


def insert_nodes_metadata(conn: object, nodes_metadata: list, table_name: str):
    """insert_nodes_metadata Insert Nodes Metadata

    Insert nodes metadata to metadata table

    Args:
        conn (object): database connection
        nodes_metadata (list): nodes metadata list
        table_name (str): table name
    """
    cols = tuple([col.lower() for col in list(nodes_metadata[0].keys())])
    records = []
    for record in nodes_metadata:
        values = [str(value) for value in record.values()]
        records.append(tuple(values))

    mgr = CopyManager(conn, table_name, cols)
    mgr.copy(records)
    conn.commit()


def check_table_exist(conn: object, table_name: str):
    """check_table_exist Check Table Exists

    Check if the specified table exists or not

    Args:
        conn (object): database connection
        table_name (str): table name

    Returns:
        bool: True if exists, false otherwise
    """
    cur = conn.cursor()
    table_exists = False
    sql = "SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = '" + table_name + "');"
    cur.execute(sql)
    (table_exists, ) = cur.fetchall()[0]

    if table_exists:
        data_exists = False
        sql = "SELECT EXISTS (SELECT * from " + table_name + ");"
        cur.execute(sql)
        (data_exists, ) = cur.fetchall()[0]
        return data_exists
    return False


def write_metric_definitions(conn: object, metric_definitions: list):
    """write_metric_definitions Write Metric Definitions

    Write metric definitions to the table

    Args:
        conn (object): database connection
        metric_definitions (list): the metric definitions
    """
    if not check_table_exist(conn, 'metrics_definition'):
        cols = ('metric_id', 'metric_name', 'description', 'metric_type',
                    'metric_data_type', 'units', 'accuracy', 'sensing_interval',
                    'discrete_values', 'data_type')

        metric_definitions_table = [(i['Id'], i['Name'], i['Description'],
        i['MetricType'], i['MetricDataType'], i['Units'], i['Accuracy'], 
        i['SensingInterval'], i['DiscreteValues'], 
        utils.data_type_mapping[i['MetricDataType']])for i in metric_definitions]

        # Sort
        metric_definitions_table = utils.sort_tuple_list(metric_definitions_table)
        
        mgr = CopyManager(conn, 'metrics_definition', cols)
        mgr.copy(metric_definitions_table)
    
    conn.commit()


def write_nodes_metadata(conn: object, nodes_metadata: list):
    """write_nodes_metadata Write Nodes Metadata

    Write nodes metadata to the table

    Args:
        conn (object): database connection
        nodes_metadata (list): nodes metadata list
    """
    if not check_table_exist(conn, 'nodes'):
        insert_nodes_metadata(conn, nodes_metadata, 'nodes') 
    else:
        update_nodes_metadata(conn, nodes_metadata, 'nodes')


def generate_slurm_sql(metric: str, 
                       start: str, 
                       end: str, 
                       interval: str, 
                       aggregate: str):
    """generate_slurm_sql Generate Slurm Sql

    Generate sql for querying slurm metrics

    Args:
        metric (str): metric name
        start (str): start of time range
        end (str): end of time range
        interval (str): aggregation interval
        aggregate (str): aggregation function

    Returns:
        string: sql string
    """
    sql = ""
    if metric == 'node_jobs':
        sql = f"SELECT time_bucket_gapfill('{interval}', timestamp) AS time, \
            nodeid, jsonb_agg(jobs) AS jobs, jsonb_agg(cpus) AS cpus \
            FROM slurm.{metric} \
            WHERE timestamp >= '{start}' \
            AND timestamp <= '{end}' \
            GROUP BY time, nodeid \
            ORDER BY time;"
    else:
        sql = f"SELECT time_bucket_gapfill('{interval}', timestamp) AS time, \
            nodeid, {aggregate}(value) AS value\
            FROM slurm.{metric} \
            WHERE timestamp >= '{start}' \
            AND timestamp <= '{end}' \
            GROUP BY time, nodeid \
            ORDER BY time;"
    return sql


def generate_slurm_jobs_sql(start: str,end: str):
    """generate_slurm_jobs_sql Generate Slurm Jobs Sql

    Generate Sql for querying slurm jobs info

    Args:
        start (str): start time
        end (str): end time

    Returns:
        string: sql string
    """
    utc_from = datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ')
    epoch_from = int((utc_from - datetime(1970, 1, 1)).total_seconds())
    utc_to = datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%fZ')
    epoch_to = int((utc_to - datetime(1970, 1, 1)).total_seconds())

    sql = f"SELECT * FROM slurm.jobs \
            WHERE start_time < {epoch_to} \
            AND end_time > {epoch_from};"
    return sql


def generate_node_jobs_sql(start: str, end: str, interval: str):
    """gene_node_jobs_sql Generate Node-Jobs Sql

    Generate SQL for querying node-jobs correlation

    Args:
        start (str): start time
        end (str): end time
        interval (str): interval for aggragation

    Returns:
        string: sql string
    """
    sql = f"SELECT time_bucket_gapfill('{interval}', timestamp) AS time, \
            nodeid, jsonb_agg(jobs) AS jobs, jsonb_agg(cpus) AS cpus \
            FROM slurm.node_jobs \
            WHERE timestamp >= '{start}' \
            AND timestamp <= '{end}' \
            GROUP BY time, nodeid \
            ORDER BY time;"
    return sql


