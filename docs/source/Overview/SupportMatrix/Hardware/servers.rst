Servers
========

PowerEdge servers
------------------
+-------------+---------------------------------------------------------------------------+
| Server Type | Server Model                                                              |
+=============+===========================================================================+
| 14G         | C4140 C6420 R240 R340 R440 R540 R640 R740 R740xd R740xd2 R840 R940 R940xa |
+-------------+---------------------------------------------------------------------------+
| 15G         | C6520 R650 R750 R750xa                                                    |
+-------------+---------------------------------------------------------------------------+
| 16G         | C6620 R660 R6625 R760 XE8640 R760xa [1]_ R760xd2  XE9680                  |
+-------------+---------------------------------------------------------------------------+

.. [1] The R760xa supports both H100 and A100.

.. note::  Since Cloud Enclosures only support shared LOM connectivity, it is recommended that `BMC <../../../InstallationGuides/InstallingProvisionTool/DiscoveryMechanisms/bmc.html>`_ or `Switch-based <../../../InstallationGuides/InstallingProvisionTool/DiscoveryMechanisms/switch-based.html>`_ methods of discovery are used.

AMD servers
-----------
+-------------+-------------------------------+
| Server Type | Server Model                  |
+=============+===============================+
| 14G         | R6415 R7415 R7425             |
+-------------+-------------------------------+
| 15G         | R6515 R6525 R7515 R7525 C6525 |
+-------------+-------------------------------+
| 16G         | R6625 R7625 R7615 R6615       |
+-------------+-------------------------------+

.. versionadded:: 1.2
    15G servers

.. versionadded:: 1.3
    AMD servers

.. versionadded:: 1.4.1
    Intel 16G servers

.. versionadded:: 1.4.3
    Intel: R760 XE8640 R760xa R760xd2 XE9680; AMD 16G servers
