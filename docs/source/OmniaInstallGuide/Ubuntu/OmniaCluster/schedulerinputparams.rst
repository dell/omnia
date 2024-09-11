Input parameters for the cluster
===================================

These parameters are located in ``input/omnia_config.yml``, ``input/security_config.yml``, and [optional] ``input/storage_config.yml``.

.. caution:: Do not remove or comment any lines in the ``input/omnia_config.yml``, ``input/security_config.yml``, and [optional] ``input/storage_config.yml`` file.

omnia_config.yml
-------------------

.. csv-table:: Parameters for kubernetes setup
   :file: ../../../Tables/scheduler_k8s_ubuntu.csv
   :header-rows: 1
   :keepspace:


security_config.yml
---------------------

.. csv-table:: Parameters for Authentication
   :file: ../../../Tables/security_config.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for OpenLDAP configuration
   :file: ../../../Tables/security_config_ldap.csv
   :header-rows: 1
   :keepspace:


storage_config.yml
--------------------

.. csv-table:: Parameters for Storage
   :file: ../../../Tables/storage_config.csv
   :header-rows: 1
   :keepspace:


.. [1] Boolean parameters do not need to be passed with double or single quotes.


Click here for more information on `OpenLDAP <BuildingCluster/Authentication.html>`_, `BeeGFS <Storage/BeeGFS.html>`_, or `NFS <Storage/NFS.html>`_.

.. note::

    * The ``input/omnia_config.yml`` and ``input/security_config.yml`` files are encrypted during the execution of ``omnia.yml`` playbook. Use the below commands to edit the encrypted input files:

        * ``omnia_config.yml``: ::

            ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key

        * ``security_config.yml``: ::

            ansible-vault edit security_config.yml --vault-password-file .security_vault.key

