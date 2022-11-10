Scheduler
==========

**Input parameters**


These parameters is located in ``input/omnia_config.yml``


+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter Name             | Default Value                      | Additional Information                                                                                                                                                                                                                  |
+============================+====================================+=========================================================================================================================================================================================================================================+
| mariadb_password           | password                           | Password   used to access the Slurm database.Required Length: 8 charactersThe password   must not contain -,, ‘,”                                                                                                                       |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_version                | 1.19.3                             | Kubernetes VersionAccepted Values:   “1.16.7” or “1.19.3”                                                                                                                                                                               |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_cni                    | calico                             | CNI   type used by Kubernetes.Accepted values: calico, flannel                                                                                                                                                                          |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| k8s_pod_network_cidr       | 10.244.0.0/16                      | Kubernetes pod network CIDR                                                                                                                                                                                                             |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| docker_username            |                                    | Username   to login to Docker. A kubernetes secret will be created and patched to the   service account in default namespace.This value is optional but suggested to   avoid docker pull limit issues                                   |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| docker_password            |                                    | Password to login to DockerThis value is   mandatory if a docker_username is provided                                                                                                                                                   |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ansible_config_file_path   | /etc/ansible                       | Path   where the ansible.cfg file can be found.If dnf is used, the default value is   valid. If pip is used, the variable must be set manually                                                                                          |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| login_node_required        | true                               | Boolean indicating whether the login   node is required or not                                                                                                                                                                          |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_required              | false                              | Boolean   indicating whether ldap client is required on the manager node and compute   nodes or not. If ldap_required is set to True, then FreeIPA will not be   installed.                                                             |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_server_ip             |                                    | This field accepts Valid LDAP Server IP.   This parameter is required when ldap_required is set to True.                                                                                                                                |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_connection_type       | **TLS**, SSL                       | Sets   the connection protocol.  If TLS is   given, make sure valid server certificate path is provided. If SSL is   provided, then the secure ldap connection is establsihed via port 636.                                             |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_ca_cert_path          |  /etc/openldap/certs/omnialdap.pem | This variable accepts Server Certificate   Path                                                                                                                                                                                         |
|                            |                                    |      Make sure certificate is present in the path provided                                                                                                                                                                              |
|                            |                                    |      The certificate should have .pem or .crt extension.                                                                                                                                                                                |
|                            |                                    |      This variable is mandatory if connection type is TLS                                                                                                                                                                               |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user_home_dir              | /home                              | This   variable accepts th user home directory path                                                                                                                                                                                     |
|                            |                                    |      If nfs mount is created for user home, make sure you provide the                                                                                                                                                                   |
|                            |                                    |      User mount home directory path                                                                                                                                                                                                     |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_username         | admin                              | The bind dn used to access the LDAP   server. If this parameter is not provided, LDAP authentication will fail                                                                                                                          |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_password         |                                    | The   bind dn password used to access the LDAP server. If this parameter is not   provided, LDAP authentication will fail                                                                                                               |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name                | omnia.test                         | Sets the intended domain name                                                                                                                                                                                                           |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| freeipa_required           | TRUE                               | When   true, FreeIPA will be installed on all the nodes                                                                                                                                                                                 |
|                            |                                    |      If freeipa_required is set to false, then FreeIPA will not be installed                                                                                                                                                            |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| realm_name                 | OMNIA.TEST                         | Sets the intended realm name                                                                                                                                                                                                            |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| directory_manager_password |                                    | Password   authenticating admin level access to the Directory for system management   tasks. It will be added to the instance of directory server created for   IPA.Required Length: 8 characters.The password must not contain -,, ‘,” |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| kerberos_admin_password    |                                    | “admin” user password for the IPA server   on RockyOS. If LeapOS is in use, it is used as the “kerberos admin” user   password for 389-dsThis field is not relevant to Control Planes running   LeapOS                                  |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| enable_secure_login_node   | false                              | Boolean   value deciding whether FreeIPA is    enabled on the Login Node.                                                                                                                                                               |
+----------------------------+------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
.. note:: When ``ldap_required`` is true, ``login_node_required`` and ``freeipa_required`` have to be false.


**Pre Requisites before you run Scheduler**


* Verify that all inventory files are updated.

* If the target cluster requires more than 10 kubernetes nodes, use a docker enterprise account to avoid docker pull limits.

* Verify that all nodes are assigned a group. Use the `inventory <../../samplefiles.html>`_ as a reference.

  * The manager group should have exactly 1 manager node.

  * The compute group should have at least 1 node.

  * The login_node group is optional. If present, it should have exactly 1 node.

  * Users should also ensure that all repos are available on the target nodes running RHEL.

.. note:: The inventory file accepts both IPs and FQDNs as long as they can be resolved by DNS.

* For RedHat clusters, ensure that RedHat subscription is enabled on all target nodes.

**Features enabled by omnia.yml**

* Slurm: Once all the required parameters in ``Omnia_config.yml`` are filled in, ``omnia.yml`` can be used to set up slurm.

* LDAP client support: The manager and compute nodes will have LDAP installed but the login node will be excluded.

* FreeIPA support

* Login Node (Additionally secure login node)

* Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

* BeeGFS bolt on installation

* NFS bolt on support

**Install scheduler**


1. In the ``input/omnia_config.yml`` file, provide the `required details <schedulerinputparams.html>`_.

.. note::  Without the login node, Slurm jobs can be scheduled only through the manager node.

2. Create an inventory file in the *omnia* folder. Add login node IP address under the *[login_node]* group, manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and NFS node IP address under the *[nfs_node]* group. A template file named INVENTORY is provided in the *omnia\docs* folder.

.. note::
     * Omnia checks for `red hat subscription being enabled on RedHat nodes as a pre-requisite <../../Roles/Utils/rhsm_subscription.html>`_. Not having Red Hat subscription enabled on the manager node will cause ``omnia.yml`` to fail. If compute nodes do not have Red Hat subscription enabled, ``omnia.yml`` will skip the node entirely.
     * Ensure that all the four groups (login_node, manager, compute, nfs_node) are present in the template, even if the IP addresses are not updated under login_node and nfs_node groups.
     * Omnia creates a log file which is available at: ``/var/log/omnia.log``.
     * If only Slurm is being installed on the cluster, docker credentials are not required.

3. To install Omnia:

       For CentOS, Rocky and RHEL:       ``ansible-playbook omnia.yml -i inventory``

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
    * All required configurations are made to slurm.conf file to enable a slurm login node.
    * FreeIPA (the default authentication system on the login node) is installed to provide centralized authentication.

.. note::

    * To enable the login node, ensure that ``login_node_required`` in ``input/omnia_config.yml`` is set to true.
    * To enable security features on the login node, ensure that ``enable_secure_login_node`` in ``input/omnia_config.yml`` is set to true.


**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd omnia/scheduler
    ansible-playbook job_based_user_access.yml -i inventory


.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.

**Installing LDAP Client**

Manager and compute nodes will have LDAP client installed and configured if ``ldap_required`` is set to true.

.. note::
    * No users/groups will be created by Omnia.
    * If LeapOS is being deployed, login_common and login_server roles will be skipped.


 To skip the installation of:

 * The login node: In the ``omnia_config.yml`` file, set the *login_node_required* variable to "false".

 * The FreeIPA server and client: Use ``--skip-tags freeipa`` while executing the *omnia.yml* file.



