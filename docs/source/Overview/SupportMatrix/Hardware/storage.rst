Storage
========

PowerVault Storage
------------------

+--------------+---------------------------+------------------------------------------------+
| Storage Type | Models supported by Omnia | Models validated with current version of Omnia |
+==============+===========================+================================================+
| ME4          | ME4084, ME4024, ME4012    | ME4024                                         |
+--------------+---------------------------+------------------------------------------------+
| ME5          | ME5012, ME5024, ME5084    |                                                |
+--------------+---------------------------+------------------------------------------------+

.. note:: Omnia supports configuration of RAID levels, volumes, pool, and SNMP on PowerVault devices. For more information on PowerVault configuration using Omnia, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/ConfiguringStorage/index.html#configuring-storage>`_.

BOSS Controller Cards
----------------------

+-----------------------------------------------------+-----------------------------------------------------+
| Models supported by Omnia                           | Models validated with current version of Omnia      |
+=====================================================+=====================================================+
| Dell Boot Optimized Storage Solution-N1 (BOSS-N1)   | Dell Boot Optimized Storage Solution-N1 (BOSS-N1)   |
+-----------------------------------------------------+-----------------------------------------------------+
| Dell Boot Optimized Storage Solution-S1 (BOSS-S1)   | Dell Boot Optimized Storage Solution-S1 (BOSS-S1)   |
+-----------------------------------------------------+-----------------------------------------------------+
| Dell Boot Optimized Storage Solution-S2 (BOSS-S2)   | Dell Boot Optimized Storage Solution-S2 (BOSS-S2)   |
+-----------------------------------------------------+-----------------------------------------------------+

.. note:: Omnia does not support virtual drive configuration for BOSS cards. A virtual drive is present by default on the BOSS card, but if it is missing, the user must manually create one before running the ``discovery_provision.yml`` playbook.

PowerScale Storage
----------------------

+-------------------------------+------------------------------------------------+
| Models supported by Omnia     | Models validated with current version of Omnia |
+===============================+================================================+
| PowerScale H5600, H7000, H500 | PowerScale H500                                |
+-------------------------------+------------------------------------------------+
| PowerScale F600, F900, F710   | PowerScale F710                                |
+-------------------------------+------------------------------------------------+

.. versionadded:: 1.7
    PowerScale H500, PowerScale F710

.. note:: Omnia does not support configuring PowerScale; it only allows users to add an existing PowerScale node to a Kubernetes cluster.