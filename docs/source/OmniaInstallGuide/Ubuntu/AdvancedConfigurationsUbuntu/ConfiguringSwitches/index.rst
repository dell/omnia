Configuring switches
=====================

.. note::

    * Omnia is specifically designed to support the configuration of Infiniband switches that run on the NVIDIA MLNX-OS network operating system.
    * Omnia is specifically designed to support the configuration of Ethernet switches that run on the Dell SmartFabric OS10 network operating system.
    * If you are using Ethernet switches that run on a free and open-source network operating system like SONiC OS, it is important to note that the configuration process will need to be done manually by users.
    * Omnia supports the configuration of the BMC (out-of-band) and admin network switches for the switches mentioned in the `support matrix <../../../../Overview/SupportMatrix/Hardware/switches.html>`_. However, it is important to note that Omnia only configures the data network and does not handle the configuration of the management network.
    * Omnia does not handle the configuration of the management port for switches. Instead, users are responsible for configuring the management port by providing the switch IP and necessary credentials.

.. toctree::
    infiniband
    ethernet-s3_s4
    ethernet-s5
    ethernet-Z


