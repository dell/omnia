Input parameters for the cluster
-------------------------------------

These parameters are located in ``input/omnia_config.yml``, ``input/security_config.yml``, ``input/telemetry_config.yml`` and [optional] ``input/storage_config.yml``.

.. caution:: Do not remove or comment any lines in the ``input/omnia_config.yml``, ``input/security_config.yml`` and [optional] ``input/storage_config.yml`` file.

**omnia_config.yml**

.. csv-table:: Parameters for kubernetes setup
   :file: ../../Tables/scheduler_k8s.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for slurm setup
   :file: ../../Tables/scheduler_slurm.csv
   :header-rows: 1
   :keepspace:

**security_config.yml**

.. csv-table:: Parameters for Authentication
   :file: ../../Tables/security_config.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for OpenLDAP configuration
   :file: ../../Tables/security_config_ldap.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for FreeIPA configuration
   :file: ../../Tables/security_config_freeipa.csv
   :header-rows: 1
   :keepspace:


**storage_config.yml**

.. csv-table:: Parameters for Storage
   :file: ../../Tables/storage_config.csv
   :header-rows: 1
   :keepspace:

**telemetry_config.yml**

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

.. [1] Boolean parameters do not need to be passed with double or single quotes.


Click here for more information on `OpenLDAP, FreeIPA <Authentication.html>`_, `Telemetry <../../Roles/Telemetry/index.html>`_, `BeeGFS <BeeGFS.html>`_ or, `NFS <NFS.html>`_.

