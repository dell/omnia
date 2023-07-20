Input parameters for the cluster
-------------------------------------

These parameters are located in ``input/omnia_config.yml``.

.. caution:: Do not remove or comment any lines in the ``input/omnia_config.yml`` file.

.. csv-table:: Parameters
   :file: ../../Tables/scheduler.csv
   :header-rows: 1
   :keepspace:

.. note::

    The ``input/omnia_config.yml`` file is encrypted on the first run of the provision tool:
        To view the encrypted parameters: ::

            ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key

