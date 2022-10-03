Provision
=========

Omnia leverages xCAT to provision servers, switches and storage. xCAT stands for eXtreme Cloud Administration Toolkit.

``Provision.yml`` can be run by itself or can be called using ``control_plane.yml``.

Once Omnia is downloaded from github:

``git clone https://github.com/dellhpc/omnia.git``

Enter all required parameters in ``omnia/input/provision_config.yml``:

.. include:: ../../InputParamGuide/provision.rst

Change directory to the omnia/provision folder:

``cd omnia/provision``


Run the script:

``ansible-playbook provision.yml``

.. warning::

* The xCAT script opens multiple ports required for xCAT to function. For a list of ports required, `click here <../../../SecurityConfigGuide/PortsUsed/xCAT>`_.
