Input Parameters for Provision Tool
------------------------------------

Fill in all provision-specific parameters in ``input/provision_config.yml``

.. tabularcolumns:: |p{7cm}|p{3.5cm}| p{7cm}| p{7cm}|

.. csv-table:: provision_config
   :file: ../Tables/Provision_config.csv
   :header-rows: 1
   :class: longtable
   :widths: 2 1 2 2

.. warning::

    * The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.
    * The IP range *x.y.246.1* - *x.y.255.253* (where x and y are provided by the first two octets of ``bmc_nic_subnet``) are reserved by Omnia.