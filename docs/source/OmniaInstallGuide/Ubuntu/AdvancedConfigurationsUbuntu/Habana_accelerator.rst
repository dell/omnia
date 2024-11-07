Alternate method to install the Intel Gaudi Software Stack and Driver
=======================================================================

The accelerator role allows users to set up the `Intel Gaudi Software Stack and Driver <https://docs.habana.ai/en/latest/Installation_Guide/Bare_Metal_Fresh_OS.html>`_. This tools allow users to unlock the potential of installed Intel Gaudi accelerators.

**Prerequisites**

* The Intel Gaudi local repositories must be configured using the `local_repo.yml <../CreateLocalRepo/index.html>`_ script.
* The ``input/software_config.json`` must contain valid ``intelgaudi`` version. See `input parameters <../CreateLocalRepo/InputParameters.html>`_ for more information.

.. note:: Intel Gaudi platform is only supported on Ubuntu 22.04 clusters containing Intel Gaudi accelerators.

**Playbook configurations**

The following configurations takes place while running the ``accelerator.yml`` playbook:

	i. Servers with Intel Gaudi accelerators are identified and the latest drivers and software stack are downloaded and installed.
	ii. Servers with no accelerator are skipped.

**Executing the playbook**

To install all the latest drivers and toolkits, run: ::

	cd accelerator
	ansible-playbook accelerator.yml -i inventory

.. note::

    * While executing the ``accelerator.yml`` playbook for Intel Gaudi nodes, a Cron job is run which brings up the Intel Gaudi scale-out network interfaces.
    * If a node contains an Intel Gaudi GPU with internet access during provisioning, then the user needs to install the Gaudi driver using the ``accelerator.yml`` playbook.