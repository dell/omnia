Running prereq.sh
=================

``prereq.sh`` is used to install the software utilized by Omnia on the control plane including Python (3.9), Ansible (2.14).  ::

    cd omnia
    ./prereq.sh

.. note::
    * If SELinux is not disabled, it will be disabled by the script and the user will be prompted to reboot the control plane.
    * The file ``input/software_config.json`` is overwritten with the default value (based on the operating system) when ``prereq.sh`` is executed.




