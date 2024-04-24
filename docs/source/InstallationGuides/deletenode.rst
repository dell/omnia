Remove Slurm/K8s configuration from a node
-------------------------------------------

Use this playbook to remove slurm and kubernetes configuration from slurm or kubernetes worker nodes  of the cluster and stop all clustering software on the worker nodes.

.. note::
    * All target nodes should be drained before executing the playbook. If a job is running on any target nodes, the playbook may timeout waiting for the node state to change.
    * When running ``remove_node_configuration.yml``, ensure that the ``input/storage_config.yml`` and ``input/omnia_config.yml`` have not been edited since ``omnia.yml`` was run.


**Configurations performed by the playbook**

    * Nodes specified in the slurm_node group or kube_node group in the inventory file will be removed from the slurm and kubernetes cluster respectively.
    * Slurm and Kubernetes services are stopped and uninstalled. OS startup service list will be updated to disable Slurm and Kubernetes.

**To run the playbook**

Run the playbook using the following commands: ::

        cd utils
        ansible-playbook remove_node_configuration.yml -i inventory

* To specify only Slurm or Kubernetes nodes while running the playbook, use the tags ``slurm_node`` or ``kube_node``. That is:
* To remove only slurm nodes, use ``ansible-playbook remove_node_configuration.yml -i inventory --tags slurm_node``.
* To remove only kubernetes nodes, use ``ansible-playbook remove_node_configuration.yml -i inventory --tags kube_node``.
* To skip confirmation while running the playbook, use ``ansible-playbook remove_node_configuration.yml -i inventory --extra-vars skip_confirmation=yes`` or ``ansible-playbook remove_node_configuration.yml -i inventory -e  skip_confirmation=yes``.

The inventory file passed for ``remove_node_configuration`` should follow the below format. ::

            #Batch Scheduler: Slurm

            [slurm_control_node]

            10.5.1.101

            [slurm_node]

            10.5.1.103

            10.5.1.104

            [login]

            10.5.1.105



            #General Cluster Storage

            [auth_server]

            10.5.1.106

            #AI Scheduler: Kubernetes

            [kube_control_plane]

            10.5.1.101

            [etcd]

            10.5.1.101

            [kube_node]

            10.5.1.102

            10.5.1.103

            10.5.1.104

            10.5.1.105

            10.5.1.106


Soft reset the cluster
-----------------------
Use this playbook to stop all Slurm and Kubernetes services. This action will destroy the cluster.

.. note::
    * All target nodes should be drained before executing the playbook. If a job is running on any target nodes, the playbook may timeout waiting for the node state to change.
    * When running ``reset_cluster_configuration.yml``, ensure that the ``input/storage_config.yml`` and ``input/omnia_config.yml`` have not been edited since ``omnia.yml`` was run.

**Configurations performed by the playbook**

    * The configuration on the kube_control_plane or the slurm_control_plane will be reset.
    * Slurm and Kubernetes services are stopped and removed.

**To run the playbook**

Run the playbook using the following commands: ::

        cd utils
        ansible-playbook reset_cluster_configuration.yml -i inventory

To specify only Slurm or Kubernetes clusters while running the playbook, use the tags ``slurm_cluster`` or ``k8s_cluster``. That is:

To reset a slurm cluster, use ``ansible-playbook reset_cluster_configuration.yml -i inventory --tags slurm_cluster``.
To reset a kubernetes cluster, use ``ansible-playbook reset_cluster_configuration.yml -i inventory --tags k8s_cluster``.

.. warning:: If you do not specify the tags ``slurm_cluster`` or ``k8s_cluster``, the ``reset_cluster_configuration.yml`` will reset the configuration for both Slurm and Kubernetes clusters.

To skip confirmation while running the playbook, use ``ansible-playbook reset_cluster_configuration.yml -i inventory --extra-vars skip_confirmation=yes`` or ``ansible-playbook remove_node_configuration.yml -i inventory -e  skip_confirmation=yes``.

The inventory file passed for ``reset_cluster_configuration`` should follow the below format. ::

        #Batch Scheduler: Slurm

        [slurm_control_node]

        10.5.1.101

        [slurm_node]

        10.5.1.103

        10.5.1.104

        [login]

        10.5.1.105



        #General Cluster Storage

        [auth_server]

        10.5.1.106

        #AI Scheduler: Kubernetes

        [kube_control_plane]

        10.5.1.101

        [etcd]

        10.5.1.101

        [kube_node]

        10.5.1.102

        10.5.1.103

        10.5.1.104

        10.5.1.105

        10.5.1.106


Delete provisioned node
------------------------

Use this playbook to remove discovered or provisioned nodes from all inventory files and Omnia database tables. No changes are made to the Slurm or Kubernetes cluster.


**Configurations performed by the playbook**

    * Nodes will be deleted from the Omnia DB and the xCAT node object will be deleted.
    * Telemetry services will be stopped and removed.

**To run the playbook**

Run the playbook using the following commands: ::

        cd utils
        ansible-playbook delete_node.yml -i inventory

To skip confirmation while running the playbook, use ``ansible-playbook delete_node.yml -i inventory --extra-vars skip_confirmation=yes`` or ``ansible-playbook remove_node_configuration.yml -i inventory -e  skip_confirmation=yes``.

The inventory file passed for ``delete_node.yml`` should follow one of the below formats. ::

    [nodes]
    10.5.0.33

.. note::
    * When the node is added or deleted, the autogenerated inventories: ``amd_gpu``, ``nvidia_gpu``, ``amd_cpu``, and ``intel_cpu`` should be updated for the latest changes.
    * Nodes passed in the inventory will be removed from the cluster. To reprovision the node, use the `add node script. <addinganewnode.html>`_






