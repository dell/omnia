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

import yaml
import logger
import hostlist
import psycopg2
from pathlib import Path

log = logger.get_logger(__name__)

data_type_mapping = {
    'Decimal': 'REAL',
    'Integer': 'BIGINT',
    'DateTime': 'TIMESTAMPTZ',
    'Enumeration': 'TEXT',
}

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_status(action: str, target: str, obj: str):
    """print_status Print Status

    Print status in a nice way

    Args:
        status (str): status
    """
    print(f'{action} {bcolors.OKBLUE}{target}{bcolors.ENDC} {obj}...')


def parse_config():
    """parse_config Parse Config

    Parse configuration files

    Returns:
        dict: Configuration in json format
    """
    cfg = []
    monster_path = Path(__file__).resolve().parent
    try:
        with open(f'{monster_path}/config.yml', 'r') as ymlfile:
            cfg = yaml.safe_load(ymlfile)
            return cfg
    except Exception as err:
        log.error(f"Parsing Configuration Error: {err}")


def get_config(target: str):
    """get_config Get Config

    Get Configuration for the specified target 

    Args:
        target (str): configuration target

    Raises:
        ValueError: Invalid configuration target

    Returns:
        dict: configurations of specified target
    """
    
    targets = ['timescaledb', 'slurm_rest_api']
    if target not in targets:
        raise ValueError(f"Invalid configuration target. Expected one of: {targets}")

    config = parse_config()[target]
    return config


def init_tsdb_connection():
    """init_tsdb_connection Initialize TimeScaleDB Connection

    Initialize TimeScaleDB Connection according to the configuration
    """
    config_tsdb = parse_config()['timescaledb']

    db_host = config_tsdb['host']
    db_port = config_tsdb['port']
    db_user = config_tsdb['username']
    db_pswd = config_tsdb['password']
    db_dbnm = config_tsdb['database']
    connection = f"postgresql://{db_user}:{db_pswd}@{db_host}:{db_port}/{db_dbnm}"
    return connection


def get_clusternodes():
    """get_clusternodes Get ClusterNodes

    Generate the nodes list in the cluster
    """
    nodes_config = parse_config()['clusternodes']
    return nodes_config


def sort_tuple_list(tuple_list:list):
    """sort_tuple Sort a list of tuple

    Sort tuple. Ref: https://www.geeksforgeeks.org/python-program-to-sort-a-\
    list-of-tuples-by-second-item/

    Args:
        tuple_list (list): a list of tuple
    """
    tuple_list.sort(key = lambda x: x[0])  
    return tuple_list


def get_os_idrac_hostname_mapping():
    """get_os_idrac_hostname_mapping Get OS iDRAC hostname mapping

    Read configuration file and get OS idrac hostname mapping if configured
    """
    hostnames_mapping = parse_config()['hostnames']
    return hostnames_mapping


def get_node_id_mapping(connection: str):
    """get_node_id_mapping Get Node-Id Mapping

    Get node-id mapping from the nodes metadata table

    Args:
        connection (str): timescaledb connection

    Returns:
        dict: node-id mapping
    """
    
    mapping = {}
    try:
        with psycopg2.connect(connection) as conn:
            cur = conn.cursor()
            query = "SELECT nodeid, os_ip_addr from nodes"
            cur.execute(query)
            for (nodeid, os_ip_addr) in cur.fetchall():
                mapping.update({
                    os_ip_addr: nodeid
                })
            cur.close()
            return mapping
    except Exception as err:
        log.error(f"Cannot generate node-id mapping: {err}")


def get_ip_id_mapping(conn: object):
    """get_ip_id_mapping Get IP-ID mapping

    Get iDRAC-ip address - node-id mapping

    Args:
        conn (object): TimeScaleDB connection object

    Returns:
        dict: ip-id mapping
    """
    mapping = {}
    cur = conn.cursor()
    query = "SELECT nodeid, os_ip_addr FROM nodes"
    cur.execute(query)
    for (nodeid, os_ip_addr) in cur.fetchall():
        mapping.update({
            os_ip_addr: nodeid
        })
    cur.close()
    return mapping


def cast_value_type(value, dtype):
    """cast_value_type Cast Value Data Type

    Cast value data type based on the datatype in TimeScaleDB

    Args:
        value ([type]): value to be casted
        dtype ([type]): TimeScaleDB data type

    Returns:
        object: casted datatype
    """
    try:
        if dtype =="BIGINT":
            return int(value)
        elif dtype == "REAL":
            return float(value)
        else:
            return value
    except ValueError:
        return value
