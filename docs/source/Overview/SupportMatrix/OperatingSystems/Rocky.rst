Rocky
=====

+------------+---------------+---------------+
| OS Version | Control Plane | Compute Nodes |
+============+===============+===============+
| 8.4        | Yes           | Yes           |
+------------+---------------+---------------+
| 8.5        | Yes           | Yes           |
+------------+---------------+---------------+

.. note:: Always deploy the DVD Edition of the OS on Compute Nodes





.. note::

     * At any given point, the client and management BeeGFS servers must be running the same major version of BeeGFS (ie 7.x). However, minor versions need not match (ie, management **7.x**.y and client **7.x**.z is supported).

     * Upgrading BeeGFS to 7.3 using ``omnia.yml`` is not supported