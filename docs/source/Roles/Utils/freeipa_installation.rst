FreeIPA installation on the NFS node
-------------------------------------

IPA services are used to provide account management and centralized authentication. If admin user intends to install the FreeIPA authentication on the NFS node (server connected to the storage devices), then the following playbook can be utilized.

To install FreeIPA on NFS node, get the values of ``kerberos_admin_password`` and ``domain_name`` from ``input/security_config.yml``. Ensure to provide the below ``ipa_server_hostname`` and ``ipa_server_ipadress`` as extra arguments along with  during playbook execution.

+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                             |
+=========================+=================================================================+============================================================================================================================================================+
| kerberos_admin_password | "admin" user password for the IPA server on Rocky OS and RedHat.| The password can be found in the file ``input/security_config.yml`` .                                                                                      |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the ``auth_server``.                                                                                                          |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name             | Domain name                                                     | The domain name can be found in the file ``input/security_config.yml``.                                                                                    |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server on the ``auth_server`` using the ``ip a`` command. This IP address should be accessible from the NFS node.   |
+-------------------------+-----------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------+

To set up IPA services for the NFS node in the target cluster, run the following command from the ``utils/cluster`` folder on the control plane: ::

    cd utils/cluster
    ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""


.. include:: ../../Appendices/hostnamereqs.rst

.. note::

    * Use the format specified under `NFS inventory in the Sample Files <../../samplefiles.html#nfs-server-inventory-file>`_ for inventory.

    * Omnia only supports ``/home`` as the ``homeDirectory``.

To set up IPA services for the NFS node in the target cluster, run the following command from the ``utils/cluster`` folder on the control plane: ::

       cd utils/cluster
       ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""


.. include:: ../../Appendices/hostnamereqs.rst

.. note:: Use the format specified under `NFS inventory in the Sample Files <../../samplefiles.html#nfs-server-inventory-file>`_ for inventory.