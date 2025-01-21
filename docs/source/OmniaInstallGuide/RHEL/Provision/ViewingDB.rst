Checking node status
----------------------

Via CLI
--------

Run ``nodels all nodelist.status`` for a list of nodes and their statuses. Here's an example of this command output: ::

    omnia-node00001: installing
    omnia-node00002: booted
    omnia-node00003: powering-on
    omnia-node00004: booted

Possible values of node status are ``powering-off``, ``powering-on``, ``bmcready``, ``installing``, ``booting``, ``post-booting``, ``booted``, and ``failed``.

.. caution:: Once xCAT is installed, restart your SSH session to the OIM to ensure that the newly set up environment variables come into effect. This will also allow the above command to work correctly. If the new environment variables still do not come into effect, enable manually using:
    ::
        source /etc/profile.d/xcat.sh

Via Omnia database [omniadb]
-----------------------------

1. To access the omniadb, execute: ::

            psql -U postgres

            \c omniadb


2. To view the schema being used in the cluster: ``\dn``

3. To view the tables in the database: ``\dt``

4. To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo;`` ::

         id | service_tag |     node      |   hostname     |     admin_mac     |   admin_ip   |   bmc_ip   | status | discovery_mechanism | bmc_mode | switch_ip | switch_name | switch_port | cpu | gpu | cpu_count | gpu_count$
        ----+-------------+---------------+----------------+-------------------+--------------+------------+--------+---------------------+----------+-----------+-------------+-------------+-----+-----+-----------+------------
          1 |             | oim           | newoim.new.dev | 00:0a:f7:dc:11:42 | 10.5.255.254 | 0.0.0.0    |        |                     |          |           |             |             |     |     |           |
          2 | xxxxxxx     | node2         | node2.new.dev  | c4:cb:e1:b5:70:44 | 10.5.0.12    | 10.30.0.12 | booted | mapping             |          |           |             |             | amd |     |         1 |         0
          3 | xxxxxxx     | node3         | node3.new.dev  | f4:02:70:b8:bc:2a | 10.5.0.10    | 10.30.0.10 | booted | mapping             |          |           |             |             | amd | amd |         2 |         1
        (3 rows)


Possible values of node status are ``powering-off``, ``powering-on``, ``bmcready``, ``installing``, ``booting``, ``post-booting``, ``booted``, ``failed``, ``ping``, ``noping``, and ``standingby``.

.. note::
    * The ``gpu_count`` in the database is only updated every time a cluster node is PXE booted.
    * Nodes listed as "failed" can be diagnosed using the ``/var/log/xcat/xcat.log`` file on the target node. Correct any underlying issues and `re-provision the node <../../Maintenance/reprovision.html>`_.
    * Information on debugging nodes stuck at ``powering-on``, ``bmcready``, or ``installing`` for longer than expected is available `here. <../../../Troubleshooting/FAQ/Common/Provision.html>`_ Correct any underlying issue on the node and `re-provision the node <../../Maintenance/reprovision.html>`_.
    * A blank node status indicates that no attempt to provision has taken place. Attempt a manual PXE boot on the node to initiate provisioning.
