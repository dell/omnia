Running prereq.sh
=================

The ``prereq.sh`` script checks the prerequisites and verifies if the control plane is ready for Omnia deployment. ``prereq.sh`` facilitates the installation of required software on the control plane, including Python (3.8) and Ansible (2.1.2.10).

    cd omnia
    sh prereq.sh


.. note::
    * If SELinux is not disabled, it will be disabled by the script and the user will be prompted to reboot the control plane.
    * If the control plane is running on the minimal edition of the OS, ensure that ``chrony`` and ``podman`` are installed before running ``provision.yml``.





