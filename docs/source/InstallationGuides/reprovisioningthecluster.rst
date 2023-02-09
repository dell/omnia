Re-provisioning the cluster
++++++++++++++++++++++++++++

While re-provisioning the cluster, users can modify the following:

    - The operating system
    - CUDA
    - OFED

Omnia can re-provision the cluster by running the following command: ::

    cd provision
    ansible-playbook provision.yml -i inventory

Where the inventory contains a list of host IPs as shown below:

::

    172.19.0.101
    172.19.0.102

.. note::
    * The host IPs passed in the inventory should be assigned by Omnia.
    * If the nodes were discovered via SNMP or mapping, users will be required to manually reboot target nodes.
