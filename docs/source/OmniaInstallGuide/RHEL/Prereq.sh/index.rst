Step 1: Execute prereq.sh
===========================

Starting from version 1.7, Omnia will be executed within a Python virtual environment. To set up this environment, the ``prereq.sh`` script is utilized. This script creates the virtual environment, as well as installs the necessary Python 3.11 and Ansible 9.5.1 versions required by Omnia on the control plane. The predefined path for this virtual environment is ``/opt/omnia_venv_1_7``. This approach ensures that Omnia has the correct dependencies and runs smoothly within a controlled and isolated environment.

.. caution:: To run Omnia, it is essential to use the Python virtual environment that is created using the ``prereq.sh`` script.

* Use the following command to execute the ``prereq.sh`` script: ::

    cd omnia
    source prereq.sh

* After running the script, use the following command to activate the virtual environment: ::

    source /opt/omnia_venv_1_7/bin/activate

* Once the virtual environment is active, the following prompt will be displayed: ::

    (omnia) [root@<control_plane_name> omnia]#

.. note::
    * Omnia recommends to disable SELinux before proceeding with the installation. If SELinux is not disabled, it will be disabled by the script and the you will be prompted to reboot the control plane.
    * The file ``input/software_config.json`` is overwritten with the default values (based on the operating system) when ``prereq.sh`` is executed.
