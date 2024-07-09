Kubernetes plugin for RoCE NIC
===================================

.. caution:: Kubernetes plugin for the RoCE NIC is only supported on the Ubuntu clusters (not on RHEL/Rocky Linux clusters).

Few important things to keep in mind before proceeding with the installation:

1. Defined network interfaces with their respective IP ranges (start and end) should be assigned.
2. Number of entries in the ``input/roce_plugin_config.yml`` should be equal to number of RoCE interfaces available in the RoCE pod.
3. VLAN NICs are not supported.
4. This playbook supports the deployment of up to 8 RoCE NIC interfaces.
5. In a scenario where there are two nodes with two separate NICs, the admin must ensure to use aliasing to make the NIC names similar before executing ``deploy_roce_plugin.yml``.
6. Omnia does not validate any parameter entries in the ``input/roce_plugin_config.yml``. It is the user's responsibility to provide correct inputs for the required parameters. In case of any errors encountered due to incorrect entries, delete and re-install the plugin with the correct inputs. For more information, `click here <../../Troubleshooting/FAQ.html>`_.

Install the plugin
-------------------

**Prerequisites**

* Ensure Kubernetes is set up on the cluster with ``flannel`` as the input for the ``k8s_cni`` parameter. For the complete list of parameters, `click here <schedulerinputparams.html#id11>`_.
* Ensure that the ``bcm_roce`` drivers are installed on the nodes.
* Ensure that additional NICs have been configured using the ``server_spec_update.yml`` playbook. For more information on how to configure additional NICs, `click here <../InstallingProvisionTool/AdditionalNIC.html>`_.
* Ensure that the ``{"name": "roce_plugin"}`` entry is present in the ``software_config.json`` and the same config has been used while executing the ``local_repo.yml`` playbook.
* Ensure to update the below mentioned parameters in ``input/roce_plugin_config.yml``:

.. csv-table:: Parameters for RoCE NIC
   :file: ../../Tables/roce_config.csv
   :header-rows: 1
   :keepspace:


Here is an example of the ``input/roce_plugin_config.yml``: ::

          interfaces:
            - name: eth1
              range: 192.168.1.0/24
              range_start:
              range_end:
              gateway: 192.168.1.1
              route: 192.168.1.0/24
            - name: eth2
              range: 192.168.2.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth3
              range: 192.168.3.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth4
              range: 192.168.4.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth5
              range: 192.168.5.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth6
              range: 192.168.6.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth7
              range: 192.168.7.0/24
              range_start:
              range_end:
              gateway:
              route:
            - name: eth8
              range: 192.168.8.0/24
              range_start:
              range_end:
              gateway:
              route:

**To run the playbook**

Run the playbook using the following commands: ::

    cd omnia/scheduler
    ansible-playbook deploy_roce_plugin.yml -i inventory

Where the inventory should be the same as the one used to setup Kubernetes on the cluster.

.. note:: A config file named ``roce_plugin.json`` is located in ``omnia\input\config\ubuntu\22.04\``. This config file contains all the details about the Kubernetes plugin for the RoCE NIC. Here is an example of the config file: ::

       {
         "package": "whereabouts",
         "url": "https://github.com/k8snetworkplumbingwg/whereabouts.git",
         "type": "git",
         "version": "master",
         "commit": "638d58"
       },
       {
         "package": "k8s-rdma-shared-dev-plugin",
         "url": "https://github.com/Mellanox/k8s-rdma-shared-dev-plugin.git",
         "type": "git",
         "version": "master",
         "commit": "c94b2cef"
       },

    * The ``version`` and the ``commit`` attributes mentioned here are set to the default values verified by Omnia. If you want to update these attributes, you may do so at your own responsibility.

Delete the plugin
------------------

**To run the playbook**

Run the playbook using the following commands: ::

    cd omnia/scheduler
    ansible-playbook delete_roce_plugin.yml -i inventory