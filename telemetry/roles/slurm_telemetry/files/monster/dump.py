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
from dateutil import tz
from dateutil.parser import parse as parse_time

log = logger.get_logger(__name__)


def dump_node_jobs(timestamp: object, node_jobs: dict, conn: object):
    """dump_node_jobs Dump Node-Jobs

    Dump node-jobs correlation to TimeScaleDB

    Args:
        timestamp (object): Attached timestamp
        node_jobs (dict): Node-jobs correlation
        conn (object): TimeScaleDB connection object
    """
    try:
        all_records = []
        target_table = 'slurm.node_jobs'
        cols = ('timestamp', 'nodeid', 'jobs', 'cpus')
        for node, job_info in node_jobs.items():
            all_records.append((timestamp, int(node), job_info['jobs'], job_info['cpus']))
        mgr = CopyManager(conn, target_table, cols)
        mgr.copy(all_records)
        conn.commit()
    except Exception as err:
        curs = conn.cursor()
        curs.execute("ROLLBACK")
        conn.commit()
        log.error(f"Fail to dump node-jobs correlation: {err}")


def dump_job_metrics(job_metrics: dict, conn: object):
    """dump_job_metrics Dump Job Metircs

    Dump job metrics to TimeScaleDB

    Args:
        job_metrics (dict): Job Metrics
        conn (object): TimeScaleDB connection object
    """
    try:
        target_table = 'slurm.jobs'
        cols = ('job_id', 'array_job_id', 'array_task_id', 'name','job_state', 
                'user_id', 'user_name', 'group_id', 'cluster', 'partition', 
                'command', 'current_working_directory', 'batch_flag', 
                'batch_host', 'nodes', 'node_count', 'cpus', 'tasks', 
                'tasks_per_node', 'cpus_per_task', 'memory_per_node', 
                'memory_per_cpu', 'priority', 'time_limit', 'deadline', 
                'submit_time', 'preempt_time', 'suspend_time', 'eligible_time', 
                'start_time', 'end_time', 'resize_time', 'restart_cnt', 
                'exit_code', 'derived_exit_code')

        cur = conn.cursor()
        all_records = []

        for job in job_metrics:
            job_id = job[cols.index('job_id')]
            check_sql = f"SELECT EXISTS(SELECT 1 FROM slurm.jobs WHERE job_id={job_id})"
            cur.execute(check_sql)
            (job_exists, ) = cur.fetchall()[0]

            if job_exists:
                # Update
                nodes = job[cols.index('nodes')]
                job_state = job[cols.index('job_state')]
                user_name = job[cols.index('user_name')]
                start_time = job[cols.index('start_time')]
                end_time = job[cols.index('end_time')]
                resize_time = job[cols.index('resize_time')]
                restart_cnt = job[cols.index('restart_cnt')]
                exit_code = job[cols.index('exit_code')]
                derived_exit_code = job[cols.index('derived_exit_code')]
                update_sql = """ UPDATE slurm.jobs 
                                 SET nodes = %s, job_state = %s, user_name = %s, start_time = %s, end_time = %s, resize_time = %s, restart_cnt = %s, exit_code = %s, derived_exit_code = %s
                                 WHERE job_id = %s """
                cur.execute(update_sql, (nodes, job_state, user_name, start_time, end_time, resize_time, restart_cnt, exit_code, derived_exit_code, job_id))
            else:
                all_records.append(job)

        mgr = CopyManager(conn, target_table, cols)
        mgr.copy(all_records)
        conn.commit()
    except Exception as err:
        curs = conn.cursor()
        curs.execute("ROLLBACK")
        conn.commit()
        log.error(f"Fail to dump job metrics: {err}")


def dump_node_metrics(timestamp: object, 
                      node_metrics: dict, 
                      conn: object):
    """dump_node_metrics Dump Node Metrics

    Dump node metrics to TimeScaleDB

    Args:
        timestamp (object): attached timestamp
        node_metrics (dict): node metrics
        conn (object): TimeScaleDB connection object
    """
    schema = 'slurm'
    try:
        metric_names = list(list(node_metrics.values())[0].keys())

        for metric_name in metric_names:
            all_records = []
            target_table = f'{schema}.{metric_name}'
            cols = ('timestamp', 'nodeid', 'value')
            for node, node_data in node_metrics.items():
                all_records.append((timestamp, int(node), node_data[metric_name]))
            mgr = CopyManager(conn, target_table, cols)
            mgr.copy(all_records)
            conn.commit()
    except Exception as err:
        curs = conn.cursor()
        curs.execute("ROLLBACK")
        conn.commit()
        log.error(f"Fail to dump node metrics : {err}")