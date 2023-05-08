FreeIPA installation on the NFS node
-------------------------------------

IPA services are used to provide account management and centralized authentication.

To customize your installation of FreeIPA, enter the following parameters in ``input/security_config.yml``.

+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                        |
+=========================+=================================================================+=======================================================================================================================================================+
| kerberos_admin_password | "admin" user password for the IPA server on RockyOS and RedHat. | The password can be found in the file ``input/security_config.yml`` .                                                                                 |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the manager node.                                                                                                        |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name             | Domain name                                                     | The domain name can be found in the file ``input/security_config.yml``.                                                                               |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server on the manager node using the ``ip a`` command. This IP address should be accessible from the NFS node. |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+


To set up IPA services for the NFS node in the target cluster, run the following command from the ``utils/cluster`` folder on the control plane: ::

       cd utils/cluster
       ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""


.. include:: ../../Appendices/hostnamereqs.rst

.. note:: Use the format specified under `NFS inventory in the Sample Files <../../samplefiles.html#nfs-server-inventory-file>`_ for inventory.