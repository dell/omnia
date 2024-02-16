Checking node status
----------------------
Via CLI
+++++++

Run ``nodels all nodelist.status`` for a list of nodes and their statuses. ::

    omnia-node00001: installing
    omnia-node00002: booted
    omnia-node00003: powering-on
    omnia-node00004: booted

Possible values of node status are powering-off, powering-on, bmcready, installing, booting, post-booting, booted, failed.

.. caution:: Once xCAT is installed, restart your SSH session to the control plane to ensure that the newly set up environment variables come into effect. This will also allow the above command to work correctly.


Via omniadb
++++++++++++++++++

1. To access the DB, run: ::

            psql -U postgres

            \c omniadb


2. To view the schema being used in the cluster: ``\dn``

3. To view the tables in the database: ``\dt``

4. To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo;`` ::

        id | service_tag |     node      |     hostname      |     admin_mac     | admin_ip  |  bmc_ip   | status | discovery_mechanism | bmc_mode | switch_ip | switch_name | switch_port
        ----+-------------+---------------+-------------------+-------------------+-----------+-----------+--------+---------------------+----------+-----------+-------------+-------------
          1 |             | control_plane | control.omnia.test| 2c:ea:7f:b4:6e:ed | 10.27.0.1 | 10.29.0.1 |        |                     |          |           |             |
          2 | 6T2R6Z2     | node1         | node1.omnia.test  | 4c:d9:8f:76:48:2e | 10.27.0.3 | 10.29.0.3 |        | mapping             |          |           |             |
          3 | C2KP643     | node2         | node2.omnia.test  | 2c:ea:7f:3d:6b:98 | 10.27.0.2 | 10.29.0.2 |        | mapping             |          |           |             |
          4 | 6TDL6Z2     | login         | login.omnia.test  | 20:04:0f:fa:88:d4 | 10.27.0.4 |           |        | mapping             |          |           |             |
        (4 rows)


Possible values of node status are powering-off, powering-on, bmcready, installing, booting, post-booting, booted, failed.

.. note::
    * Nodes are listed as failed when the IB NIC or OFED did not get configured. They are still reachable via the admin IP. Correct any underlying connectivity issue on the IB NIC and `re-provision the node <../reprovisioningthecluster.html>`_.
    * Information on debugging nodes stuck at 'powering-on', 'bmcready' or 'installing' for longer than expected is available `here. <../../Troubleshooting/FAQ.html>`_ Correct any underlying issue on the node and `re-provision the node <../reprovisioningthecluster.html>`_.
    * A blank node status indicates that no attempt to provision has taken place. Attempt a manual PXE boot on the node to initiate provisioning.
