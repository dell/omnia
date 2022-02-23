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

log = logger.get_logger(__name__)


def build_slurm_table_schemas():
    """build_slurm_table_schemas Build Slurm Table Schemas

    Build slurm table schemas for storing resource usage metrics obtained from 
    slurm

    Returns:
        dict: slurm table schemas
    """
    table_schemas = {}
    add_tables = {
        'memoryusage':{
            'add_columns': ['Value'],
            'add_types': ['REAL']
        },
        'memory_used':{
            'add_columns': ['Value'],
            'add_types': ['INT']
        },
        'cpu_load':{
            'add_columns': ['Value'],
            'add_types': ['INT']
        },
        'state':{
            'add_columns': ['Value'],
            'add_types': ['INT']
        },
        'node_jobs':{
            'add_columns': ['Jobs', 'CPUs'],
            'add_types': ['INTEGER[]', 'INTEGER[]']
        }
    }
    try:
        for table_name, detail in add_tables.items():
            column_names = ['Timestamp', 'NodeID']
            column_types = ['TIMESTAMPTZ NOT NULL', 'INT NOT NULL']
            column_names.extend(detail['add_columns'])
            column_types.extend(detail['add_types'])

            table_schemas.update({
                table_name: {
                    'column_names': column_names,
                    'column_types': column_types
                }
            })
    except Exception as err:
        log.error(f'Cannot build slurm table schemas: {err}')
    return table_schemas