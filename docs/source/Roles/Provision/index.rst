Provision
=========

Omnia leverages xCAT to provision servers, switches and storage. xCAT stands for eXtreme Cloud Administration Toolkit.

``Provision.yml`` can be run by itself or can be called using ``control_plane.yml``.

Once Omnia is downloaded from github:

``git clone https://github.com/dellhpc/omnia.git``

Change directory to the omnia/provision folder:

``cd omnia/provision``

Enter all required parameters:

<Table insert here>

Run the script:

``ansible-playbook provision.yml``

.. warning::

* The xCAT script opens multiple ports required for xCAT to function
