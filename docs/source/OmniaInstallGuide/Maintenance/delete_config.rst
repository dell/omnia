Remove Slurm/Kubernetes configuration from a node
====================================================

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

The inventory file passed for ``remove_node_configuration.yml`` should follow the below format. ::

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









