Scheduler
==========

Before you build clusters
--------------------------

* Verify that all inventory files are updated.

* If the target cluster requires more than 10 kubernetes nodes, use a docker enterprise account to avoid docker pull limits.

* Verify that all nodes are assigned a group. Use the inventory as a reference.

  * The manager group should have exactly 1 manager node.

  * The compute group should have at least 1 node.

  * The login_node group is optional. If present, it should have exactly 1 node.

  * Users should also ensure that all repos are available on the target nodes running RHEL.

.. note:: The inventory file accepts both IPs and FQDNs as long as they can be resolved by DNS.


* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``scheduler.yml`` on RHEL target nodes.

* For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.

**Features enabled by omnia.yml**

* Slurm: Once all the required parameters in ``omnia_config.yml`` are filled in, ``omnia.yml`` can be used to set up slurm.

* Login Node (Additionally secure login node)

* Kubernetes: Once all the required parameters in ``omnia_config.yml`` are filled in, ``omnia.yml`` can be used to set up kubernetes.

* BeeGFS bolt on installation

* NFS bolt on support


Input parameters for the cluster
-------------------------------------

These parameters are located in ``input/omnia_config.yml``

.. note::

    The ``input/omnia_config.yml`` file is encrypted on the first run of the provision tool:
        To view the encrypted parameters: ::

            ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key


Building clusters
------------------

1. In the ``input/omnia_config.yml`` file, provide the `required details <schedulerinputparams.html>`_.

.. note::  Without the login node, Slurm jobs can be scheduled only through the manager node.

2. Create an inventory file in the *omnia* folder. Add login node IP address under the manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and Login node IP under the *[login_node]* group,. Check out the `sample inventory for more information <../samplefiles.html>`_.

.. note::
     * RedHat nodes that are not configured by Omnia need to have a valid subscription. To set up a subscription, `click here <https://omnia-doc.readthedocs.io/en/latest/Roles/Utils/rhsm_subscription.html>`_.
     * Omnia creates a log file which is available at: ``/var/log/omnia.log``.
     * If only Slurm is being installed on the cluster, docker credentials are not required.

3. To run ``omnia.yml``: ::

        ansible-playbook omnia.yml -i inventory


.. note::
    * To visualize the cluster (Slurm/Kubernetes) metrics on Grafana (On the control plane)  during the run of ``omnia.yml``, add the parameters ``grafana_username`` and ``grafana_password`` (That is ``ansible-playbook omnia.yml -i inventory -e grafana_username="" -e grafana_password=""``). Alternatively, Grafana is not installed by ``omnia.yml`` if it's not available on the Control Plane.
    * Having the same node in the manager and login_node groups in the inventory is not recommended by Omnia.

**Using Skip Tags**

Using skip tags, the scheduler running on the cluster can be set to Slurm or Kubernetes while running the ``omnia.yml`` playbook. This choice can be made  depending on the expected HPC/AI workloads.

    * Kubernetes: ``ansible-playbook omnia.yml -i inventory --skip-tags "kubernetes"``  (To set Slurm as the scheduler)

    * Slurm: ``ansible-playbook omnia.yml -i inventory --skip-tags "slurm"`` (To set Kubernetes as the scheduler)

.. note::
        * If you want to view or edit the ``omnia_config.yml`` file, run the following command:

                - ``ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key`` -- To view the file.

                - ``ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key`` -- To edit the file.

        * It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to ``omnia_config.yml``.

**Kubernetes Roles**

As part of setting up Kubernetes roles, ``omnia.yml`` handles the following tasks on the manager and compute nodes:

    * Docker is installed.
    * Kubernetes is installed.
    * Helm package manager is installed.
    * All required services are started (Such as kubelet).
    * Different operators are configured via Helm.
    * Prometheus is installed.

**Slurm Roles**

As part of setting up Slurm roles, ``omnia.yml`` handles the following tasks on the manager and compute nodes:

    * Slurm is installed.
    * All required services are started (Such as slurmd, slurmctld, slurmdbd).
    * Prometheus is installed to visualize slurm metrics.
    * Lua and Lmod are installed as slurm modules.
    * Slurm restd is set up.

**Login node**

If a login node is available and mentioned in the inventory file, the following tasks are executed:

    * Slurmd is installed.
    * All required configurations are made to ``slurm.conf`` file to enable a slurm login node.

.. include:: ../../Appendices/hostnamereqs.rst

.. note::

    * To enable the login node, ensure that ``login_node_required`` in ``input/omnia_config.yml`` is set to true.

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd scheduler
    ansible-playbook job_based_user_access.yml -i inventory


.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.



**Running Slurm MPI jobs on clusters**

To enhance the productivity of the cluster, Slurm allows users to run jobs in a parallel-computing architecture. This is used to efficiently utilize all available computing resources.

.. note::

    * Omnia does not install MPI packages by default. Users hoping to leverage the Slurm-based MPI execution feature are required to install the relevant packages from a source of their choosing.

    * Running jobs as individual users (and not as root) requires that passwordSSH be enabled between compute nodes for the user.

**For Intel**


To run an MPI job on an intel processor, set the following environmental variables on the head nodes or within the job script:

    - ``I_MPI_PMI_LIBRARY`` = ``/usr/lib64/pmix/``
    - ``FI_PROVIDER`` = ``sockets`` (When InfiniBand network is not available, this variable needs to be set)
    - ``LD_LIBRARY_PATH`` (Use this variable to point to the location of the Intel/Python library folder. For example: ``$LD_LIBRARY_PATH:/mnt/jobs/intelpython/python3.9/envs/2022.2.1/lib/``)

**For AMD**

To run an MPI job on an AMD processor, set the following environmental variables on the head nodes or within the job script:

    - ``PATH`` (Use this variable to point to the location of the OpenMPI binary folder. For example: ``PATH=$PATH:/appshare/openmpi/bin``)
    - ``LD_LIBRARY_PATH`` (Use this variable to point to the location of the OpenMPI library folder. For example: ``$LD_LIBRARY_PATH:/appshare/openmpi/lib``)
    - ``OMPI_ALLOW_RUN_AS_ROOT`` = ``1`` (To run jobs as a root user, set this variable to ``1``)
    - ``OMPI_ALLOW_RUN_AS_ROOT_CONFIRM`` = ``1`` (To run jobs as a root user, set this variable to ``1``)












