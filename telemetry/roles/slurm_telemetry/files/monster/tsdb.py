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

import sql
import utils
import logger
import schema
import psycopg2

log = logger.get_logger(__name__)


def init_tsdb():
    """init_tsdb Initialize TimeScaleDB

    Initialize TimeScaleDB; The database specified in the configuration file
    should be created before run this function.
    """
    connection = utils.init_tsdb_connection()
    
    utils.print_status('Getting', 'nodes' , 'metadata')
    nodes_metadata = utils.get_clusternodes()
    slurm_table_schemas = schema.build_slurm_table_schemas()

    with psycopg2.connect(connection) as conn:
        cur = conn.cursor()

        # Create node metadata table
        utils.print_status('Creating', 'TimeScaleDB' , 'tables')
        metadata_sql = sql.generate_metadata_table_sql(nodes_metadata, 'nodes')
        cur.execute(metadata_sql)
        sql.write_nodes_metadata(conn, nodes_metadata)

        # Create schema for slurm
        slurm_sqls = sql.generate_metric_table_sqls(slurm_table_schemas, 'slurm')
        cur.execute(slurm_sqls['schema_sql'])

        # Create slurm tables
        all_sqls = slurm_sqls['tables_sql']
        for s in all_sqls:
            table_name = s.split(' ')[5]
            cur.execute(s)

            # Create hypertable
            create_hypertable_sql = "SELECT create_hypertable(" + "'" \
                + table_name + "', 'timestamp', if_not_exists => TRUE)"
            print(create_hypertable_sql)
            cur.execute(create_hypertable_sql)
        
        # Create table for jobs info
        slurm_job_sql = sql.generate_slurm_job_table_sql('slurm')
        cur.execute(slurm_job_sql['schema_sql'])
        for s in slurm_job_sql['tables_sql']:
            table_name = s.split(' ')[5]
            cur.execute(s)
        
        conn.commit()
        cur.close()
    utils.print_status('Finish', 'tables' , 'initialization!')

if __name__ == '__main__':
    init_tsdb()
