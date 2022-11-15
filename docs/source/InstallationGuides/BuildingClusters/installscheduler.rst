Building Clusters
------------------

1. In the ``input/omnia_config.yml`` file, provide the `required details <schedulerinputparams.html>`_.

.. note::  Without the login node, Slurm jobs can be scheduled only through the manager node.

2. Create an inventory file in the *omnia* folder. Add login node IP address under the manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and Login node IP under the *[login_node]* group,. Check out the `sample inventory for more information <../samplefiles.html>`_.

.. note::
     * Omnia checks for `red hat subscription being enabled on RedHat nodes as a pre-requisite <../../Roles/Utils/rhsm_subscription.html>`_. Not having Red Hat subscription enabled on the manager node will cause ``omnia.yml`` to fail. If compute nodes do not have Red Hat subscription enabled, ``omnia.yml`` will skip the node entirely.
     * Omnia creates a log file which is available at: ``/var/log/omnia.log``.
     * If only Slurm is being installed on the cluster, docker credentials are not required.

3. To run ``omnia.yml``: ::

 ansible-playbook omnia.yml -i inventory

.. note:: To visualize the cluster (Slurm/Kubernetes) metrics on Grafana (On the control plane)  during the run of ``omnia.yml``, add the parameters ``grafana_username`` and ``grafana_password`` (That is ``ansible-playbook omnia.yml -i inventory -e grafana_username="" -e grafana_password=""``). Alternatively, Grafana is not installed by ``omnia.yml`` if it's not available on the Control Plane.


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
    * FreeIPA (the default authentication system on the login node) is installed to provide centralized authentication.

.. include:: ../../Appendices/hostnamereqs.rst

.. note::

    * To enable the login node, ensure that ``login_node_required`` in ``input/omnia_config.yml`` is set to true.
    * To enable security features on the login node, ensure that ``enable_secure_login_node`` in ``input/omnia_config.yml`` is set to true.
    * To customize the security features on the login node, fill out the parameters in ``input/omnia_security_config.yml``.

.. warning:: No users/groups will be created by Omnia.

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd scheduler
    ansible-playbook job_based_user_access.yml -i inventory


.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.

**Installing LDAP Client**

Manager and compute nodes will have LDAP client installed and configured if ``ldap_required`` is set to true. The login node does not have LDAP client installed.

.. warning:: No users/groups will be created by Omnia.




