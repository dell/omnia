Alternate method to install the Intel Gaudi Habana platform
=============================================================

The accelerator role allows users to set up the `Intel Gaudi Habana <https://docs.habana.ai/en/latest/Installation_Guide/Bare_Metal_Fresh_OS.html>`_ platform. This tools allow users to unlock the potential of installed Intel Gaudi accelerators.

**Prerequisites**

* The Habana local repositories must be configured using the `local_repo.yml <../CreateLocalRepo/index.html>`_ script.
* The ``input/software_config.json`` must contain valid ``intelgaudi`` version. See `input parameters <../CreateLocalRepo/InputParameters.html>`_ for more information.

.. note:: Intel Gaudi Habana platform is only supported on Ubuntu 22.04 clusters containing Intel Gaudi accelerators.

**Playbook configurations**

The following configurations takes place while running the ``accelerator.yml`` playbook:

	i. Servers with Intel Gaudi accelerators are identified and the latest drivers and Habana platforms are downloaded and installed.
	ii. Servers with no accelerator are skipped.

**Executing the playbook**

To install all the latest drivers and toolkits, run: ::

	cd accelerator
	ansible-playbook accelerator.yml -i inventory

.. note:: While executing the ``accelerator.yml`` playbook for Intel Gaudi nodes, a Cron job is run which brings up the Intel Gaudi scale-out network interfaces.