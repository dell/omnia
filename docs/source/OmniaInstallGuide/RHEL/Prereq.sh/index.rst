Step 1: Running prereq.sh
===========================

The ``prereq.sh`` script installs the software utilized by Omnia on the control plane. Use the following command to execute the ``prereq.sh`` script: ::

    cd omnia
    ./prereq.sh

.. note::
    * Omnia recommends to disable SELinux before proceeding with the installation. If SELinux is not disabled, it will be disabled by the script and the you will be prompted to reboot the control plane.
    * The file ``input/software_config.json`` is overwritten with the default values (based on the operating system) when ``prereq.sh`` is executed.





