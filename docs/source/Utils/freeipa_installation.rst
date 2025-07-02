FreeIPA installation on the NFS node
=====================================

IPA services are used to provide account management and centralized authentication. If admin user intends to install the FreeIPA authentication on the NFS node (server connected to the storage devices), then the following playbook can be utilized.

To install FreeIPA on NFS node, get the values of ``kerberos_admin_password`` and ``domain_name`` from ``input/security_config.yml``. Ensure to provide the below ``ipa_server_hostname`` and ``ipa_server_ipadress`` as extra arguments along with  during playbook execution.

+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                             |
+=========================+=================================================================+============================================================================================================================================================+
| kerberos_admin_password | "admin" user password for the IPA server on RHEL                | The password can be found in the file ``input/security_config.yml`` .                                                                                      |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the ``auth_server``.                                                                                                          |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name             | Domain name                                                     | The domain name can be found in the file ``input/security_config.yml``.                                                                                    |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server on the ``auth_server`` using the ``ip a`` command. This IP address should be accessible from the NFS node.   |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+

To set up IPA services for the NFS node in the target cluster, run the following command from the ``utils/cluster`` folder on the OIM: ::

    cd utils/cluster
    ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""

**Hostname requirements**

* The hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed with commas and periods.
* The hostname cannot start or end with a hyphen (-).
* No upper case characters are allowed in the hostname.
* The hostname cannot start with a number.
* The hostname and the domain name (that is: ``hostname00000x.domain.xxx``) cumulatively cannot exceed 64 characters. For example, if the ``node_name`` provided in ``input/provision_config.yml``

.. note::

    * Use the format specified under `NFS inventory in the Sample Files <../OmniaInstallGuide/samplefiles.html#nfs-server-inventory-file>`_ for inventory.
    * Omnia only supports ``/home`` as the ``homeDirectory``.