Running prereq.sh
=================

``prereq.sh`` is used to install the software utilized by Omnia on the control plane including Python (3.8), Ansible (2.12.10).  ::

    cd omnia
    sh prereq.sh


.. note::
    * If SELinux is not disabled, it will be disabled by the script and the user will be prompted to reboot the control plane.
    * If the control plane is running on the minimal edition of the OS, ensure that ``chrony`` and ``podman`` are installed before running ``provision.yml``.





