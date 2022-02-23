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

import time
import pytz
import utils
import dump
import slurm
import parse
import logger
import psycopg2
import schedule

from datetime import datetime

log = logger.get_logger(__name__)


def monitor_slurm():
    """monitor_slurm Monitor Slurm

    Monitor Slurm Metrics
    """
    connection = utils.init_tsdb_connection()
    node_id_mapping = utils.get_node_id_mapping(connection)
    os_idrac_hostname_mapping = utils.get_os_idrac_hostname_mapping()    
    slurm_config = utils.get_config('slurm_rest_api')
    
    #Schedule fetch slurm
    schedule.every().minutes.at(":00").do(fetch_slurm, 
                                          slurm_config, 
                                          connection, 
                                          node_id_mapping,
                                          os_idrac_hostname_mapping)

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            schedule.clear()
            break
        

def fetch_slurm(slurm_config: dict, 
                connection: str, 
                node_id_mapping: dict,
                os_idrac_hostname_mapping: dict):
    """fetch_slurm Fetch Slurm Metrics

    Fetch Slurm metrics from the Slurm REST API

    Args:
        slurm_config (dict): slurm configuration
        connection (str): tsdb connection
        node_id_mapping (dict): node-ip mapping
        os_idrac_hostname_mapping (dict): OS-iDRAC hostname mapping
    """
    token = slurm.read_slurm_token(slurm_config)
    timestamp = datetime.now(pytz.utc).replace(microsecond=0)

    # Get nodes data
    nodes_url = slurm.get_slurm_url(slurm_config, 'nodes')
    nodes_data = slurm.call_slurm_api(slurm_config, token, nodes_url)    

    # Get jobs data
    jobs_url = slurm.get_slurm_url(slurm_config, 'jobs')
    jobs_data = slurm.call_slurm_api(slurm_config, token, jobs_url)    

    # Process slurm data
    if nodes_data and jobs_data:
        job_metrics = parse.parse_jobs_metrics(jobs_data, 
                                               os_idrac_hostname_mapping)
        node_metrics = parse.parse_node_metrics(nodes_data, 
                                                node_id_mapping,
                                                os_idrac_hostname_mapping)
        node_jobs = parse.parse_node_jobs(jobs_data,
                                          node_id_mapping,
                                          os_idrac_hostname_mapping)

        # Dump metrics
        with psycopg2.connect(connection) as conn:
            dump.dump_job_metrics(job_metrics, conn)
            dump.dump_node_metrics(timestamp, node_metrics, conn)
            dump.dump_node_jobs(timestamp, node_jobs, conn)


if __name__ == '__main__':
    monitor_slurm()
