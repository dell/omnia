Checking node status
----------------------

1. To access the DB, run: ::

            psql -U postgres

            \c omniadb


2. To view the schema being used in the cluster: ``\dn``

3. To view the tables in the database: ``\dt``

4. To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo;`` ::

        id  | serial  |        node        |            hostname            |     admin_mac     |   admin_ip   |    bmc_ip    |    ib_ip     |   status   | bmc_mode |   switch_ip   | switch_name | switch_port
        ----+---------+--------------------+--------------------------------+-------------------+--------------+--------------+--------------+------------+----------+---------------+-------------+-------------
          1 | XXXXXXX | control_plane      |   control_plane.omnia.test     | ec:2a:72:34:f7:26 |  10.5.255.254| 10.19.255.254|              |            |          |               |             |
          2 | XXXXXXX | omnia-node00002    | omnia-node00002.omnia.test     |                   |  10.5.0.102  | 10.19.0.102  | 10.10.0.102  | booted     |          | 10.96.28.132  | switch1     | 3
          3 | XXXXXXX | omnia-node00003    | omnia-node00003.omnia.test     |                   |  10.5.0.103  | 10.19.0.103  | 10.10.0.103  |            |          | 10.96.28.132  | switch1     | 4
          4 | XXXXXXX | omnia-node00004    | omnia-node00004.omnia.test     | 2c:ea:7f:3d:6b:98 |  10.5.0.104  | 10.19.0.104  | 10.10.0.104  | installing |          | 10.96.28.132  | switch1     | 5
          5 | XXXXXXX | omnia-node00005    | omnia-node00005.omnia.test     |                   |  10.5.0.105  | 10.19.0.105  | 10.10.0.105  |            |          | 10.96.28.132  | switch1     | 6
          6 | XXXXXXX | omnia-node00006    | omnia-node00006.omnia.test     |                   |  10.5.0.106  | 10.19.0.106  | 10.10.0.106  |            |          | 10.96.28.132  | switch1     | 7
          7 | XXXXXXX | omnia-node00007    | omnia-node00007.omnia.test     | 4c:d9:8f:76:48:2e |  10.5.0.107  | 10.19.0.107  | 10.10.0.107  | booted     |          | 10.96.28.132  | switch1     | 8
          8 | XXXXXXX | omnia-node00008    | omnia-node00008.omnia.test     |                   |  10.5.0.108  | 10.19.0.108  | 10.10.0.108  |            |          | 10.96.28.132  | switch1     | 1
          9 | XXXXXXX | omnia-node00009    | omnia-node00009.omnia.test     |                   |  10.5.0.109  | 10.19.0.109  | 10.10.0.109  | failed     |          | 10.96.28.132  | switch1     | 10
        10  | XXXXXXX | omnia-node00010    | omnia-node00010.omnia.test     |                   |  10.5.0.110  | 10.19.0.110  | 10.10.0.110  |            |          | 10.96.28.132  | switch1     | 12
        11  | XXXXXXX | omnia-node00011    | omnia-node00011.omnia.test     |                   |  10.5.0.111  | 10.19.0.111  | 10.10.0.111  | failed     |          | 10.96.28.132  | switch1     | 13
        12  | XXXXXXX | omnia-node00012    | omnia-node00012.omnia.test     |                   |  10.5.0.112  | 10.19.0.112  | 10.10.0.112  |            |          | 10.96.28.132  | switch1     | 14

Possible values of status are static, powering-on, installing, bmcready, booting, post-booting, booted, failed. The status will be updated every 3 minutes.

.. note:: For nodes listing status as 'failed', provisioning logs can be viewed in ``/var/log/xcat/cluster.log`` on the target nodes.

