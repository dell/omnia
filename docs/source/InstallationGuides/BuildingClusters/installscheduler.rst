Building clusters
------------------

1. In the ``input/omnia_config.yml`` file, provide the `required details <schedulerinputparams.html>`_.

.. note::
    * Use the parameter ``scheduler_type`` in ``input/omnia_config.yml`` to customize what schedulers are installed in the cluster.
    * Without the login node, Slurm jobs can be scheduled only through the manager node.

2. Create an inventory file in the *omnia* folder. Add login node IP address under the manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and Login node IP under the *[login]* group,. Check out the `sample inventory for more information <../samplefiles.html>`_.

.. note::
     * RedHat nodes that are not configured by Omnia need to have a valid subscription. To set up a subscription, `click here <https://omnia-doc.readthedocs.io/en/latest/Roles/Utils/rhsm_subscription.html>`_.
     * Omnia creates a log file which is available at: ``/var/log/omnia.log``.
     * If only Slurm is being installed on the cluster, docker credentials are not required.

3. To run ``omnia.yml``: ::

        ansible-playbook omnia.yml -i inventory


.. note::
    * To visualize the cluster (Slurm/Kubernetes) metrics on Grafana (On the control plane)  during the run of ``omnia.yml``, add the parameters ``grafana_username`` and ``grafana_password`` (That is ``ansible-playbook omnia.yml -i inventory -e grafana_username="" -e grafana_password=""``). Alternatively, Grafana is not installed by ``omnia.yml`` if it's not available on the Control Plane.
    * Having the same node in the manager and login groups in the inventory is not recommended by Omnia.
    * If you want to view or edit the ``omnia_config.yml`` file, run the following command:

                - ``ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key`` -- To view the file.

                - ``ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key`` -- To edit the file.

        * It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to ``omnia_config.yml``.

**Setting up a shared home directory**

.. image:: ../../images/UserHomeDirectory.jpg

Users wanting to set up a shared home directory for the cluster can do it in one of two ways:
    1. **Using the head node as an NFS host**: Set ``enable_omnia_nfs`` (``input/omnia_config.yml``) to true and provide a share path which will be configured on all nodes in ``omnia_usrhome_share`` (``input/omnia_config.yml``). During the execution of ``omnia.yml``, the NFS share will be set up for access by all compute nodes.
    2. **Using an external filesystem**: Configure the external file storage using ``storage.yml``. Set ``enable_omnia_nfs`` (``input/omnia_config.yml``) to false and provide the external share path in ``omnia_usrhome_share`` (``input/omnia_config.yml``). Run ``omnia.yml`` to configure access to the external share for deployments.


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

    * To enable the login node, ensure that the ``login`` group in the inventory has the intended IP populated.

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

    * Omnia does not install MPI packages by default. Users hoping to leverage the Slurm-based MPI execution feature are required to install the relevant packages from a source of their choosing. For information on setting up Intel OneAPI on the cluster, `click here <../OneAPI.html>`_.
    * Ensure there is an NFS node on which to host slurm scripts to run.
    * Running jobs as individual users (and not as root) requires that passwordSSH be enabled between compute nodes for the user.

**For Intel**

To run an MPI job on an intel processor, set the following environmental variables on the head nodes or within the job script:

    - ``I_MPI_PMI_LIBRARY`` = ``/usr/lib64/pmix/``
    - ``FI_PROVIDER`` = ``sockets`` (When InfiniBand network is not available, this variable needs to be set)
    - ``LD_LIBRARY_PATH`` (Use this variable to point to the location of the Intel/Python library folder. For example: ``$LD_LIBRARY_PATH:/mnt/jobs/intelpython/python3.9/envs/2022.2.1/lib/``)

.. note:: For information on setting up Intel OneAPI on the cluster, `click here <../OneAPI.html>`_.

**For AMD**

To run an MPI job on an AMD processor, set the following environmental variables on the head nodes or within the job script:

    - ``PATH`` (Use this variable to point to the location of the OpenMPI binary folder. For example: ``PATH=$PATH:/appshare/openmpi/bin``)
    - ``LD_LIBRARY_PATH`` (Use this variable to point to the location of the OpenMPI library folder. For example: ``$LD_LIBRARY_PATH:/appshare/openmpi/lib``)
    - ``OMPI_ALLOW_RUN_AS_ROOT`` = ``1`` (To run jobs as a root user, set this variable to ``1``)
    - ``OMPI_ALLOW_RUN_AS_ROOT_CONFIRM`` = ``1`` (To run jobs as a root user, set this variable to ``1``)











