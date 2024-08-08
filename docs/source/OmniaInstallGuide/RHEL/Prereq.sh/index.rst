Step 1: Execute prereq.sh
===========================

Starting from version 1.7, Omnia will be executed within a Python virtual environment. To set up this environment, the ``prereq.sh`` script is utilized. This script installs the necessary Python 3.11, creates the Python virtual environment, as well as installs Ansible 9.5.1 version and other software packages required by Omnia on the control plane. The predefined path for this virtual environment is ``/opt/omnia17_ven``. This approach ensures that Omnia has the correct dependencies and runs smoothly within a controlled and isolated environment.

.. caution:: To run Omnia, it is essential to use the Python virtual environment that is created using the ``prereq.sh`` script.

* Use the following command to execute the ``prereq.sh`` script on the control plane: ::

    cd omnia
    ./prereq.sh

* To activate the virtual environment, use the following command: ::

    source /opt/omnia17_venv/bin/activate

 .. image:: ../../../images/virtual_env_2.png

* To verify that the virtual environment is active, check if the following prompt is displayed: ::

    (omnia) [root@<control_plane_name> omnia]#

.. note::
    * Omnia recommends to disable SELinux before proceeding with the installation. If SELinux is not disabled, it will be disabled by the script and the you will be prompted to reboot the control plane.
    * The file ``input/software_config.json`` is overwritten with the default values (based on the operating system) when ``prereq.sh`` is executed.


Deactivate the Omnia virtual environment
---------------------------------------------

* If you want to deactivate the virtual environment set up by the ``prereq.sh`` script, use the following command from within the activated virtual environment: ::

    deactivate

 .. image:: ../../../images/virtual_env_deactivate.png

