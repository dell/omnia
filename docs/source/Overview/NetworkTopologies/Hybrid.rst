Network Topology: Hybrid setup
=============================

For an environment containing both LOM and dedicated ports, the provision tool needs to be run twice to correctly manage all ports in the network.

.. images:: ../../images/omnia_network_Hybrid.png

The first time the provision tool is run, ensure that the following variables are set in ``input/provision_config.yml``:

    * ``network_interface_type``: ``Dedicated``
    * ``discovery_mechanism``: ``mapping``

.. caution:: Leave the variables ``bmc_nic_subnet``, ``bmc_static_start_range``, ``bmc_static_end_range``, ``primary_dns`` and ``secondary_dns`` blank in ``input/provision_config.yml``. Entering these variables will cause IP reassignment and can interfere with the availability of ports on your target servers.

Once all the dedicated NICs are discovered, re-run the provisioning tool with the following variables in ``input/provision_config.yml``:
    * ``network_interface_type``: ``LOM``
    * ``discovery_mechanism``: ``bmc``